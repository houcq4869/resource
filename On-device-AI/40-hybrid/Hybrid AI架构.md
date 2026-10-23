# Hybrid AI 架构（云端协同）

> 2026-10-23 初稿。端云分工是端侧 AI 的"默认架构"而非可选项——本篇梳理分工的粒度、策略与代表系统。
> 相关：[[端侧RAG与个性化记忆]]、[[隐私与端侧学习]]、[[投机解码与加速]]、[[SLM设计演进]]

## 0. TL;DR

- 行业共识（Qualcomm "The Future of AI is Hybrid"、Apple 端云双模型、综述 [arXiv:2504.15300](https://arxiv.org/html/2504.15300)）：**端侧管即时/隐私/个性化，云端管复杂推理与世界知识**
- 学术分类（[ACM CSUR 2025 协同综述](https://dl.acm.org/doi/10.1145/3838593)）按粒度分三层：**任务级分配**（整个请求路由）→ **任务级切分**（子任务分解）→ **token 级混合**（关键 token 上云）
- 代表性数据：MINIONS 协议在长文档推理上**省 5.7× 云成本、恢复 97.9% 云模型性能**；token 级路由用 0.5B 端模型 + <7% 上云 token 拿到 +60% CommonsenseQA
- Apple 的实现是"架构级"的：端侧 3B + PCC 服务器 PT-MoE，App 开发者用统一 API 无感切换（见 [[隐私与端侧学习]]）

## 1. 为什么要协同（约束分析）

| 端侧短板 | 云侧短板 |
|---|---|
| 模型容量上限（3-8B） | 延迟（网络 RTT）、成本（token 计费） |
| 世界知识/复杂推理弱 | 隐私（数据出域）、离线不可用 |
| 内存/热/电量预算 | 个性化（无本地上下文） |

协同的本质是**把请求的"难度 × 隐私敏感度 × 时延敏感度"三维映射到端-云-边缘的资源谱上**。

## 2. 协同粒度的三层分类

（框架来自 [ACM CSUR 协同综述](https://dl.acm.org/doi/10.1145/3838593) 与 [arXiv:2504.15300](https://arxiv.org/html/2504.15300) 的数据级/特征级/参数级分类）

### 2.1 任务级分配（Task Assignment）

整请求路由：端侧先判断（或小模型先答），不确定/高难度再上云。

- 简单可靠，是当前产品形态（Apple Intelligence、Gemini）的主干
- 关键问题：**路由判据**（prompt 难度估计、置信度、隐私标记）与**失败回退**

### 2.2 任务级切分（Task Division）

云模型把任务分解成端侧可执行的子任务。代表工作 **MINIONS**（[Narayan et al., PMLR 2025](https://proceedings.mlr.press/v267/narayan25a.html)）：

- 朴素协议 MINION（端云两个模型对话式协作）：**云成本降 30.4×，但只恢复 87% 性能**——失败模式明确：小模型跟不住云端的多步指令、长上下文推理弱
- 改进协议 MINIONS：云端分解任务为**短块子任务、端侧并行执行**：成本降 5.7×，性能恢复 97.9%
- 场景：金融/医疗/科研长文档推理（只有端侧模型读全文，云端只见摘要与子问题）

### 2.3 Token 级混合（Mixture / Token-level）

端模型逐 token 生成，**关键 token 求助云端**：

- [Token Level Routing（ACL 2025 demo）](https://aclanthology.org/2025.acl-demo.16/)：M1 MacBook 上 0.5B 模型 + 云端大模型，仅 <7% token 上云，CommonsenseQA +60%
- 与投机解码同构——SLED（端起草 + 边缘服务器验证，见 [[投机解码与加速]] §4）把同一结构扩展到设备间
- 本质：**decode 的不确定性分布是不均匀的**，高熵 token 集中在少数决策点

## 3. Apple 的工程实现（产品级参照系）

（[Apple FM 2025](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates)）

```
请求 → 端侧 ~3B（默认，离线可用）
     → 需要更强能力时 → PCC（服务器 PT-MoE，端到端加密）
     → App 开发者视角：Foundation Models / Language Model 协议统一 API
```

- 分工哲学写在模型设计里：端侧模型"不做世界知识"（能力边界诚实），服务器模型为 PCC 的隐私约束定制架构（PT-MoE 并行轨道降同步开销）
- 2025 年新增：Language Model 协议让第三方云模型（Claude/Gemini）也接入同一 API——**Apple 把自己变成端云路由的仲裁者**

## 4. 协同学习的另一维度（训练期）

推理协同之外，训练协同（云端大模型 ↔ 端侧小模型共同进化）见 [[隐私与端侧学习]]：蒸馏（能力注入）、联邦学习（数据不出端）、端侧 LoRA（个性化）。三者与推理协同构成完整闭环：

```
云端预训练 → 蒸馏到端侧 → 端侧个性化(LoRA/记忆) → 联邦聚合回云端（可选，DP 保护）
```

## 5. 关键洞察

1. **粒度越细、收益越高、系统越复杂**：任务分配（成熟）→ 任务切分（研究中）→ token 混合（前沿）；token 级方法与投机解码在共享同一套基础设施（draft-verify/路由），技术正在合流
2. **"成本恢复率"是协同系统的核心指标**：MINION→MINIONS 的改进（87%→97.9%）说明瓶颈不在"是否上云"而在**任务怎么切**——云端做规划、端侧做执行是更稳的分工方向
3. **隐私是协同的第一路由约束**：Apple 把隐私保证做成架构（PCC），而非可选项——这决定了它的路由判据比"性能优先"的系统简单得多（敏感 → 端侧/PCC，无灰色地带）
4. **边缘服务器是被忽视的中间层**：SLED、CoMoE 等工作提示谱系其实是三级（端-边-云），边缘层擅长"验证/批量/共享模型"，但商业部署最少

## 6. 开放问题

- [ ] 路由判据的在线学习（用户级难度分布漂移）
- [ ] 端云模型版本异步（端侧模型更新慢于云端）的一致性语义
- [ ] token 级路由与 KV cache 的交互（上云 token 的上下文如何同步——上下文搬运本身可能泄漏）
- [ ] 协同系统的基准缺失：MINIONS 用自有任务集，缺乏公认 benchmark

## 7. 来源

- [Collaborative Inference and Learning between Edge SLMs and Cloud LLMs（ACM CSUR 2025）](https://dl.acm.org/doi/10.1145/3838593)——任务分配/切分/混合的统一分类
- [MINIONS: Cost-efficient Collaboration（PMLR 2025）](https://proceedings.mlr.press/v267/narayan25a.html)
- [Token Level Routing Inference System（ACL 2025 demo）](https://aclanthology.org/2025.acl-demo.16/)
- [Collaborative Learning of On-Device Small Model and Cloud-Based Large Model（arXiv:2504.15300）](https://arxiv.org/html/2504.15300)
- [Apple FM 2025 Updates](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates) / [What's New - Apple Intelligence](https://developer.apple.com/apple-intelligence/whats-new/)
- [Qualcomm 混合 AI 白皮书（2025 中文版）](https://www.qualcomm.cn/content/dam/qcomm-martech/dm-assets/documents/files/ai_whitepaper/ai_whitepaper_2025.pdf)
- [SLED（ACM 2025）](https://doi.org/10.1145/3769102.3770608)
