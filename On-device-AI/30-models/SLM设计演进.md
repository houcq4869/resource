# SLM 设计演进

> 2026-10-23 初稿。小型语言模型（~0.1B–4B）的设计哲学：架构、数据、训练配方三条线。
> 相关：[[模型-硬件协同设计]]、[[量化技术]]、[[端侧AI全景图]]

## 0. TL;DR

- SLM 设计的三条主线：**架构微调**（MobileLLM：深瘦 > 浅胖、层复用）、**数据为王**（Phi-4：合成数据超越教师模型）、**配方工程**（Phi-4-Mini-Reasoning：四步 CoT 配方让 3.8B 数学推理超过 7B 蒸馏模型）
- 反直觉发现：**参数量不是唯一变量**——MobileLLM 证明架构在 sub-billion 尺度影响巨大；Phi-4 证明数据质量可与算力 scaling 等价交换
- 一个反例值得记住：MobileLLM 尝试从 LLaMA-2-7B 蒸馏，**精度不升反降**且训练慢 2.6–3.2×——蒸馏不是银弹
- Apple 的路线提醒我们：SLM 的终点不是"通用小模型"，而是**系统中的角色模型**（OS 服务 + LoRA 适配器按任务切换）

## 1. 架构线：MobileLLM 的启示

[MobileLLM (Meta, ICML 2024)](https://arxiv.org/html/2402.14905v2) 针对 sub-billion（125M–1.5B）系统实验：

| 设计选择 | 收益 | 备注 |
|---|---|---|
| SwiGLU FFN | +1.3% | 大模型经验直接迁移 |
| **深瘦架构**（30–42 层 vs 惯例 12 层） | 显著 | 反 Kaplan scaling law 直觉——参数量相近时深 > 宽 |
| 输入/输出 embedding 共享 | 省 ~10–12% 参数 | 125M 模型 embedding 占 20%+（7B 仅 3.7%）→ 省下的参数换成更多层 |
| GQA（KV 头 1/4 于 Q 头） | +0.4% | 本质又是一种权重复用 |
| **立即块级层共享**（MobileLLM-LS） | +0.7–1.1% | 同一块连续执行两次——因为 SRAM（~20MB）只放得下一个 block，立即复用可避免权重在 SRAM↔DRAM 间搬运（**硬件感知设计**） |

配套发现：MobileLLM 在 **API 调用任务上接近 LLaMA-v2-7B**——小模型足以覆盖端侧常见用例（结构化任务），差距在开放世界知识。

## 2. 数据线：Phi 系列

[Phi-4 技术报告（14B）](https://arxiv.org/html/2412.08905v1) 核心主张：**数据质量可与模型/数据规模 scaling 等价交换**。

- 训练数据 40% 是合成数据（多智能体 prompting、自我修订工作流、指令反转生成），仅 30% 来自 web
- "教科书级"种子的筛选 + 课程学习 + pivotal token search 构造 DPO 对
- 结果：**STEM QA 超过其教师 GPT-4**——证明不只是蒸馏，合成数据管线本身在创造能力
- 架构几乎照抄 phi-3（创新全在数据与后训练）

对端侧的意义：SLM 的知识密度由数据管线决定——这解释了为什么 3B 级模型能做到"够用"的通用质量。

## 3. 配方线：小模型的推理能力

[Phi-4-Mini-Reasoning (3.8B)](https://arxiv.org/pdf/2504.21233) 四步配方解锁小模型 CoT 推理：

```
1. 大规模 mid-training（蒸馏长 CoT 数据）
2. 高质量长 CoT 的 SFT
3. Rollout DPO（精选偏好集）
4. 可验证奖励的 RL
```

结果：Math-500 上超过 DeepSeek-R1-Distill-Qwen-7B 3.2 分、超过 R1-Distill-Llama-8B 7.7 分。

**端侧视角的张力**：长 CoT = 更多输出 token = 更长 decode 时间（端侧最贵的阶段）。推理能力与端侧延迟天然冲突，投机解码（结构化推理文本可预测性高）是主要缓解手段（见 [[投机解码与加速]]）。

## 4. 训练路线之争：从头训 vs 蒸馏

| 路线 | 证据 | 适用 |
|---|---|---|
| 从头训练 | MobileLLM（1T token）；Gemma/Qwen 系 | 有算力的大厂，追求架构自由 |
| 云端大模型蒸馏 | DeepSeek R1 蒸馏模型数天内上端侧（Qualcomm 白皮书）；Phi-4-Mini-Reasoning 的 CoT 数据 | 快速跟进前沿能力 |
| 蒸馏无效的反例 | MobileLLM 用 LLaMA-2-7B 做 KD：精度持平或更差，训练慢 2.6–3.2× | sub-billion + 通用预训练场景 |

结论：**蒸馏在"能力注入"（推理风格、领域知识）时有效，在"基础语言能力"上不如直接 next-token 训练**。

## 5. 当前 SLM 架构收敛形态

（综合 [ACL 2025 survey](https://aclanthology.org/2025.acl-long.718.pdf) 与各家模型）

```
标准 SLM ≈ GQA + SwiGLU/gated FFN（FFN ratio 2–8）+ RMSNorm
         + 词表 50K–260K + RoPE + 滑窗/全局交替注意力（Gemma 式）
差异化变量 ≈ KV cache 形态（Apple 5:3 共享 / MLA）
          + 嵌套结构（Gemma 3n MatFormer，→ [[模型-硬件协同设计]]）
          + 激活稀疏（SPARC）、层增强（AltUp/LAuReL）
```

代表模型定位：

| 模型 | 规模 | 特色 |
|---|---|---|
| Apple 端侧 FM | ~3B | 2-bit 3.7bpw + LoRA 适配器热切换；不追求世界知识，专注摘要/提取/改写（[2025 更新](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates)） |
| Gemma 3n E2B/E4B | 有效 2B/4B | 多模态 + MatFormer 嵌套 + PLE 外置（见 [[多模态端侧模型]]） |
| Phi-4-mini | 3.8B | 数据配方驱动，推理强化版超 7B 蒸馏模型 |
| Qwen 2.5/3 小型号 | 0.5B–4B | 开源生态最全，端侧社区适配最广 |
| MobileLLM | 125M–1.5B | sub-billion 架构研究的标杆 |

## 6. 关键洞察

1. **SLM 的价值锚点是"角色"而非"全能"**：Apple 明确声明端侧模型不做世界知识和高级推理——把 SLM 当系统组件（配合云、配合 RAG、配合适配器）而非缩小版 LLM
2. **能力来自配方，规模只是载体**：Phi 系两次证明（数据质量、CoT 配方）小模型上限远未到顶
3. **sub-billion 是架构创新的黄金区**：embedding 占比、SRAM 约束、层共享等在大模型中不显著的因素在此尺度全部激活
4. **评测陷阱**：ACL survey 指出 SLM 的 in-context learning 能力仍受限——benchmark 分数（多为 0-shot/few-shot）可能高估真实 Agent 场景（长指令、多工具）表现

## 7. 开放问题

- [ ] 端侧 SLM 的"足够好"标准：任务级评测（App 集成）vs 学术 benchmark 的差距
- [ ] 适配器（LoRA）生态：端侧快速切换的工程标准（Apple 已做，开源侧空白）
- [ ] 长输出（CoT）与端侧延迟的矛盾如何收敛：配方端压缩推理长度？
- [ ] 小模型 + RAG vs 稍大模型：知识获取的帕累托前沿在哪

## 8. 来源

- [MobileLLM (ICML 2024)](https://arxiv.org/html/2402.14905v2) / [PMLR 页面](https://proceedings.mlr.press/v235/liu24ce.html)
- [Phi-4 Technical Report (arXiv:2412.08905)](https://arxiv.org/html/2412.08905v1)
- [Phi-4-Mini-Reasoning (arXiv:2504.21233)](https://arxiv.org/pdf/2504.21233)
- [Demystifying SLMs for Edge Deployment (ACL 2025)](https://aclanthology.org/2025.acl-long.718.pdf)
- [Apple FM 2025 Updates](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates)
- [Qualcomm 终端侧推理白皮书 2025](https://www.qualcomm.cn/content/dam/qcomm-martech/dm-assets/documents/files/ai_whitepaper/ai_whitepaper_2025.pdf)——R1 蒸馏模型一周内上端侧
- [SLM Survey (arXiv:2505.19529)](https://arxiv.org/html/2505.19529)
