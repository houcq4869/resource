# AI 软件开发全景：概念、方法与流程

> **定位**：一份系统的 AI 辅助 / Agentic 软件开发知识地图，覆盖演进脉络、方法论、开发流程、技术标准、多 Agent 编排、上下文工程、安全与落地路线。
> **时效**：数据截至 2026 年 10 月。本领域迭代极快（协议半年一版、工具一月一更），阅读时请核对各项目官方页面。
> **姊妹篇**：《AI软件开发概念与方法.md》——Superpowers / SDD / TDD / Spec 四个概念的深入展开。

---

## 目录

1. [范式变迁与演进时间线](#1-范式变迁与演进时间线)
2. [2026 年的共识工作流](#2-2026-年的共识工作流)
3. [方法论全景](#3-方法论全景)
4. [开发流程详解：Plan → Build → Review](#4-开发流程详解)
5. [技术标准与协议栈](#5-技术标准与协议栈)
6. [上下文工程](#6-上下文工程)
7. [多 Agent 编排](#7-多-agent-编排)
8. [安全](#8-安全)
9. [评估与运营](#9-评估与运营)
10. [工具速查表](#10-工具速查表)
11. [落地路线图](#11-落地路线图)
12. [趋势判断与常见误区](#12-趋势判断与常见误区)
13. [参考资料](#13-参考资料)

---

## 1. 范式变迁与演进时间线

### 1.1 四个时代

| 时代 | 时期 | 主导模式 | 人的角色 |
|---|---|---|---|
| **SE 1.0** | ~2020 | 传统敏捷 + DevOps | 人写代码 |
| **辅助编程** | 2021–2024 | 自动补全（Copilot 开端） | 人写代码，AI 补片段 |
| **Vibe Coding** | 2025 初 | 对话式生成（Karpathy 提出） | 人用 prompt 驱动，"感觉对就收货" |
| **Agentic SE（SE 3.0）** | 2025 下半年至今 | Agent 自主执行目标级任务 | 人做编排者与验证者 |

Agentic 时代的关键判断（学术界表述）：**生产力悖论**——个体效率提升的同时，团队级的吞吐、审查容量和稳定性反而退化，除非重新引入工程纪律。这就是所有下述方法论存在的理由。

### 1.2 关键事件时间线

| 时间 | 事件 |
|---|---|
| 2021.06 | GitHub Copilot 预览，补全时代开始 |
| 2024.11 | Anthropic 开源 **MCP**（Model Context Protocol） |
| 2025.02 | Karpathy 提出 **vibe coding** |
| 2025.07 | AWS **Kiro** 发布（spec-driven IDE）；Google A2A 协议亮相 |
| 2025.08 | **AGENTS.md** 约定出现（OpenAI Codex / Amp / Jules / Cursor / Factory 共同推动） |
| 2025.09 | Anthropic 发布 Agent **Skills** 标准（agentskills.io）；发表上下文工程工程博客 |
| 2025.09.08 | MCP Registry 上线 |
| 2025.10 | **Superpowers 1.0** 发布；GitHub **Spec Kit** 开源；Thoughtworks/Red Hat 等开始系统化论述 |
| 2025.12 | Anthropic 将 MCP 捐赠给 **Agentic AI Foundation**（Linux Foundation 旗下，OpenAI/Block 联合创立） |
| 2026.02 | Claude Code 原生 git worktree 支持 |
| 2026.04 | **A2A v1.0**（签名 Agent Card，150+ 组织）；Bloop 关闭 Vibe Kanban |
| 2026.06 | Google **Antigravity** 接收 Gemini CLI 个人用户；Windsurf 品牌退役为 Devin Desktop；Spec Kit 发布 converge |
| 2026.07 | MCP 2026-07-28 规范（无状态核心等）；Codex 并入 ChatGPT 桌面端 |
| 2026.09 | Claude Code 原生读取 AGENTS.md（v2.1.277）；MCP 月下载量达 ~5 亿 |
| 2026.10 | Superpowers 7.0（发布一周年，~30 万 stars）；BMAD v7 预告 |

### 1.3 一个重要的认知框架

> **Agent = Model + Harness（缰具）**——编码 agent 的可靠性不只取决于模型，还取决于包裹模型的系统：执行状态、检索、记忆管理、权限、审查界面、资源分配。方法论和流程，本质上都是在设计 Harness。

---

## 2. 2026 年的共识工作流

目前所有主流工作流（无论叫 SDD、Superpowers 还是内置 plan mode）都收敛到同一个形状：

```
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ Research │ → │  Plan   │ → │ Execute │ → │ Review  │ → │  Ship   │
│ 探索意图  │   │ 规范/计划 │   │ agent实现 │   │ 验证/审查 │   │ 交付运维 │
└─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

2026 年的三个结构性变化（来自 Bilgin Ibryam 的年度全景）：

1. **计划成为一等公民**：认真做事的团队在 agent 碰代码之前先写 spec/plan；主流工具全部内置 plan / explore / read-only 模式
2. **构建分裂为三类**：全栈应用生成器（Bolt/Lovable/Replit，prompt-to-product）、本地开发 agent（Claude Code/Codex/OpenCode，在真实 repo 里工作）、异步云 agent（丢任务给云端，回来收 PR）
3. **审查成为新瓶颈**：代码生成速度超过了人工检查能力，AI review 成了跟上 AI 产能的唯一办法；两段式审查（本地 pre-commit + PR）成为标配，测试 agent 是下一个扩张点

---

## 3. 方法论全景

按"约束放在哪里"分类：

| 方法论 | 纪律放进 | 核心主张 | 代表 |
|---|---|---|---|
| **Vibe Coding** | 无（直觉） | 对话迭代到满意为止 | Karpathy 式用法 |
| **TDD / TDA** | 测试 | 先写失败测试；测试 = 机器可判定的完成标准 | 经典 TDD；Thoughtworks "Test-driven AI" |
| **Spec / SDD** | 文档 | 先写规范再生成；规范是人机契约 | Spec Kit、Kiro、OpenSpec、BMAD |
| **Superpowers** | Agent 技能 | 强制工作流：brainstorm → plan → TDD → review | obra/superpowers |
| **四支柱**（Red Hat） | 分层组合 | vibes 探索 / specs 定义 / skills 赋能 / agents 执行 | 概念框架 |
| **五大构件**（Thoughtworks） | 企业流程 | 结构化输入、CI/CD 集成、测试驱动、版本审计、人工把关 | 企业级框架 |
| **BMAD** | 角色分工 | 用多角色 agent 模拟完整敏捷团队 | BMAD-METHOD |

### 3.1 Vibe Coding：正确用法与边界

- **定义**：纯自然语言对话驱动生成，接受"感觉对"的输出
- **价值**：POC、原型、内部工具、想法探索——压缩"从想法到 demo"的时间无可匹敌
- **边界（被反复证实的"三个月墙"）**：缺乏确定性，不适合需要长期维护、扩展、审计的系统；企业界共识是"vibe coding 做前端加速器，spec 做地基"
- **2026 定位**：与 SDD **互补而非竞争**——"用 vibe 探索需求，用 spec 固化交付"

### 3.2 TDD → TDA

经典红-绿-重构（RED-GREEN-REFACTOR）在 agent 时代获得第三个角色：

| 时代 | 测试的作用 |
|---|---|
| 经典 TDD | 驱动设计 + 回归保护 |
| **TDA（Test-driven AI）** | 上述 + **为 AI 产出提供机器可判定的验收锚点** |

实践要点：Spec 描述意图（What/Why），测试证明达成（verification）；要求 agent 生成代码时同步甚至先行生成测试；Superpowers 等框架强制"先看测试失败再实现"。

### 3.3 Spec / SDD：三分法与工具生态

Fowler 团队的 Spec 生命周期三分法已是标准语言：

| 层次 | 含义 | 代表 |
|---|---|---|
| **Spec-first** | 用完即弃 | Spec Kit、Kiro、BMAD |
| **Spec-anchored** | 持续演化的活文档 | OpenSpec、Spec Kitty |
| **Spec-as-source** | 只编辑 spec，代码生成（`// GENERATED FROM SPEC - DO NOT EDIT`） | Tessl（实验） |

头部工具（2026-10 数据）：

| 工具 | Stars | 最新版本 | 特点 |
|---|---|---|---|
| Superpowers | ~300k | 7.0（10-09） | 方法论+技能，含 SDD/TDD |
| GitHub Spec Kit | ~141k | v1.1.3（10-09） | constitution→specify→plan→tasks→implement；converge 收敛循环；41 agent 集成 |
| GSD | ~64k | — | solo dev、上下文隔离、分波执行 |
| OpenSpec | ~54k | 1.14.1（10-06） | delta-spec，brownfield 最优，token 约为 Spec Kit 一半 |
| BMAD | ~54k | 6.12.2（10-11），v7 预告 | 21+ 角色 agent，敏捷全流程，48 平台 |

**实证边界**（Uvik 50 工单对照实验）：功能开发/数据管道/6+ 文件大改动上 spec 组 merge 率 90% vs 对照 60%；bug 修复/重构/补测试上 spec 开销收不回。**结论：SDD 按问题规模付费。**

### 3.4 Superpowers：方法论的产品化

一年从 1.0 到 7.0，GitHub 历史第 12 受欢迎项目、Claude Code 第一大第三方插件（110 万+ 安装）。核心流程：

```
brainstorming（苏格拉底式需求挖掘）
→ git worktree 隔离
→ writing-plans（2-5 分钟粒度任务）
→ subagent-driven development（逐任务派发+review）或 Native 执行（inline，更快更省）
→ TDD 强制
→ code review → 收尾分支
```

值得跟踪的演进信号（方法论随模型能力自适应的活样本）：

- 6.x 吸收 SDD 机制（plan-scoped workspace、fix loop）
- 6.4 评测：前沿模型上 Native 执行比 subagent 快一倍、省一半 token；裸跑最快但 bug 显著更多
- 7.0 重做 brainstorming，更懂得"在你明确知道要什么时让路"

### 3.5 内置 Plan Mode：被商品化的基线

Claude Code plan mode、Cursor plan、Codex plan 等——**严肃工具全部在动手前提供只读规划模式**。这已把"先想后做"变成默认行为。社区争论焦点（2026-05 r/ClaudeCode 热帖）："Spec 框架是否已被内置能力取代？"——答案分场景：小改动 AGENTS.md + plan mode 足够；大特性仍需重型 SDD。

---

## 4. 开发流程详解

### 4.1 阶段一：Research / Ideation

- 用对话式 agent 探索想法、评估方案（"四支柱"中 vibes 的正当用途）
- AI 作为 spec 教练：让模型给自己的 spec 打分（"0-10 分，一个自治 agent 只凭这份 spec 能把功能做出来吗？缺什么？"），迭代到 9-10 分再进入执行
- 产出：设计文档或轻量共识

### 4.2 阶段二：Plan（规范）

- 产出物：requirements（What）/ design（How）/ tasks（粒度 2-5 分钟的任务清单）
- What/How 分离写入不同文件（what-vision.md、how-security.md、how-testing.md…）
- 经验法则：**一份 spec 约 300 token，能消除 90% 的来回返工**

### 4.3 阶段三：Execute（构建）

三种执行模式（按投入排序）：

1. **交互式 pair**：人在环上，agent 每步受检——生产代码、安全敏感改动的默认
2. **Subagent 分治**：编排者拆任务，子 agent 各自干净上下文中执行，回传摘要（父上下文 +200 token 而非 +8000）
3. **异步云 agent**：任务丢给云端沙箱（容器/VM），人离开，回来收 PR——适合边界清晰、无需中途人工判断的任务（测试生成、文档、例行重构、积压清理）

**隔离的基石是 git worktree**：每个 agent 一个独立工作目录 + 分支，共享 `.git` 对象库，执行期零合并冲突。Claude Code 2026.02 起原生支持 `--worktree`，Codex 子 agent 支持 `isolation: worktree`。

### 4.4 阶段四：Review（验证）

- **两段式**：本地（commit/PR 前）+ 共享（PR 上）——review 已内化进开发循环而非终局关卡
- AI review 工具：Codex 内置 code review、Claude Code review、Copilot review、CodeRabbit 等
- 测试层：agent 跑测试并自修复 CI；浏览器 agent 做端到端验证（下一扩张点）
- 原则：**AI 生成的代码必须有人类 owner**——"开发者签了 PR 但没写代码"不能成为免责理由
- 行业判断："调度并行 agent 很容易，人人都会了；稀缺的是决定放什么过去——**这是 review 问题，不是编排问题**"

### 4.5 阶段五：Ship（交付）

- AI 提交物过与人类相同的门禁：CI、lint、SAST、SCA、secret 扫描、人工签核
- 版本控制即审计：清晰 commit message、可追溯、可回滚；agent 的每一步动作留痕
- Lessons-learned 循环（spec 共同演化）：agent 遇到 bug/构建失败时记录根因到 LessonsLearned.md 并建议更新对应 how-*.md 规范

---

## 5. 技术标准与协议栈

2025 年末开始的**标准收敛**是本领域最重要的基础设施事件：竞争激烈的厂商把"接口层"交给中立治理。类比：MCP 之于 AI 工具集成，正如 LSP 之于编辑器-语言服务器。

```
┌──────────────────────────────────────────────┐
│  OTel GenAI 语义约定（trace/metrics，未稳定）  │  可观测
├──────────────────────────────────────────────┤
│  A2A（agent ↔ agent 通信）· WebMCP · NLWeb    │  互联
├──────────────────────────────────────────────┤
│  MCP（agent ↔ 工具/数据）                      │  连接
├──────────────────────────────────────────────┤
│  AGENTS.md（仓库级指令）· Agent Skills（SKILL.md）│  指令/技能
├──────────────────────────────────────────────┤
│  ACP（编辑器 ↔ agent 进程，"agent 界的 LSP"）   │  宿主
└──────────────────────────────────────────────┘
```

### 5.1 MCP（Model Context Protocol）

- **是什么**：AI 应用连接工具/数据/服务的标准接口（JSON-RPC；server 暴露 tools/resources/prompts）
- **治理**：Anthropic 2024.11 创建 → 2025.12 捐赠给 Agentic AI Foundation（Linux Foundation 旗下；OpenAI、Block 联合创立；Google/Microsoft/AWS/Cloudflare 支持）；40+ 维护者中不到 1/4 在 Anthropic
- **规模**（2026-09/10）：Tier-1 SDK 月下载 ~5 亿；Claude 平台累计 10 亿+ 工具调用；官方 Registry 收录 3.8 万+ server，月安装 1.2 亿+；第三方记录 26.5 万条目（16.4 万 server / 5.9 万 skill / 4.2 万 plugin）
- **2026-07-28 规范**要点：无状态核心（免握手调用）、header 路由、可缓存列表、正式扩展框架、12 个月弃用窗口
- **使用建议**：版本锁定；协议代码藏在薄适配层后面；预算迁移成本——两年内已五次修订

### 5.2 AGENTS.md

- **是什么**：仓库根目录的一个 Markdown 文件——构建/测试/lint 命令、代码约定——给编码 agent 的 README
- **采用**：6 万+ 开源项目；Copilot、Claude Code（2026.09 起无 CLAUDE.md 时原生读取）、Cursor、Gemini CLI、VS Code 等全部支持；AAIF 创始项目
- **行动建议**：**本周就给你的仓库提交一份 AGENTS.md**——它是当前最便宜的移植性保险

### 5.3 Agent Skills

- **是什么**：可移植的指令包——`SKILL.md`（YAML frontmatter + Markdown）+ `references/`，agent 按需加载
- **标准**：agentskills.io 开放标准（Anthropic 发起），45+ agent 产品支持
- **价值**：渐进披露——常驻成本仅 ~200 token 的名称+描述，触发时才加载全文；spec 说"做什么"，skill 提供"怎么做"的程序性知识

### 5.4 其他

| 协议 | 状态（2026-10） |
|---|---|
| **A2A** | v1.0（2026.04）；签名 Agent Card；150+ 组织；Azure/Bedrock/Copilot Studio GA |
| **ACP** | JetBrains + Zed；编辑器可托管任意 ACP agent 子进程；OpenCode 已内置 |
| **WebMCP** | Shopify 全部 Liquid 店面默认开启（2026.08）；Chrome origin trial |
| **NLWeb** | 仍是 proof-of-concept，勿依赖 |
| **OTel GenAI** | 语义约定开发中，未稳定 |

**关键洞察：锁定已转移到约定层。** 掂商可换，模型可换；你的 MCP server 集合、skills 库、AGENTS.md 不可换——这就是新锁定所在。

---

## 6. 上下文工程

> **定义**（Anthropic）：上下文工程是 prompt engineering 的自然演进——不再优化单条 prompt，而是**策展 agent 在每一步推理时看到的一切 token**：系统指令、工具、MCP 数据、消息历史、记忆。

### 6.1 为什么成为显学

- Agent 变成长时程：数小时的会话需要能在 compaction、溢出、重启后存活的上下文
- 舰队常态化：5-50 个并行 agent 时，糟糕的 CLAUDE.md 浪费被放大 20 倍
- 核心原则：**找到最小的高信号 token 集合，最大化达成目标的概率**

### 6.2 六个上下文表面（以 Claude Code 为例）

| 表面 | 加载时机 | 强制力 | 适用 |
|---|---|---|---|
| CLAUDE.md / AGENTS.md | 每次会话开始 | 软（~70%） | 项目约定、构建命令 |
| Hooks | 特定事件（PreToolUse 等） | **硬（100%）** | 安全红线、强制格式化 |
| Skills | 按需（agent 自判） | 软 | 领域程序性知识 |
| Subagents | 委派时 | 独立上下文 | 深度探索、隔离杂讯 |
| Memory | 会话开始 | 软 | 跨会话偏好/决策 |
| Specs | 每任务注入 | 软 | 任务级验收标准 |

**最重要的一条工程规则**：安全规则放 CLAUDE.md 只有 ~70% 遵守率；放 hook（在模型之外执行的 shell 命令，exit code 2 可阻断）是 100%。"never push to main"这种事，70% 意味着迟早出事故。

### 6.3 长时程技术（Anthropic 工程实践）

| 技术 | 做法 | 解决什么 |
|---|---|---|
| **Compaction（压缩）** | 上下文将满时摘要关键信息重启窗口（保留架构决策、未解 bug、实现细节，丢弃冗余工具输出） | 超长任务连贯性 |
| **结构化笔记 / Agent 记忆** | 定期把笔记写到窗口外文件（NOTES.md、todo），后续拉回 | 跨几十次工具调用的状态保持 |
| **Just-in-time 检索** | 常驻轻量标识符（文件路径、查询、链接），运行时按需拉取 | 避免预加载全量数据 |
| **Subagent 隔离** | 深度工作在子 agent 的干净上下文中进行，只回传 1-2k token 摘要 | 父上下文不被中间输出污染 |

### 6.4 并行 agent 的记忆架构

- 会话级知识放会话级存储；**共享知识放共享存储**（REST API / 数据库），永远不要用本地文件系统充当并行 worktree 间的共享状态
- 跨厂商舰队需要跨运行时记忆桥（如 amux memory bridge，2026.08）——Claude/Gemini/Codex 各有互不兼容的记忆格式

---

## 7. 多 Agent 编排

### 7.1 三层框架（Addy Osmani，O'Reilly CodeCon 2026.03）

| | Tier 1：进程内 | Tier 2：本地编排 | Tier 3：云异步 |
|---|---|---|---|
| **并行数** | ≤6 | 3–30 | 不限 |
| **时长** | 分钟级 | 小时级 | 数小时~过夜 |
| **监督** | 持续在场 | 仪表盘/周期 | 事后 PR review |
| **隔离** | 共享沙箱 | git worktree | 云容器/VM |
| **代表** | Claude Code/Codex subagents、Claude agent teams | Gas Town、Conductor、Claude Squad、Orca | Codex Cloud、Claude Code Web、Copilot agent、Jules、Devin、Cursor Cloud |
| **成本** | 零设置 | 中等（Gas Town 满载 ~$100/小时 token） | 托管，按量 |

**升级判据**：6 线程不够 → Tier 2；本机饱和 → Tier 3。三层不互斥——多数团队三层并用：Tier 1 交互开发，Tier 2 并行冲刺，Tier 3 夜间排积压。

### 7.2 协作模式（协作成熟度分档）

| 模式 | 机制 | 代表 |
|---|---|---|
| **并行隔离**（最常见） | 各自 worktree 干活，人来合并 | Conductor、Cursor、Codex、Orca |
| **单厂商编排** | lead agent 拆分给自家 subagent | Claude Code agent teams、Devin、Factory Missions |
| **跨厂商协作**（前沿） | 不同厂商 agent 在共享房间交接任务、@mention、human in place | BAND |

Claude Code agent teams 细节：多个实例共享 `TASKS.md` 任务清单，teammate 之间用 `SendMessage` 点对点通信——peer-to-peer，区别于 Codex 的 parent-child 临时工模型。仍为实验特性。

### 7.3 Harness（缰具）选择要点

- 先选 harness 再选编辑器：绑定单厂商订阅（Claude Code/Codex）vs 任意模型（OpenCode/aider/Crush）
- 编辑器支持 ACP 就把 harness 托管进去，别迁移 IDE
- 批量工作交给已有 harness 的云形态；**读清会话时长上限再承诺交付日期**（如 Copilot 云 agent 单会话 59 分钟）

---

## 8. 安全

OWASP 已发布《Secure Coding with AI》《AI Agent Security》《MCP Security》《LLM Prompt Injection Prevention》四张速查表——**用 AI 写代码，安全标准不降**。

### 8.1 Agentic 编码的独特攻击面

| 攻击面 | 机理 |
|---|---|
| **间接 prompt injection** | agent 读的一切都是指令源：issue 正文、PR 描述、README、依赖 changelog、报错堆栈、抓取的网页、MCP 工具返回——能写这些的人就能操纵 agent |
| **MCP 供应链** | 恶意/被黑 server 可污染工具描述、影子化合法工具名、通过参数外传凭据、**先过审后改定义（rug-pull）** |
| **规则文件持久化** | `.cursorrules`、CLAUDE.md、AGENTS.md 静默引导后续所有生成——恶意 PR 或 agent 自己改这些文件 = 持久后门 |
| **CI/CD 混淆代理** | review bot 持组织 secrets 处理 PR 内容，恶意 PR 可诱导其外传 secrets 或改流水线 |
| **Slopsquatting** | 模型会幻觉出不存在的包名，攻击者预先注册这些名字等你 `pip install` |

### 8.2 防御清单（实操级）

**自治分级**（匹配风险）：
- 逐编辑 review：生产代码、安全敏感、涉凭据改动的默认
- 范围内 auto-accept：草稿/绿地实验可接受
- 完全自治/长时程：**只在沙箱内**（devcontainer / 临时 VM / 云 runner）——无个人 SSH key 与云凭据、仅限本仓库的短命 token、网络出口最小化、干净文件系统快照

**日常纪律**：
- 不给 agent 环境级凭据；密钥进 vault/env，绝不进项目树
- 敏感文件（`.env`、`*.pem`、`credentials.json`）加进 AI 工具的忽略清单
- rules 文件按安全关键配置对待：PR 中改动这些文件必须显式审批，加 git hook/CI 检查
- MCP server 准入：确认发布方、审工具清单（`run_shell` 类工具加倍审视）、最小权限、定义入库可审计、锁定工具定义并 diff 检测 rug-pull
- 安装前验证依赖真实存在、维护者与下载量合理（反 slopsquatting）
- **读 diff 再接受**——"agent 改文件的速度超过你阅读的速度，就是净安全损失"
- 把安全审查做成 skill（security-review SKILL.md 模式）：commit 前强制自查 secrets/注入/加密/依赖/许可证
- 多 agent 系统中，一个 agent 的输出对另一个 agent 是**不可信输入**；审批绑定到确切动作（actor+tool+参数+时效），原子消费，防重放

**红线**（来自 OWASP 的 Don'ts 精选）：不给通配符工具权限；不信任外部内容；不无沙箱执行任意代码；不把敏感数据明文进记忆/日志；不让 agent 无上限地递归重试（DoW——拒绝钱包式 DoS）。

---

## 9. 评估与运营

### 9.1 核心观念：按系统评估，而非按模型

> "编码 agent **作为模型被评估，作为系统被部署**。"——可靠性取决于 harness、执行状态、检索、记忆、权限、审查界面、资源分配的整条链。

实操含义：
- run-to-run 方差必须先测量再下结论（同一任务跑多次；prompt 措辞的语义等价变化可造成中位 7.5 个百分点的准确率摆动）
- 消融实验：归因某个组件（如记忆）的贡献，必须只去掉它重跑，其余全冻结
- 成本与准确率一起报；供应商静默更新模型会造成时间漂移，需锁定版本

### 9.2 人的角色重定义

- **Spec Architect（规范架构师）**：价值在于捕获、形式化、验证**意图**，而非实现代码
- **Review 者**：review 能力是团队新瓶颈——"个体提速而团队退化"的解药在 review 容量，不在生成速度
- **问责**：验证审计的是证据而非重构意图；onboarding 读的是 spec 而非代码
- 指标建议：merge 率、每 merged ticket 成本、返工轮数、spec 漂移率、review 缺陷率——而非单纯速度

### 9.3 规模化判据

autonomy 按**动作类型**逐步放宽：只有当测得的审批率/修改率证明某类动作可靠时，才放行该类动作的自治。多 agent 设计必须先证明优于单 agent 同任务，才值得上。

---

## 10. 工具速查表

*以 2026-10 公开数据为参考；该领域"基准和评测几周就过时"，最可靠的测试是把同一任务交给 2-3 个 agent 比 diff。*

### 10.1 编码 Agent（Harness）

| Agent | 厂商 | 要点 |
|---|---|---|
| Claude Code | Anthropic | ~150k stars；并行能力最全（subagents、/batch、agent teams、cloud、Remote Control）；插件/skills/hooks 生态最大；无免费档 |
| Codex CLI | OpenAI | Apache-2.0 开源；ChatGPT 订阅覆盖 CLI/IDE/云/review；AGENTS.md 配置；子 agent（.codex/agents/ TOML） |
| OpenCode | 开源 | ~213k stars；任意模型/任意 key；`opencode acp` 进 Zed/JetBrains/Neovim |
| Antigravity（agy） | Google | 2026 接收 Gemini CLI 个人用户；async subagents；大厂中最慷慨免费档 |
| Copilot CLI | GitHub | 多厂商模型一个订阅；GitHub 原生（issues/PR/MCP 内建）；免费档起 |
| Gemini CLI | Google | ~107k stars；转企业授权与付费 API |
| DeepSeek Harness | DeepSeek | ~249k stars（prerelease，增速最快） |
| Devin | Cognition | 打包式自治工程师；Windsurf 并入为 Devin Desktop；云端交接长任务 |
| 其他 | — | Cursor CLI、Amp、Droid、Muse Code（8 agent/树）、Qwen Code、Kimi Code、Mistral Vibe、Crush、aider… |

### 10.2 方法论 / SDD 框架

| 需求 | 推荐 |
|---|---|
| 存量项目增量修改 | OpenSpec |
| 绿地新功能、Copilot 团队 | Spec Kit |
| 治理/审计/全敏捷链路 | BMAD |
| spec+IDE 一体化 | Kiro |
| 纪律性自治开发 | Superpowers |
| 小改动 | 不上框架：plan mode + AGENTS.md |

### 10.3 编排 / 并行工作区

| 场景 | 工具 |
|---|---|
| 单厂商全套 | Claude Code 桌面端 / ChatGPT 桌面端（Codex）/ Cursor Agents Window / Antigravity 2.0 |
| Mac 上最顺滑的 worktree 流 | Conductor |
| 跨平台免费开源 | Orca（~91k stars）、Emmdash、Nimbalyst |
| 终端原生 | Claude Squad |
| 跨厂商混编 + 看板 | Morphy、BAND |
| 云异步 | Codex Cloud、Claude Code Web、Jules、Devin、Factory、Warp、Copilot cloud agent |

### 10.4 基础设施

- **工具连接**：MCP（Playwright MCP 是全球安装量第一的 server，2680 万/月）
- **仓库指令**：AGENTS.md（6 万+ 项目）
- **技能库**：agentskills.io 标准技能（在册 ~5.9 万个）
- **编辑器协议**：ACP（Zed / JetBrains / Neovim）

---

## 11. 落地路线图

### 个人（第 0 周）

1. 选定 harness（绑定订阅或任意模型二选一）
2. 给仓库提交 AGENTS.md：构建/测试/lint 命令 + 三五条硬约定
3. 养成习惯：非平凡改动先过 plan mode；用 worktree 并行
4. 掌握 TDA：让 agent 先写测试、看到红、再实现

### 个人进阶（第 1-2 月）

5. 建 2-3 个高频 skill（部署流程、代码规范、安全自查）
6. 学会用 subagent 做探索（省上下文）而非自己读全库
7. 云异步跑积压：文档、测试补齐、依赖升级丢给 Tier 3
8. 接受"review 是新瓶颈"：AI review + 人工把关两段式

### 团队（第 2-6 月）

9. 共享 spec/skill 库——让每个人都在团队最好架构师的水平线上工作
10. 选型 SDD 工具（按 brownfield/greenfield/治理需求，见 10.2）
11. 统一 review 门禁：AI pre-review + 人工签核 + CI 全自动检查
12. 引入编排：>6 并行线时上 Tier 2；夜间 Tier 3 排积压

### 组织（第 6-12 月）

13. 上下文工程制度化：六表面分层规范（什么进 AGENTS.md、什么进 hook、什么进 skill）
14. 安全基线：OWASP 清单落地（自治分级、MCP 准入、rules 文件审批流、反 slopsquatting）
15. 指标体系：merge 率 / 每单成本 / 返工轮数 / spec 漂移率，取代单纯速度指标
16. 参与标准：AAIF / MCP / A2A 还年轻到外部团队仍能影响走向；现在写的规则会变成未来产品的内嵌假设

---

## 12. 趋势判断与常见误区

### 12.1 趋势

1. **规范前移**：纪律从代码（人写时代）转移到 spec（agent 写时代）——"瓶颈不再是写代码的速度，而是意图的清晰度"
2. **标准固化**：MCP/A2A/AGENTS.md/Skills 进入中立治理，锁定转移到约定层
3. **执行下沉**：Plan/Review 长在 harness 里，"先想后做"成为默认而非附加
4. **review 与测试自动化**：AI review 已成必需；浏览器 agent + 云运行时让端到端验证成为下一扩张点
5. **异步化**：从 GitHub/下班前丢任务到过夜跑批，工程工作不再必须同步
6. **流程随模型减负**：前沿模型能力越强，重型流程越做减法（Superpowers 的 Native 执行化、7.0 的"让路"设计是信号）——但"裸奔最快也最 buggy"的结论至今成立
7. **三层融合**：in-process/local/cloud 编排趋向单一透明层，按任务特征自动落位

### 12.2 误区

| 误区 | 事实 |
|---|---|
| "方法论落伍了，模型够强直接干" | 裸跑确实最快最便宜，但评测一致显示 bug 显著更多；纪律换的是**质量下限** |
| "SDD 万能" | bug fix/重构/补测试类任务上 spec 开销收不回；按问题规模付费 |
| "所有内容都要塞进 CLAUDE.md" | 常驻上下文是成本；渐进披露（skills）+ 硬规则（hooks）+ 任务注入（specs）各归其位 |
| "安全规则写在指令文件里就够了" | 软约束 ~70% 遵守率；红线必须 hook 硬执行 |
| "agent 读 issue/网页是只读操作，无风险" | 一切 agent 读的内容都是指令源（间接注入） |
| "并行 agent 越多越好" | 调度已商品化，**review 才是稀缺资源**；并行度受 review 容量约束 |
| "有了 AI，测试可以省了" | 恰恰相反：测试是 AI 产出唯一客观的验收锚点，TDD 因 AI 复兴 |
| "star 数 = 生产可用" | MCP 生态 97% 是 solo 项目、54% 超过 90 天无提交；看维护新鲜度与多贡献者，再看 star |

---

## 13. 参考资料

**标准与协议**
- MCP：<https://modelcontextprotocol.io>（规范 2026-07-28 版）；MCP Registry；The Stack / O'Reilly Radar 对 MCP 现状的报道（2026-09）
- Agent Skills：<https://agentskills.io>；AGENTS.md（AAIF 创始项目）
- 协议栈总览：No Hacks, *The Standards Powering the Agentic Web*（2026-02，2026-08 更新）

**方法论**
- Birgitta Böckeler（martinfowler.com）：*Understanding SDD: Kiro, spec-kit, Tessl*（2025-10）
- Thoughtworks：*Beyond Vibe Coding: The Five Building Blocks of AI-Native Engineering*（2026-03）
- Red Hat Developer：*Vibes, Specs, Skills, and Agents*（2026-03）
- InfoWorld：*Vibe Coding or SDD: How to Choose*（2026-05）
- arXiv：*Spec-Driven Development for Agentic Software Engineering*；*SDAD: Spec-Driven Agentic Development*
- Superpowers：<https://github.com/obra/superpowers>；Prime Radiant 博客
- Uvik：*SDD Benchmark 2026*（对照实验数据）

**流程与生态**
- Bilgin Ibryam：*State of AI-Assisted Coding in 2026*（2026-03）
- Addy Osmani 三层编排框架（O'Reilly CodeCon 2026.03）；codex.danielvaughan.com 的解读
- agentic-coding-tools landscape（tomrochette.com，持续更新）；Superset / collaborativecodingagents.com / agentatlas.dev 的对比页

**上下文工程**
- Anthropic Engineering：*Effective Context Engineering for AI Agents*（2025-09）
- amux：*Context Engineering for AI Coding Agents*（2026）；Sourcegraph 同题指南（2026-05）

**安全**
- OWASP Cheat Sheets：*Secure Coding with AI* / *AI Agent Security* / *MCP Security* / *LLM Prompt Injection Prevention*
- LBL Science IT：*AI-Assisted Coding and Agentic Security Review*（含 security-review SKILL.md 模板）

**评估与运营**
- arXiv：*Evaluating and Operating Coding-Agent Systems*（monograph，Agent = Model + Harness）

---

*文档生成于 2026-10-15。协议半年一版、工具一月一更：本地图的"形状"比"数字"更耐久——每季度核对一次数字，形状每年重估一次。*
