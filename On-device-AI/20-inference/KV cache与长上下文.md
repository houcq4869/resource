# KV cache 与长上下文

> 2026-10-23 初稿。权重之后的第二道内存墙：上下文越长，KV cache 越大。
> 相关：[[量化技术]]、[[异构调度与NPU利用]]、[[模型-硬件协同设计]]

## 0. TL;DR

- KV cache 大小 ∝ 序列长度 × 层数 × KV 头数 × 头维度，**线性增长且每步读写**——端侧它同时吃内存容量和带宽
- 优化技术分四类（驱逐/选择/合并/压缩）+ 系统层（分页）+ 架构层（MLA/GQA/滑窗/线性注意力）
- **生产落地的教训**：MLSys 2025 实证发现压缩后的 KV cache 反而可能导致端到端延迟变长（FlashAttention/PagedAttention 内核不为压缩布局优化 + 压缩改变输出长度分布）——**压缩必须与内核协同设计**
- 端侧最有前途的路线是**架构层**：DeepSeek MLA（低秩潜在缓存）、Apple 5:3 分块 KV 共享（-37.5%）、Gemma/其他模型的滑窗混合——在训练时就决定 cache 形态（→ [[模型-硬件协同设计]]）

## 1. 问题定义

自回归解码时，attention 的 Key/Value 缓存避免重算历史 token：

```
KV cache size ∝ N(序列长度) × L(层数) × H_kv(KV头数) × d(头维度) × 2(K和V) × bytes
```

端侧示例：3B 模型（≈26 层、GQA 4 KV 头、128 维）FP16 下 8K 上下文 ≈ 100–200MB 级；随着多模态（图片 token 数千级）与 Agent 记忆（长会话）需求，上下文预算向 32K+ 走，KV cache 会追上权重成为第一大内存项。

