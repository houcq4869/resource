# NPU 工具链与碎片化问题

> 2026-10-23 初稿。端侧 AI 落地最大的非技术障碍：每家 NPU 一套 SDK。
> 相关：[[NPU架构对比]]、[[推理框架横向对比]]、[[异构调度与NPU利用]]

## 0. TL;DR

- 现状：**QNN（高通）/ Core ML（Apple）/ NeuroPilot（联发科）/ HiAI（华为）/ 三星 ONE / RKNN（瑞芯微）各占一隅**；通用框架 MNN 为覆盖 NPU 需实现 5 种后端
- 标志性事件：**Android NNAPI 在 Android 15 被弃用**——Google 亲手承认"统一硬件抽象层"路线在生成式 AI 时代失败，转向 TFLite in Play Services + AICore（系统内置 Gemini Nano）
- 统一化的三条现役路线：**算子标准**（TOSA）、**编译器统一**（MLIR/IREE——"AI 界的 LLVM"）、**开放硬件 ISA**（Google Coral NPU，RISC-V + ML-first）
- 工程现世的解法是 **delegate 分区**（ExecuTorch）：编译期把支持的子图下沉给各厂商库，其余 CPU 兜底——不消除碎片化，但让它变得可管理

## 1. 碎片化的全景

### 1.1 为什么会碎片化

1. **NPU 是私有 ISA**（除 Coral 外）：Hexagon 三条 ISA、ANE 无 ISA——编程模型必然由厂商定义（见 [[NPU架构对比]]）
2. **编译期绑定**：NPU 偏好静态图/静态 shape，模型必须**离线编译成命令流/目标产物**（MNN QNN 离线模式按 SOC ID + Hexagon arch 生成 `.bin`）——与"一份 GGUF 走天下"的开源生态根本冲突
3. **性能调优不可移植**：microtile 切法、TCM 布局、算子融合策略都是 per-vendor 私有知识
4. **商业动机**：工具链是差异化护城河（Omdia："软件支持是 NPU 新进入者的最大壁垒"）

### 1.2 碎片化的代价（实证）

