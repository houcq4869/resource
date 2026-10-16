# AI 软件开发概念 & 方法

> 面向想了解 AI 辅助 / Agentic 软件开发方法论的开发者。
> 文中数据截至 2026 年 10 月，此类工具与框架迭代极快，具体数字请以官方仓库为准。

---

## 1. 背景：AI 软件开发的三阶段演进

理解下面几个概念，需要先看清这两年多的演进脉络：

| 阶段 | 时期 | 主导模式 | 特征 |
|---|---|---|---|
| **AI 辅助** | ~2024 | 自动补全（Autocomplete） | 人写代码，AI 补全片段，SDLC 结构不变 |
| **Vibe Coding** | 2025 初 | 自然语言对话式开发 | Karpathy 提出；用 prompt 迭代生成代码，"感觉对就收货"；个人效率极高，但责任制、可验证性退化 |
| **Agentic Engineering** | 2025 下半年至今 | Agent 编排 + 规范驱动 | 自主 agent 执行目标级任务，人类转为编排者和验证者；SDD、Superpowers 等方法论在此窗口爆发 |

2026 年的行业共识可以概括为一句话：

> **先计划（Plan），再构建（Build），后审查（Review）** —— 计划成为一等公民，Review 成为新的质量瓶颈。

真正"落伍"的只有一件事：**无结构的裸 prompt 迭代（纯 vibe coding）在严肃工程中的口碑**——它有公认的"三个月技术债墙"。而 TDD、Spec/SDD、Superpowers 恰恰是应对这个问题的主流答案。

---

## 2. 四个概念一览

| 概念 | 全称 / 出处 | 一句话定位 | 所属层次 |
|---|---|---|---|
| **TDD** | Test-Driven Development（Kent Beck，2003） | 先写失败测试，再写实现 | 开发纪律（最底层，历史最久） |
| **Spec** | Specification（规格说明） | 用结构化文档定义"做什么"，作为人机之间的契约 | 工件（Artifact） |
| **SDD** | Spec-Driven Development | 把 Spec 前置为开发流程的核心步骤，再让 agent 生成代码 | 方法论（流程层） |
| **Superpowers** | obra/superpowers（Jesse Vincent，2025.10） | 一整套打包成"技能"的 agent 开发方法论框架 | 工具 / 框架（落地层） |

四者不互斥，而是**自下而上叠加**：TDD 提供验证纪律，Spec 提供意图契约，SDD 把契约组织成流程，Superpowers 把流程做成 agent 可自动执行的技能包。

---

## 3. TDD：测试驱动开发

### 3.1 经典定义

TDD 由 Kent Beck 在 XP（极限编程）中系统化，核心循环是 **红-绿-重构（RED-GREEN-REFACTOR）**：

1. **红**：写一个会失败的测试（描述期望行为）
2. **绿**：写最少的代码让测试通过
3. **重构**：在测试保护下改进结构，循环往复

经典 TDD 的两大收益：**驱动设计**（测试倒逼接口先于实现想清楚）和**回归保护**（改动有安全网）。

### 3.2 在 AI 时代的新角色：TDA

Agent 时代，TDD 不是过时了，而是**换了个引擎复兴**——它多了第三个、也是更硬的角色：

> **为 AI 产出提供机器可判定的"完成标准"（Definition of Done）。**

LLM 生成的代码没有"作者意图"可依赖，测试成为唯一客观的验收锚点。因此出现了 **TDA（Test-driven AI）** 的说法：要求 agent 先生成测试、或基于测试生成代码，把测试覆盖率作为代码生成的前置条件。Thoughtworks 将其列为企业级 AI 开发的五大构件之一（AI as QA）。

实践中的微妙转变：

- 经典：测试驱动**设计**（design）
- Agentic：Spec 描述意图 → 测试证明**达成**（verification）

典型体现：Superpowers 把 TDD 做成强制技能——测试必须先失败、实现必须最小化，甚至**删除先于测试写出的代码**。

### 3.3 适用判断

