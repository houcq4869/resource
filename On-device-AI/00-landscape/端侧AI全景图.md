# 端侧AI全景图

> 初稿：2026-10-23。基于第一轮网络调研的摘要，各层细节在对应目录深入展开。
> 来源见文末；关键论断均已标注出处。

## 1. 定义与范围

**端侧AI（On-Device AI）**：AI 推理在终端设备（手机、PC、汽车、可穿戴、IoT）本地执行，而非云端。核心价值：

- **即时性**：无网络往返延迟
- **隐私**：数据不出设备（结合 Private Cloud Compute / 联邦学习等范式）
- **离线可用**、**成本**（规避云推理费用）、**个性化**（本地上下文）

注意与"边缘计算（Edge Computing）"的区别：端侧指设备本身，边缘计算还包含近端服务器。行业共识是**混合架构（Hybrid AI）**——大部分任务端云分工协作，而非纯端侧（[Qualcomm 白皮书 2025](https://www.qualcomm.cn/content/dam/qcomm-martech/dm-assets/documents/files/ai_whitepaper/ai_whitepaper_2025.pdf)）。

## 2. 市场与产业概况

| 数据点 | 数值 | 来源 |
|---|---|---|
| 端侧AI市场规模（2025） | ~107 亿美元 | [Grand View Research](https://www.grandviewresearch.com/industry-analysis/on-device-ai-market-report) |
| 预测（2033） | 755 亿美元，CAGR 27.8% | 同上 |
| 边缘AI SoC 出货（2030 预测） | 87 亿颗、收入 1029 亿美元 | [SHD Group 2025 报告](https://theshdgroup.com/wp-content/uploads/2025/07/Edge-AI-2025-Report-070125-final-1.pdf) |
| 边缘AI 加速硬件市场 | 2024 ~$43B → 2029 ~$89.7B | Omdia（转引自 [NXP 白皮书](https://www.nxp.com/docs/en/white-paper/OMIDIA-REPORT-2024-NXP.pdf)） |
| 2025 旗舰手机 NPU 算力 | 35–85 TOPS，向 100 TOPS 迈进 | [Futuresource](https://www.futuresource-consulting.com/the-source/industry-pulse/ai-is-trading-the-cloud-for-your-pocket-starting-with-15-billion-smartphones/) |
| AI PC 定义 | NPU ≥ 40 TOPS；2025 年占新机 <10%，预计 2030s 初过半 | [IDTechEx](https://www.idtechex.com/en/research-report/ai-chips-for-edge-applications/1148) |

要点：

- **手机是当前最大载体**（2025 年全球出货 ~15 亿部），AI PC 是增长最快的第二战场；手表、TWS 耳机、AR 眼镜开始配备独立 NPU（Snapdragon Wear Elite 达 12 TOPS）。
- 行业已明确**抛弃"唯 TOPS 论"**，转向关注实际能效与软件生态（[智东西：芯片六巨头决战手机AI芯片](https://zhidx.com/p/487563.html)）。
- 边缘芯片格局与数据中心不同：**没有 NVIDIA 式垄断**，"一切都在长得像手机 SoC"——异构集成 CPU+GPU+NPU 是主流形态（Omdia）。

## 3. 技术栈分层图景

```
┌─────────────────────────────────────────────────┐
│ 应用层：端侧 Agent / RAG / 翻译 / 影像 / UI      │  → 40-hybrid/
├─────────────────────────────────────────────────┤
│ 模型层：SLM (1-4B) / 端侧多模态 / MoE            │  → 30-models/
├─────────────────────────────────────────────────┤
│ 推理系统：框架 / 量化 / KV cache / 投机解码 / 调度│  → 20-inference/
├─────────────────────────────────────────────────┤
│ 硬件层：CPU / GPU / NPU 异构 SoC + 厂商 SDK      │  → 10-hardware/
└─────────────────────────────────────────────────┘
```

### 3.1 硬件层（详见 10-hardware/）

- 主要玩家：高通（Hexagon NPU，80+ TOPS）、苹果（ANE，垂直整合）、联发科（第 7 代 NPU，面向 Transformer）、华为（麒麟+昇腾）、Arm（Ethos IP）、三星、小米（玄戒 O1）。
- **碎片化是核心痛点**：每家 NPU 一套 SDK（QNN / Core ML / NeuroPilot / HiAI / NNAPI / RKNN）。开源框架 MNN 为覆盖 NPU 需同时实现 5 种后端（[MNN NPU 文档](https://github.com/alibaba/MNN/wiki/npu)）。

### 3.2 推理系统层（详见 20-inference/，第一深入层）

- 主流框架：**llama.cpp**（GGUF、可移植性最广）、**MLC-LLM**（TVM 编译器路线、跨平台一致）、**MLX**（Apple 平台性能最优）、**MNN / ncnn**（国产、移动端积累深）、execuTorch（Meta）、LiteRT + Google AI Edge（Google）。
- 关键实证：EPFL 在 OnePlus 13R 上实测 VLM 推理，**CPU 占用 600–800% 而 GPU/NPU 基本闲置**，纯 CPU 路线功耗 10–12W/90°C，GPU 卸载路线仅 1.3W/60°C，差距近 8 倍（[arXiv:2507.08505](https://arxiv.org/pdf/2507.08505)）。
- Apple Silicon 上框架对比：MLX 对 sub-14B 模型比 llama.cpp 快 20–87%（[arXiv:2511.05502](https://arxiv.org/abs/2511.05502)）。

### 3.3 模型层（详见 30-models/）

- 代表模型：Apple 端侧 ~3B（2-bit 量化，均 3.7 bits/weight）、Gemma 3n（原生多模态）、Phi-4、Qwen 小模型系列、gpt-oss-20b（MoE，每 token 仅激活 5–10% 参数）。
- ACL 2025 对 60+ SLM 的系统研究：SOTA SLM 已在通用任务上超过 7B 模型，但**上下文学习能力仍受限**，优化空间在动态任务路由、模型-硬件协同设计、词表/KV cache 压缩（[ACL 2025](https://aclanthology.org/2025.acl-long.718.pdf)）。

### 3.4 云端协同与应用层（详见 40-hybrid/）

- 范式共识：端云协作学习（on-device small model × cloud large model），分数据级/特征级/参数级协同（[综述 arXiv:2504.15300](https://arxiv.org/html/2504.15300)）。
- 端侧能力栈快速标准化：Google AI Edge 提供端侧 RAG 与 Function Calling 库；Apple Foundation Models 框架向三方 App 开放系统级 ~3B 模型（guided generation、tool calling）；MCP 协议开始进入端侧。

## 4. 三个关键张力（调研主线索）

1. **NPU 利用率悖论**——硬件算力已就位（35–85 TOPS），但现有推理框架大多跑在 CPU 上，NPU 闲置。根因是 NPU 编程模型碎片化 + LLM 解码阶段 GEMV 负载与 NPU 架构不匹配（arXiv:2507.08505）。→ 深入见 [[异构调度与NPU利用]]
2. **从"压缩云端模型"到"为端侧设计"**——Apple 3B 的 5:3 分块 KV 共享（省 37.5% KV cache）、Gemma 3n 的 MatFormer、MoE 端侧化，模型架构开始围绕端侧内存与算力约束原生设计。→ 深入见 [[模型-硬件协同设计]]
3. **开发者生态分层**——苹果垂直整合最完整（Foundation Models 框架 + MLX + ANE）；安卓阵营厂商各自为战，跨平台部署成本高。→ 深入见 [[NPU工具链与碎片化问题]]

## 5. 主要来源

- 综述：[A Comprehensive Survey on On-Device AI Models (ACM 2025)](https://dl.acm.org/doi/10.1145/3724420)
- 综述：[Collaborative Learning of On-Device Small Model and Cloud-Based Large Model (arXiv:2504.15300)](https://arxiv.org/html/2504.15300)
- 实测：[Efficient Deployment of VLMs on Mobile Devices, EPFL (arXiv:2507.08505)](https://arxiv.org/pdf/2507.08505)
- 实测：[Local LLM Inference on Apple Silicon (arXiv:2511.05502)](https://arxiv.org/abs/2511.05502)
- 官方：[Apple Foundation Models 2025 Updates](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates) / [2024 原始技术报告](https://machinelearning.apple.com/research/introducing-apple-foundation-models)
- 官方：[Qualcomm 终端侧推理白皮书 2025](https://www.qualcomm.cn/content/dam/qcomm-martech/dm-assets/documents/files/ai_whitepaper/ai_whitepaper_2025.pdf)
- 官方：[Google AI Edge SLM 博客](https://developers.googleblog.com/en/google-ai-edge-small-language-models-multimodality-rag-function-calling/)
- 市场报告：Grand View / SHD Group / IDTechEx / Omdia / Futuresource（链接见第 2 节表格）