- MNN 的 QNN 后端使用流程：host 交叉编译 + 指定 SOC ID/HEXAGON_ARCH + 推送 4 个 QNN so + ADSP_LIBRARY_PATH 配置——**开发者为一个芯片做的事，换芯片全部重来**（[MNN 文档](https://github.com/alibaba/MNN/wiki/npu)）
- EPFL 实测：主流开源框架干脆放弃 NPU（CPU 600-800%、NPU 零调用），见 [[异构调度与NPU利用]]
- Omdia 观察：多家公司"成功流片，却拿不到开发者"——芯片好造，生态难养

### 1.3 NNAPI 之死

[Android NNAPI 于 Android 15 弃用](https://developer.android.com/ndk/guides/neuralnetworks/migration-guide)。官方理由：transformer/扩散模型迭代太快，系统级 API 跟不上。替代路径：

- TFLite in Play Services（可更新运行时）
- AICore：系统内置 Gemini Nano，App 经 API 消费——**Google 也转向"系统服务路线"**（见 [[推理框架横向对比]] §1.3）
- Samsung ONE 1.30 同步把 NNAPI 降级为测试用途

解读：NNAPI 的失败不是抽象层技术不行，而是**硬件加速抽象必须随模型形态快速演进，而 OS API 冻结周期太长**。

## 2. 统一化的三条路线

### 2.1 算子标准：TOSA

Arm 主导的 Tensor Operator Set Architecture：用**标准算子集 + 标准行为语义**约束编译目标（Ethos-U85 全合规）。模型 → TOSA 图 → 各后端 lowering。局限：算子集覆盖跟不上新模型结构。

### 2.2 编译器统一：MLIR / IREE

（[Google Coral 编译器文档](https://developers.google.com/coral/guides/software/mlir-iree-compilers) / [iree.dev](https://www.iree.dev/)）

```
JAX(StableHLO) ─┐
PyTorch(torch-mlir) ─┼→ MLIR 统一管线（linalg/TOSA dialect）→ 各目标代码
LiteRT(TOSA) ─┘                    （CPU/GPU/NPU/FPGA, Vulkan/SPIR-V/...）
```

- **MLIR**：LLVM 生态的多层 IR，明确为"解决 AI/ML 与异构加速器的碎片化"而生
- **IREE**：MLIR 上的端到端编译+运行时，已入 LF AI & Data 基金会；支持动态 shape/流控制；嵌入式二进制可低至 30KB；AMD 已提交 IREE 版 SDXL 到 MLPerf
- 对 LLM 的关键意义：**动态 shape 一等公民**——正是 NPU 离线编译最痛的点
- 现实约束：IREE 的 NPU 后端仍需各厂商写插件；"统一 IR"≠"统一性能"

### 2.3 开放硬件：Coral NPU

Google 开源 RISC-V NPU IP：把张量/向量/标量融进**一条公开 ISA**，C 可编程、MLIR 工具链直达——从物理层消灭"私有命令流"。定位 wearable/IoT（见 [[NPU架构对比]] §2.5）。观察价值大于出货价值：**如果开源 NPU 能复制 RISC-V CPU 的生态路径，碎片化将从根部瓦解**。

## 3. 现世工程解法：delegate 分区

ExecuTorch 的模式（见 [[推理框架横向对比]]）：

- 编译期：partitioner 把模型切成"后端支持的子图"（下沉给 QNN/Core ML/MediaTek NPU/Ethos-U）+ "不支持的部分"（portable CPU 内核兜底）
- 运行时：一份 `.pte`，部分加速、渐进覆盖
- 本质：**把"适配每家 NPU"从框架维护者的负担变成厂商自己的责任**（厂商为自己的芯片写 delegate）——商业上顺人人性，所以有效

MNN 的多后端（QNN/CoreML/NNAPI/HiAI/RKNN + 插件化）是同一思路的开源实现，代价是维护五套后端。

## 4. 分层现状总结

| 层 | 现状 | 统一度 |
|---|---|---|
| 模型交换格式 | GGUF 事实标准 / ONNX 广泛支持 | 🟢 较好 |
| 图编译/IR | MLIR 渐成共识，TOSA/StableHLO 竞合 | 🟡 进行中 |
| 运行时 | LiteRT / ExecuTorch / MNN / llama.cpp 并立 | 🟡 分层竞争 |
| **NPU 驱动/SDK** | **每厂商私有** | 🔴 碎片化核心 |
| 编程 ISA | 私有（Hexagon 半开放）/ Coral 开源试验 | 🔴 |

## 5. 关键洞察

1. **碎片化在"往下"收敛、在"往上"被绕开**：上层用系统服务（Foundation Models/AICore）让 App 开发者无感，中层用 delegate 管理差异，底层（NPU ISA）反而更封闭——**统一的努力都在中层**
2. **NNAPI 之死是重要信号**：静态硬件抽象跑不过模型形态的演化速度；可更新运行时（Play Services）+ 系统模型成为新正统
3. **MLIR 是当前最有希望的"AI LLVM 时刻"**：但历史提示 CUDA 的霸主地位从未被编译器击败过——统一编译器必要但不充分
4. **中国生态的双面性**：碎片化更重（HiAI/MNN/ONE/MindSpore Lite 并立），但也诞生了 MNN 这种"以一己之力适配五家 NPU"的整合者

## 6. 开放问题

- [ ] IREE 在旗舰手机 NPU 上的实际落地案例（当前后端集中在 GPU/CPU/部分 DSP）
- [ ] Coral NPU 是否会出现"RISC-V 生态级"采纳
- [ ] LLM 动态 shape + KV cache 的标准化抽象（谁定义"NPU 友好"的 LLM 图规范？）
- [ ] 端侧模型的"一次编译、处处运行"是否有商业动力（厂商答案大概率是"否"）

## 7. 来源

- [Android NNAPI 迁移指南（弃用公告）](https://developer.android.com/ndk/guides/neuralnetworks/migration-guide)
- [MNN NPU 后端文档](https://github.com/alibaba/MNN/wiki/npu)
- [Google Coral: MLIR and IREE compilers](https://developers.google.com/coral/guides/software/mlir-iree-compilers) / [Coral NPU 介绍](https://developers.google.com/coral/guides/intro)
- [IREE 官网](https://www.iree.dev/) / [openxla/iree](https://github.com/openxla/iree)
- [Arm Ethos-U85 Technical Overview（TOSA 合规）](https://documentation-service.arm.com/static/66617778d72aaf32efecd23f)
- [Samsung ONE Release 1.30.0](https://github.com/Samsung/ONE/releases/tag/1.30.0)（NNAPI 降级）
- [Omdia Market Radar（软件是 NPU 壁垒）](https://www.nxp.com/docs/en/white-paper/OMIDIA-REPORT-2024-NXP.pdf)
- [ExecuTorch 后端文档（delegate 分区）](https://docs.pytorch.org/executorch/main/backends-overview.html)