| 场景 | TDD 是否划算 |
|---|---|
| 新功能、边界条件多、可形式化的行为 | ✅ 强烈推荐 |
| 探索性原型 / 一次性脚本 | ⚠️ 可后补测试 |
| UI 视觉、胶水代码 | 视情况，可用 E2E 冒烟替代 |

---

## 4. Spec：规格说明

### 4.1 定义

Spec（Specification）是一份**结构化的、版本化的、人类可读且 AI 可执行**的需求/设计文档。它回答"做什么（What）"与"在什么约束下做（How）"，是从人类意图到 agent 执行之间的**契约层**。

在 agentic 范式下，Spec 的性质发生了根本变化：

> **传统软件工程里，Spec 是人和人之间的沟通文档；在 Agentic SE 里，Spec 是人和 agent 之间的规范契约，代码、测试、文档都从它派生，并可追溯。**

### 4.2 What / How 分离

被广泛引用的实践是把 Spec 模块化拆开，避免单个 prompt 里 What 和 How 混杂导致 AI "顾此失彼"：

```
specs/
├── what-vision.md          # 高层目标（做什么）
├── how-security.md         # 认证、密钥、权限约束
├── how-observability.md    # 日志与可观测性要求
├── how-standards.md        # 代码与架构规范
└── how-testing.md          # 覆盖率目标与 mock 策略
```

与之配套的是 **Context Engineering（上下文工程）**：Spec 管 What/How，而 AGENTS.md / CLAUDE.md / `.cursor/rules` 这类指令文件管"长期项目约定"。两者共同构成给 agent 的完整上下文。

### 4.3 Spec 生命周期的三个层次

Martin Fowler 团队（Birgitta Böckeler）对 SDD 工具的划分，已成为讨论 Spec 时的标准语言：

| 层次 | 含义 | 代表工具 |
|---|---|---|
| **Spec-first**（规范先行） | 写 Spec → 生成代码 → **Spec 用完即弃** | GitHub Spec Kit、Kiro、BMAD |
| **Spec-anchored**（规范锚定） | Spec 随实现**持续演化**，是长期事实源 | OpenSpec、Spec Kitty |
| **Spec-as-source**（规范即源码） | **只编辑 Spec，代码完全自动生成** | Tessl（实验中） |

层次越高越激进，也越接近当年 MDD（模型驱动开发）的梦想——LLM 消解了自定义 DSL 和代码生成器的成本，但也引入了非确定性。

---

## 5. SDD：规范驱动开发

### 5.1 定义

**SDD = 在让 AI 动手写代码之前，先通过人机协作产出结构化规范（需求 → 设计 → 任务），再由 agent 依据规范生成实现，并在规范与实现之间保持验证闭环的开发方法。**

它是对 vibe coding 的直接纠偏。业界对其动因的一句话概括：

> "瓶颈已经不再是写代码的速度，而是**意图的清晰度**。"

学术界的表述更正式：SDD 重新确立了 vibe coding 所消解的三样东西——**可问责性（accountability）、可验证性（verifiability）、可迁移性（transferability）**，只不过以"规范为中心"的形式回归。

### 5.2 典型流程

虽然各工具细节不同，但收敛于同一个形状：

```
意图捕获 → 规范（requirements.md / spec.md）
        → 设计（design.md / plan.md）
        → 任务拆解（tasks.md，2-5 分钟粒度）
        → Agent 实现（受约束生成）
        → 验证（测试 / 审查 / 一致性检查，对照规范）
        → 人工签核（human sign-off）
```

### 5.3 主要工具生态（2026 年）

SDD 已是拥有 30+ 框架的拥挤赛道，头部玩家：

