# NPU 架构对比

> 2026-10-23 初稿。端侧 NPU 的微架构：Hexagon（高通）、ANE（Apple）、NPU 890（联发科）、Ethos-U（Arm）、Coral NPU（Google 开源）。
> 相关：[[手机SoC端侧AI能力横向对比]]、[[NPU工具链与碎片化问题]]、[[异构调度与NPU利用]]

## 0. TL;DR

- NPU 微架构的公共内核是 **MAC 阵列 + 显式数据搬运（DMA）+ 分层存储**——用"数据驻留换算力"提高能效；差异在于**可编程性光谱**：Hexagon 是"跑三条 ISA 的可编程处理器"，ANE 是"Core ML 后面的固定功能引擎"，Ethos-U/Coral 是"离线编译命令流的执行器"
- 设计哲学分歧聚焦一点：**定点 vs 浮点**。高通 HotChips 报告明确论证：DNN 数据多为正态分布，INT8 优于 FP8（PTQ/QAT 均然）；Transformer 的 softmax outlier 用 QAT 拉回
- Apple ANE 的细节长期是黑盒，2025-2026 年被逆向工程完整还原（ane-guide）：MAC 阵列几何、程序格式、93 条命令协议——证实"无公开 ISA、不可直接编程"是其碎片化角色的根源
- Google Coral NPU（开源 RISC-V IP）代表"用通用 ISA 消灭 NPU 编程碎片化"的激进实验

## 1. NPU 通用微架构原理

