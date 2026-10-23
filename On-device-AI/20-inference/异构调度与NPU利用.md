# 异构调度与 NPU 利用

> 2026-10-23 初稿。核心问题：**为什么手机 NPU 有几十 TOPS 算力，实际 LLM 推理却跑在 CPU 上？**
> 主线实证：EPFL 在 OnePlus 13R 上的跨框架实测（[arXiv:2507.08505](https://arxiv.org/pdf/2507.08505)）。
> 相关：[[推理框架横向对比]]、[[KV cache与长上下文]]、[[NPU工具链与碎片化问题]]

## 0. TL;DR

**NPU 利用率悖论**：2025 年旗舰手机 NPU 标称 35–85 TOPS，但主流开源框架（llama.cpp、mllm 等）推理时 CPU 占用 600–800%、GPU/NPU 几乎完全闲置。EPFL 实测纯 CPU 路线与 GPU 卸载路线功耗差距近 **8 倍**（10–12W vs 1.3W）。根因不是单一工程问题，而是四层结构性错配：**负载特征错配（GEMV vs NPU 设计偏好）、动态性错配（自回归解码 vs 静态图）、内存模型错配（KV cache 动态增长 vs 固定内存规划）、生态碎片化（每家 NPU 一套 SDK）**。

## 1. 核心实证：OnePlus 13R 上的 VLM 推理

实验设置：OnePlus 13R（骁龙 8 Gen 2：8 核 Kryo CPU + Adreno 740 GPU + Hexagon NPU，12GB RAM），Android 15，root 后采集 /proc、/sys 性能计数器，100ms 间隔。负载：LLaVA-1.5 7B / MobileVLM-3B / Imp-v1.5-3B，框架：llama.cpp / mllm / MLC-Imp。

| 指标 | llama.cpp + LLaVA-7B（CPU 路线） | mllm + LLaVA-7B（CPU 路线） | MLC-Imp + Imp-3B（GPU 卸载） |
|---|---|---|---|
| CPU 占用 | ~600%（8 核） | 650–750% | ≤120% |
| GPU 占用 | 0% | 0% | 90–100% |
| NPU 占用 | **从未调用** | **从未调用** | 未用（但 GPU 有效利用） |
| 结温 | 88–90°C（15s 内从 40°C 升至） | 92–95°C | 60°C 峰值 |
| 功耗 | ~3.1A（≈10W） | ~2.9A（≈11W） | 0.33A（≈1.3W） |
| 电池续航* | ~8 小时 | — | ~2 天 |

\* 按每分钟一次查询的负载折算。

其他关键观察：

- **延迟瓶颈在 prompt eval**：LLaVA-7B 在 llama.cpp 上 prompt eval 约 70s/605 tokens（~150 ms/token），token 生成 ~171 ms/token；总延迟 80–170s 量级
- 尝试把图像处理卸载到 GPU 的框架出现过**设备不稳定**（屏幕冻结、响应劣化）
- MLC-Imp 成功卸载后，延迟仍受限于**逐 token 串行解码**——加速器解决的是功耗和发热，解码延迟需要另想办法（投机解码、架构级优化）

> 注：论文原文文本与表格数字略有出入（不同 run），上表取自论文表格，文字数据取区间。

## 2. 根因分析：四层结构性错配

### 2.1 负载特征错配：decode 是 GEMV，NPU 不擅长

LLM 推理两阶段负载截然不同：

| 阶段 | 计算形态 | 特征 | 适合的硬件 |
|---|---|---|---|
| **prefill**（提示编码） | GEMM（大矩阵乘） | 高算术强度、高并行、数据复用充分 | GPU / NPU |
| **decode**（逐 token 生成） | GEMV（矩阵×向量） | 内存带宽受限、低并行、低算术强度 | CPU 大核 / 带宽优化单元 |

NPU 的效率来自**数据复用**（PE 阵列驻留权重、输入流过），GEMV 的算术强度太低，NPU 跑 GEMV 反而浪费阵列——EPFL 论文明确指出 "NPUs are particularly inefficient for GEMV workloads due to limited data reuse and low arithmetic intensity"。而 decode 恰恰是交互延迟的主要构成。**硬件算力（TOPS）是为 prefill 型负载宣传的，用户感知的卡顿发生在 decode。**

### 2.2 动态性错配：自回归 vs 静态图

NPU 编译工具链（QNN 等）偏好**静态 shape、静态图**——算子融合、内存规划都在编译期确定。而 LLM 推理：

- 每步生成 1 个 token，序列长度逐步 +1（KV cache 写入位置变化）
- batch=1 单流负载，无法像云端那样靠 batching 摊薄
- MNN QNN 后端要求 `shapeMutable=false`，正是这种约束的体现——需要离线构图、按 SoC 生成产物

### 2.3 内存模型错配：KV cache 动态增长

KV cache 随上下文线性增长且每步读写，与 NPU 固定内存规划冲突。Apple 为此专门"开发了一种在神经引擎上高效更新 KV cache 的方法"（[Apple FM 技术报告](https://machinelearning.apple.com/research/introducing-apple-foundation-models)）——侧面说明这是接入 ANE 的真正难点之一。Apple 2025 模型的 5:3 分块 KV 共享设计（省 37.5%）也是从模型架构侧缓解此问题（→ [[模型-硬件协同设计]]）。

### 2.4 生态碎片化：通用框架覆盖不了 NPU

- 每家 NPU 一套 SDK：QNN / Core ML / NeuroPilot / HiAI / NNAPI(被 Google 弃更) / RKNN
- 手写内核路线（llama.cpp、MLX）无法为每种 NPU 维护后端 → NPU 支持缺失
- 编译器路线的解法：ExecuTorch **delegate 分区 + CPU fallback**（部分加速渐进落地），已将 QNN、Core ML、MediaTek NPU 等升到 production；MNN 用五后端硬扛
- Apple 是唯一把 NPU 路径彻底打通的（私有栈 + 自家模型 + 自家框架）

## 3. 现有解决路径

| 路径 | 思路 | 代表 |
|---|---|---|
| **GPU 卸载** | 通用性最好的中间态：GPU 跑 prefill + 部分解码，功耗/温度大幅下降 | MLC-Imp（1.3W vs 10W 实证） |
| **NPU-CPU 分阶段混合** | NPU 跑 chunked prefill，decode 拆到 CPU+NPU 多核协同 | mllm-NPU（浙大，待精读） |
| **CPU 内部异构** | 大小核调度 + 热点神经元驻留 GPU（激活局部性） | PowerInfer（上交） |
| **Delegate 分区** | 编译期把支持的区域下沉 NPU，其余 CPU 兜底 | ExecuTorch |
| **垂直整合** | 模型架构为 NPU 定制（KV cache 更新、2-bit 量化）+ 私有工具链 | Apple（ANE 路径） |
| **工程级优化** | KV cache 布局重排减少 transpose（CPU +25%/GPU +20%）、prefill/decode 权重共享 | Google AI Edge |

## 4. 开放问题（研究机会）

1. **decode 阶段的根本加速**：即使 NPU 全部利用，GEMV 带宽受限的本质不变。出路可能在投机解码（→ [[投机解码与加速]]）、模型架构（Sliding window / 线性注意力 / KV 压缩）
2. **统一 NPU 编译层**：是否存在"LLM 推理领域的 OpenXLA"？动态 shape + KV cache 的标准化抽象是关键缺口；MLIR 生态可能有戏（待调研）
3. **实测基准的缺失**：厂商宣传 TOPS，论文测 token/s，缺乏统一的"端侧能效"基准（GSMA Intelligence 正在推动 chipset benchmark，见其 [On-Device AI 报告](https://www.gsmaintelligence.com/research/on-device-ai-mobile-network-filler-or-saviour)）
4. **热约束下的持续性能**：EPFL 数据显示 15 秒内冲到 90°C——峰值性能 vs 持续性能的差距在端侧被热设计放大，调度策略需要热感知

## 5. 来源

- 主线：[EPFL: Efficient Deployment of Vision-Language Models on Mobile Devices (arXiv:2507.08505)](https://arxiv.org/pdf/2507.08505)——含开源 benchmarking pipeline
- [Apple Intelligence Foundation Models 技术报告](https://machinelearning.apple.com/research/introducing-apple-foundation-models)（ANE 上的 KV cache 更新）
- [ExecuTorch 后端与 delegate 机制文档](https://docs.pytorch.org/executorch/main/backends-overview.html)
- [MNN NPU 后端文档](https://github.com/alibaba/MNN/wiki/npu)（shapeMutable=false 约束、离线构图流程）
- [Google AI Edge Gemma 3 优化博客](https://developers.googleblog.com/gemma-3-on-mobile-and-web-with-google-ai-edge/)（KV cache 布局、权重共享）
- mllm-NPU、PowerInfer 论文待精读 → 见 [[论文与报告清单]]