| 工具 | 定位 | 关键特征 |
|---|---|---|
| **GitHub Spec Kit**（~14 万 stars） | 社区采用最广的 CLI 工具 | 五步管线：constitution → specify → plan → tasks → implement；41 个 agent 集成；constitution 定义项目"不可变原则" |
| **AWS Kiro**（商业 IDE） | Spec 内建于编辑器 | EARS 需求表示法（WHEN…THE SYSTEM SHALL…）；GA 后推出基于需求的 property-based testing，把 Spec 变成可执行验证 |
| **OpenSpec**（~5.4 万 stars） | 轻量 delta-spec | 面向存量项目（brownfield）的增量变更管理；token 消耗约为 Spec Kit 的一半 |
| **BMAD Method**（~5.4 万 stars） | 重型多角色框架 | 模拟完整敏捷团队（分析师/PM/架构师/Dev/QA 等 21+ 角色 agent）；PRD → 架构 → 史诗 → 故事的全链路 |
| **Tessl** | spec-as-source 探索 | 代码标注 `// GENERATED FROM SPEC - DO NOT EDIT`，编辑 Spec 后重新生成 |
| **GSD**（~6.4 万 stars） | solo dev 黑马 | 上下文隔离 + 分波执行，2025-12 出现后增长最快 |

### 5.4 实证效果与局限

50 张生产工单的对照实验（Uvik Benchmark，Claude Sonnet 5，盲审）：

| 维度 | 结果 |
|---|---|
| 功能开发 / 数据管道 / 6+ 文件大改动 | spec 组 merge 率 **90%** vs 无 spec 对照组 **60%** |
| Bug 修复 / 重构 / 补测试 | spec 开销**收不回**，对照组打平或更优 |
| 规格漂移（spec drift） | OpenSpec 最低（2.4%），Spec Kit / BMAD 约 12% |

**结论**：SDD 是"按问题规模付费"的方法——大特性明确划算，小修小补是杀鸡用牛刀（Böckeler 实测：一个小 bug 被 Kiro 拆成 4 个 user story + 16 条验收标准）。

### 5.5 与 Vibe Coding 的关系

主流观点认为两者**互补而非竞争**：

> "用 vibe coding 探索和做原型，用 spec-driven development 交付和上线。"

一个常见工作流：先 vibe 出需求的样子 → 把沉淀下来的理解固化成 Spec → 用 SDD 硬化并交付。

---

## 6. Superpowers

### 6.1 是什么