EPFL 实测中 VLM 推理内存占用达设备内存的 32–55%，其中 KV cache 是主要动态部分（mllm 的更大 KV 布局 vs llama.cpp 的对比）（[arXiv:2507.08505](https://arxiv.org/pdf/2507.08505)）。

## 2. 系统层：分页内存管理

**PagedAttention**（vLLM，OSD award 工作，[综述 arXiv:2506.21901](https://arxiv.org/html/2506.21901)）：

- 借鉴操作系统虚拟内存：逻辑 cache 页 → 物理块映射表，按需分配小块
- 消除预分配浪费和碎片；块共享（shared system prompt 场景）避免重复存储
- 代价：非连续内存需要专门的 paged kernels

**端侧适配的现实**：分页是为云端多请求并发设计的；端侧 batch=1、单请求，分页的主要收益变为"与 NPU 固定内存规划的折中"（小块分配 vs 整段预分配）。ExecuTorch 的 off-graph KV cache 布局（flat/ring/cell）、Google AI Edge 的 KV 布局重排（CPU 延迟 -25%/GPU -20%）是端侧版的同类工作——**布局优化比通用分页更贴近端侧痛点**。

## 3. 压缩技术四分类

（分类框架来自 [NTU 综述幻灯](https://arbor.ee.ntu.edu.tw/static/gm/20250714_黃彥傑.pdf) 与 [arXiv:2508.06297](https://arxiv.org/html/2508.06297)）

| 类别 | 思路 | 代表工作 |
|---|---|---|
| **驱逐 Eviction** | 满时丢弃"不重要"的 token | H2O（attention 分数贪心）、FastGen、PyramidInfer、RazorAttention |
| **选择 Selection** | 每个 query 只取相关子集 | SnapKV、InfiniGen（OSDI'24）、PQCache |
| **合并 Merging** | 相似 KV 合并为代表向量 | KVMerger、DMC |
| **压缩 Compression** | 每个 KV 更小的表示 | **KVQuant**（量化）、Palu（低秩） |

关键技术点：

- **Attention sink**（StreamingLLM）：初始 token 持续获得高注意力权重且与语义无关——"保留 sink + 滑窗"就能外推长序列。这是理解 KV 重要性的基础发现
- **KVQuant** 的细节体现 KV 量化的独特难点：Key 有 distinct outlier channels（RoPE 引入），所以 **Key 按 channel、Value 按 token** 量化 + 非均匀编码 + outlier 隔离，可做到 2-bit
- llama.cpp 落地版：`--cache-type-k/v q8_0/q4_0`（需 `-fa` flash attention）——工程上 K 量化比 V 更伤精度，需分开配置

## 4. 生产环境的教训（重要）

[MLSys 2025: Rethinking KV Cache Compression](https://proceedings.mlsys.org/paper_files/paper/2025/file/26289c647c6828e862e271ca3c490486-Paper-Conference.pdf) 的实证发现：

1. 压缩减少内存，但 **FlashAttention/PagedAttention 内核不为稀疏/压缩布局优化**，吞吐反而可能次优
2. 压缩 cache 可能**改变输出长度分布**（生成变长），端到端延迟不降反升
3. 整体性能好看但**个体样本方差大**——生产可用性存疑

推论到端侧：手机上没有"再加一块 GPU"的退路，**内核-布局-算法协同设计**比云端更刚性（Google AI Edge 的布局重排+内核配套就是正面案例）。

## 5. 架构层：训练时就决定 cache 形态

| 方案 | 机制 | 效果 | 端侧适配度 |
|---|---|---|---|
| **GQA/MQA** | 多 Q 头共享 KV 头 | 数倍压缩，已是标配 | ✅ 无损、无额外计算 |
| **MLA**（DeepSeek-V2） | 低秩联合压缩，cache 存潜在向量，推理时展开 | 大幅压缩，支持 128K | ⚠️ 展开仍在带宽路径上（[arXiv:2407.18003](https://arxiv.org/html/2407.18003v4) 指出未根本解决带宽） |
| **滑窗/混合注意力** | 局部窗口 + 少量全局 | cache 有上界 | ✅ 端侧主流（Gemma 等采用） |
| **线性注意力**（Mamba/RWKV/线性 Transformer） | 递归状态替代显式 cache | cache 变 O(1) 状态 | 🟡 与 NPU 的静态图反而契合，但质量/生态仍在追赶（[综述 arXiv:2507.19595](https://arxiv.org/html/2507.19595v2)） |
| **Apple 5:3 分块 KV 共享** | 模型分两块，block2 复用 block1 末层 KV | **-37.5% KV + 显著改善 TTFT**（[Apple FM 2025](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates)） | ✅ 专为端侧设计的范例 |

## 6. 端侧实践汇总

| 玩家 | KV cache 优化 |
|---|---|
| Apple | 5:3 分块共享；专门开发 ANE 上的高效 KV 更新路径（ANE 对动态写入不友好，见 [[异构调度与NPU利用]]） |
| Google AI Edge | 布局重排减少 transpose/reshape（CPU -25%/GPU -20%）；GPU 原地更新算子 |
| llama.cpp | KV 量化（q8_0/q4_0）+ flash attention |
| ExecuTorch | off-graph KV cache 布局（flat/ring/cell + 共享池） |
| 学术前沿 | KVQuant 2-bit、Palu 低秩、SnapKV 选择 |

## 7. 关键洞察

1. **云端技术不能直接搬**：分页为并发而生、压缩为 GPU 显存而生；端侧的关键词是"布局 + 内核协同 + 有上界"
2. **架构层的收益最干净**：GQA/滑窗/MLA 在训练时定形，推理侧零额外逻辑；后处理压缩则处处是精度-延迟权衡
3. **KV cache 是模型-硬件协同设计的核心变量**：Apple 的分块共享直接改变了"什么模型适合端侧"的答案
4. **多模态和 Agent 是长上下文的真正推手**：一张图几百上千 token、一轮工具调用往返几千 token——端侧上下文预算从 4K 向 32K 演进，KV cache 权重比随之上升

## 8. 开放问题

- [ ] 端侧 KV cache 的统一基准：现有评测全部基于 A100/H100，手机内存带宽下的四类技术对比缺失
- [ ] KV 压缩 × 投机解码的交互：draft 阶段的 cache 一致性
- [ ] Agent 场景的持久 KV（跨会话复用）与隐私（cache 里的用户数据残留）
- [ ] 线性注意力模型的 NPU 映射是否真的更优（递归状态 vs NPU 静态图的匹配度）

## 9. 来源

- [A Survey of LLM Inference Systems (arXiv:2506.21901)](https://arxiv.org/html/2506.21901)——分页/驱逐/卸载/持久化的系统视角
- [KV Cache Compression Review (arXiv:2508.06297)](https://arxiv.org/html/2508.06297)
- [KV Cache Management Survey (arXiv:2412.19442)](https://arxiv.org/html/2412.19442v3)——token/模型/系统三层分类 + [Awesome 列表](https://github.com/TreeAI-Lab/Awesome-KV-Cache-Management)
- [Keep the Cost Down (arXiv:2407.18003)](https://arxiv.org/html/2407.18003v4)——PagedAttention/MLA 深入分析
- [Rethinking KV Cache Compression (MLSys 2025)](https://proceedings.mlsys.org/paper_files/paper/2025/file/26289c647c6828e862e271ca3c490486-Paper-Conference.pdf)——生产环境实证
- [Efficient Attention Mechanisms Survey (arXiv:2507.19595)](https://arxiv.org/html/2507.19595v2)——线性/稀疏注意力
- [Apple FM 2025 更新](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates)——5:3 分块 KV 共享
- [Google: Gemma 3 on mobile](https://developers.googleblog.com/gemma-3-on-mobile-and-web-with-google-ai-edge/)——KV 布局优化实测数据