（以 [Arm Ethos-U85 技术文档](https://documentation-service.arm.com/static/66617778d72aaf32efecd23f) 为参照系）

```
中央控制（CC）─ 调度命令流
    ├── DMA 控制器 ─ 显式搬运（片外 DRAM ↔ 片上 SRAM）
    ├── 权重解码器（WD）─ 权重流解压（标准/FWD 两种格式）+ MATMUL 张量重排
    ├── MAC 单元 ─ DPU 阵列做点积；L1（每周期）/L2（每 8 周期）两级累加
    └── 激活输出（AO）单元 ─ 激活/池化写出
```

能效的三个来源：

1. **算术强度**：N×N 矩阵乘读 2N² 值做 2N³ 次运算——计算/访存比 N:1，远高于标量/向量单元（[Qualcomm NPU 白皮书](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Unlocking-on-device-generative-AI-with-an-NPU-and-heterogeneous-computing.pdf)）
2. **数据驻留**：片上 SRAM/共享内存复用权重与中间结果，减少 DRAM 往返
3. **精度裁剪**：INT4/INT8 专用通路；Ethos-U85 还支持 2:4 稀疏（预剪枝后 DPU 吞吐翻倍）

代价：**偏好静态、规整、高复用的负载**——这正是 LLM decode（GEMV、动态 shape、KV cache 逐 token 写）在 NPU 上表现差的微架构根源（见 [[异构调度与NPU利用]]）。

## 2. 各家架构逐个分析

### 2.1 Qualcomm Hexagon——"可编程 NPU"

（[HotChips 2023](https://hc2023.hotchips.org/assets/program/conference/day2/ML%20Inference/HC2023%20Qualcomm%20Hexagon%20NPU.pdf) + 产品简报）

- **一个处理器、三条 ISA**：Scalar（控制流，Int8-64/Float32-64）+ Vector（1024-bit SIMD，scatter/gather）+ Tensor（矩阵乘/卷积专用，支持 (8/16)×(4/8/16) 整数与 FP16×FP16，融合激活、per-output-channel scaling）
- **DSP 血统**：VLIW、硬件循环、多硬件线程；又带 CPU 特性（虚拟内存、安全、缓存、LLVM 工具链）——**是三家里最像"通用处理器"的 NPU**
- **TCM（紧耦合内存）**：软件管理的 cache，向量/张量走 L2 而非 L1——可预测带宽 + scatter/gather 加速
- **演进脉络**：2020 融合架构（标量+向量+张量共享大内存）→ 8 Gen 2（独立供电轨、microtile 推理、INT4、transformer 加速）→ 8 Gen 3（共享内存带宽翻倍，+98% 性能/+40% 能效）→ 8 Elite Gen 5（12 标量 + 8 向量 + 1 张量配置，INT2 支持，生成式模型加密）
- **数值哲学**：QFloat 替代 IEEE 浮点（硬件更高效、无 NaN/Inf 语义）；定点累加优于浮点累加——"CNN 数据正态，INT8 胜 FP8；Transformer 有 softmax outlier，但 QAT 能拉回"
- 配套 Sensing Hub：双 micro NPU 常驻待机（<1mA）处理音频/传感器

### 2.2 Apple ANE——"固定功能引擎"

（逆向工程 [ane-guide](https://ane-guide.readthedocs.io/en/latest/)，2025-2026 完成；Apple 官方几乎不公开细节）

- **无公开 ISA、无驱动接口、无文档**——只能经 Core ML 间接使用（placement hint）；这是"最高性能利用率 × 最低可编程性"的极端
- MAC 阵列几何（M1 实测）：4 个物理核（每核独立电源轨），8 深累加器文件（双缓冲上限 4），int8 每周期 8 输出通道 / fp16 每周期 4 通道，radix-4 规约树 + fp32 宽累加器
- 固件里**没有卷积/Winograd/systolic 代码**——固件只是实时内核 + tile/kernel/DMA 管道：计算结构全部由编译器离线编排进命令流
- 命名规则：M(n) 芯片 = H(n+12) 引擎架构（M1=H13、M5=H17），跨代仅核心数/频率扩展（M5：16 核 ~1.89GHz），一个编译器二进制覆盖 28 个目标
- 逆向甚至发现：普通用户进程可以绕过 Core ML 直连引擎——但接口随时可能随 OS 更新失效

### 2.3 MediaTek NPU 890——"生成式特化"

（[MediaTek AI 页面](https://www.mediatek.com/zh-cn/technology/ai) + 旗舰发布材料）

- 第 7 代 NPU 起面向 Transformer 生成式 AI 设计；890 为第八代
- 多核架构：MDLA（深度学习加速器，MAC 阵列）+ MVPU（视觉处理器）+ 硬件多核调度器 + 专用 DMA（深度层融合与数据压缩，降 DRAM 带宽）+ 片上网络 NoC
- 混合精度：INT4/INT8/INT16、FP16、BF16
- **差异化能力**：宣称首个支持**端侧 LoRA 训练**的手机 NPU；支持 MoE/MLA 架构模型（DeepSeek-R1-Distill 端侧运行）
- 能效主张：DLA 相对典型 CPU 能效 27×、相对 GPU 15×

### 2.4 Arm Ethos-U85——"标准的 MCU 级 NPU"

- 128–2048 MAC 可配置（256 GOP/s–4 TOPS @1GHz），比 U55/U65 能效 +20%，原生支持 transformer
- **TOSA（Tensor Operator Set Architecture）合规**——用标准算子集约束编译目标，是碎片化问题的正面回应（见 [[NPU工具链与碎片化问题]]）
- 离线编译器把模型编成命令流，运行时 MCU 只负责递交——纯静态执行模型

### 2.5 Google Coral NPU——"开源 RISC-V 实验"

（[官方文档](https://developers.google.com/coral/guides/intro)）

- **动机直指碎片化**：传统 NPU 依赖专有编译器生成命令缓冲，开发者面对"每块 ML 加速单元一套私有工具链"
- 设计：ML-first（先矩阵后向量标量，统一进一条 ISA）；RV32IM 标量核（run-to-completion、无 OS）+ RVV 1.0 向量核 + 量化外积 MAC 引擎；8KB/16KB 单层 cache
- 开源 IP + MLIR/IREE 工具链（JAX/PyTorch/LiteRT 经 StableHLO/TOSA 进同一条编译管线）
- 定位可穿戴/ambient sensing（目标 ~512 GOP/s @1GHz、mW 级功耗）——不与旗舰 SoC NPU 竞争，而是验证"**开放 NPU 架构**"路线

## 3. 横向对比表

| 维度 | Hexagon | ANE | NPU 890 | Ethos-U85 | Coral NPU |
|---|---|---|---|---|---|
| 可编程性 | 三 ISA 可编程 | 不可编程（Core ML 间接） | SDK 接入 | 离线命令流 | **C 可编程（RISC-V）** |
| 算力定位 | 45–80+ TOPS（旗舰） | ~35 TOPS | ~50 TOPS | ≤4 TOPS（MCU） | ~512 GOP/s |
| 数值 | INT2/4/8/16, FP16, QFloat | int8/fp16 | INT4/8/16, FP16/BF16 | INT8/16 | 量化 MAC |
| 交付形态 | SoC 内置 | SoC 内置 | SoC 内置 | IP 授权 | **开源 IP** |
| 工具链开放度 | 上开下闭 | 全闭 | 中 | 开放（TOSA） | 全开（MLIR） |
| 独特能力 | microtile、Sensing Hub | 规模化垂直整合 | 端侧 LoRA 训练 | 2:4 稀疏 | 统一 ISA 消碎片 |

## 4. 关键洞察

1. **可编程性是光谱而非开关**：Hexagon（可编程处理器）↔ ANE（固定功能引擎）两端之间，Ethos 的"标准算子集 + 命令流"和 Coral 的"通用 ISA + ML 编译器"是两种中间态——**碎片化的根源不在硬件而在"谁有权定义编程模型"**
2. **三家头部都收敛到"标量+向量+张量异构融合 + 大共享内存 + 独立供电"** 的模板；差异被推到数值格式和工具链层
3. **微架构证据支持"QAT 路线"**：高通的定点论证 + NPU 整数通路优势，与 [[量化技术]] 中"端侧不能只靠 PTQ"的结论在硬件层闭环
4. **逆向工程是了解 ANE 的唯一途径**这一事实本身，就是端侧生态信息不对称的极端体现

## 5. 开放问题

- [ ] NPU 890 的端侧 LoRA 训练的公开技术细节（训练/推理混合负载的内存调度）
- [ ] Coral NPU 路线是否会被主流 SoC 采纳（还是停留在大芯片边缘的 wearable/IoT）
- [ ] ANE 逆向成果（ane-guide）的系统化验证与跨版本稳定性
- [ ] 2:4 稀疏等"结构化稀疏通路"在 LLM 权重上的实际收益数据

## 6. 来源

- [Qualcomm: Unlocking On-Device Generative AI with an NPU（白皮书）](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Unlocking-on-device-generative-AI-with-an-NPU-and-heterogeneous-computing.pdf)
- [Qualcomm Hexagon NPU @ HotChips 2023](https://hc2023.hotchips.org/assets/program/conference/day2/ML%20Inference/HC2023%20Qualcomm%20Hexagon%20NPU.pdf)
- [Hexagon V68 HVX Programmer's Reference](https://docs.qualcomm.com/doc/80-N2040-47/80-N2040-47.pdf) / [8 Elite / 8 Elite Gen 5 产品简报](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-5-product-brief.pdf)
- [ane-guide: Apple Neural Engine 逆向工程](https://ane-guide.readthedocs.io/en/latest/)（[GitHub](https://github.com/sbryngelson/ane-guide)）
- [Arm Ethos-U85 Technical Overview](https://documentation-service.arm.com/static/66617778d72aaf32efecd23f) / [产品页](https://www.arm.com/products/silicon-ip-cpu/ethos/ethos-u85)
- [MediaTek AI 技术页](https://www.mediatek.com/zh-cn/technology/ai)
- [Google Coral NPU 文档](https://developers.google.com/coral/guides/intro)