[Superpowers](https://github.com/obra/superpowers) 是 Jesse Vincent（obra）于 2025 年 10 月发布的**面向编码 agent 的完整软件开发方法论**，以一组可组合的**技能（Skills）**形式交付，通过初始指令确保 agent 真正使用它们——**是强制工作流，不是建议**。

它是当前该赛道事实上的头部：

- 约 **30 万 GitHub stars**（历史第 12 受欢迎项目）
- Claude Code **第一大第三方插件**（110 万+ 安装；每两周被 clone 约 5000 万次）
- MIT 开源，支持 15+ harness：Claude Code、Codex、Cursor、Gemini CLI、OpenCode、Copilot CLI、Qwen Code、Antigravity 等
- 2026 年 10 月刚发布 **7.0**（重做 brainstorming）

### 6.2 核心工作流

```
1. brainstorming        苏格拉底式需求挖掘——先问清你要什么、为什么，复述确认
                        （小改动在聊天中达成一致；项目级产出设计文档）
2. using-git-worktrees  设计通过后，创建隔离 worktree + 新分支，跑干净测试基线
3. writing-plans        把工作拆成 2-5 分钟粒度的任务，每个任务带精确文件路径
                        和验证步骤
4. subagent-driven      每个任务派发独立子 agent 实现 + 逐任务 review（最严格）；
   development /        或 Native（inline）执行：当前会话直接做完，分支末尾
   executing-plans      一次整体 review（最便宜）
5. test-driven-         实现期间强制红-绿-重构；先于测试写的代码会被删掉
   development
6. requesting-code-     任务间对照计划审查，按严重度报告问题，Critical 阻塞推进
   review
7. finishing-a-         验证测试全绿，呈现 merge / PR / 保留 / 丢弃选项，
   development-branch   清理 worktree
```

技能体系还覆盖：**systematic-debugging**（四阶段根因分析，三次修复失败强制升级架构审查）、verification-before-completion、writing-skills（用 TDD 思路写技能本身）等。

### 6.3 值得关注的演进信号

Superpowers 一直在随前沿模型的能力变化自我调整，这本身就是方法论演化的活样本：

- **吸收 SDD**：6.x 引入了 plan-scoped workspace、resume-based fix loop 等 SDD 机制
- **流程减负**：6.4 评测显示，在当代前沿模型上 Native 执行比 subagent 模式**快约一倍、token 花费约一半**；完全不挂流程（bare metal）更快更便宜，但 bug 显著更多——"好的流程管理依然比放养结果更好"
- **跨平台中立化**：技能文案从 Claude Code 方言改写为平台无关表述，并附每个 harness 的工具映射表
- **自我诊断**：`diagnosing-superpowers` 技能可以读会话记录，定位"技能为什么没触发"，产出带 `path:line` 证据的报告

### 6.4 适用判断

- ✅ 想要**纪律性的自治开发**（agent 长时间自主跑，质量可控）
- ✅ 团队想统一 agent 开发规范，且不想被绑死在单一工具上
- ⚠️ 快速小改动、随手脚本——流程开销大于收益，7.0 虽已优化"让路"体验，但仍有成本

---

## 7. 四者的关系：一张图

```
┌─────────────────────────────────────────────────────┐
│  Superpowers（框架层）                                │
│  把方法论打包成 agent 可自动触发的技能                  │
│  ┌───────────────────────────────────────────────┐  │
│  │  SDD（流程层）                                  │  │
│  │  意图 → Spec → 设计 → 任务 → 实现 → 验证 → 签核  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  Spec（工件层）                           │  │  │
│  │  │  What / How 分离的结构化契约文档           │  │  │
│  │  │  ┌───────────────────────────────────┐  │  │  │
│  │  │  │  TDD（纪律层）                      │  │  │  │
│  │  │  │  红-绿-重构 = 机器可判定的完成标准    │  │  │  │
│  │  │  └───────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

四层共同回答一个问题：**当写代码的不再是人，工程纪律放在哪里？**

- TDD 把纪律放进**测试**
- Spec 把纪律放进**文档**
- SDD 把纪律放进**流程**
- Superpowers 把纪律放进 **agent 本身**

---

## 8. 选型速查

| 你的情况 | 建议 |
|---|---|
| 小改动、日常修 bug | Agent 内置 plan mode + 一份维护良好的 AGENTS.md，别上框架 |
| 新功能 / 大特性 / 6+ 文件改动 | SDD 明确划算：绿地选 Spec Kit，存量项目选 OpenSpec |
| 治理、审计、合规要求高 | BMAD Method（角色化 + 全链路文档） |
| 想要 spec + IDE 一体化 | AWS Kiro（注意 IDE 锁定） |
| 想要纪律性自治开发 | Superpowers（MIT、跨平台、生态最大） |
| 探索期 / 做原型 | 放心 vibe coding，但记得事后把理解固化成 Spec |

**常见组合姿势**：vibe coding 探索 → Spec 固化 → SDD 交付 → TDD 兜底。

---

## 9. 参考资料与延伸阅读

- Superpowers 仓库：<https://github.com/obra/superpowers>（及 Prime Radiant 博客的版本发布说明）
- GitHub Spec Kit：<https://github.com/github/spec-kit>
- AWS Kiro：<https://kiro.dev>
- OpenSpec：<https://github.com/Fission-AI/OpenSpec>
- BMAD Method：<https://github.com/bmad-code-org/BMAD-METHOD>
- Birgitta Böckeler, *Understanding Spec-Driven Development: Kiro, spec-kit, Tessl*（martinfowler.com，2025-10）——SDD 工具三分法的出处
- Thoughtworks, *Beyond Vibe Coding: The Five Building Blocks of AI-Native Engineering*（2026-03）
- Red Hat Developer, *Vibes, Specs, Skills, and Agents: The Four Pillars of AI Coding*（2026-03）
- InfoWorld, *Vibe Coding or Spec-Driven Development? How to Choose*（2026-05）
- arXiv: *Spec-Driven Development for Agentic Software Engineering*（SDD 的学术化表述）
- Uvik Software, *SDD Benchmark 2026*（50 工单对照实验数据）

---

*文档生成于 2026-10-15。该领域迭代极快，建议每季度核对一次工具状态。*
