# 端侧 Agent 与工具调用

> 2026-10-23 初稿。Agent 是端侧 AI 的"终极形态假设"：AI 成为新的 UI（Qualcomm 语）。
> 相关：[[端侧RAG与个性化记忆]]、[[Hybrid AI架构]]、[[SLM设计演进]]、[[投机解码与加速]]

## 0. TL;DR

- 端侧 Agent 的能力栈 2025 年快速成型：**工具调用（端模型驱动 App 功能）+ 系统语义索引（App Intents/实体 schema）+ 屏幕理解（GUI agent）**
- Apple 的设计最具系统性：Foundation Models 的 **tool calling 构建在 guided generation 之上**（类型安全、永不产生非法调用名/参数）+ **App Intents 生态**（App 功能自动被 Siri/Spotlight 可达）+ **View Annotations**（屏幕内容感知）
- 小模型做 Agent 的可行性证据：Apple **Ferret-UI Lite（3B）** 在 GUI grounding 上达 91.6%（ScreenSpot-V2）、AndroidWorld 导航成功率 28%——配方是数据混合 + CoT + 视觉工具 + RL
- 关键张力：**Agent 的长程多步推理正是 SLM 最弱的能力**（ACL survey：ICL 受限；IJCAI：量化小模型在指令遵循上掉点）——端侧 Agent 的真正瓶颈不是工具调用而是规划

## 1. 工具调用：三家范式

### 1.1 Apple：类型安全的工具调用

（[WWDC25 Foundation Models](https://developer.apple.com/videos/play/wwdc2025/286/)）

```
Tool 协议（Swift）→ 编译期宏 @Generable 生成 schema
→ 模型输出经 guided generation 约束解码（永不非法）
→ 框架自动执行 → 结果回填 transcript → 模型整合作答
```

- **工具调用 = guided generation 的应用**：模型不可能产生无效工具名/参数——把"结构化输出"做成了安全边界而非事后校验
- **instructions 与 prompts 的分离**：模型被训练为"指令优先于提示"，是对抗 prompt injection 的系统性设计（官方也承认"not bulletproof"）
- 有状态会话（transcript）支持多轮工具往返；支持运行时动态 schema
- 2025 年扩展：**Language Model 协议**——Apple FM / Claude / Gemini / 任意供应商统一进一个 Swift API；**Dynamic Profiles** 在会话中动态换模型/工具/指令；Evaluations 框架做行为回归测试

### 1.2 Apple：App Intents——工具的"供给侧"

（[WWDC25 App Intents](https://developer.apple.com/videos/play/wwdc2025/244/)）

工具调用的难点从来不是调用侧，而是**工具从哪来**。Apple 的答案：

- App 声明 **intents（动词）+ App Entities/Enums（名词）**，系统自动暴露给 Siri / Spotlight / 快捷指令 / Action Button
- **Entity schemas 贡献进 Spotlight 语义索引**——App 内容天然进入系统级检索（与 [[端侧RAG与个性化记忆]] 的系统索引路线呼应）
- **View Annotations API**：把屏幕上的视图映射为实体——"对眼前内容说话"的屏幕感知
- 系统定义 schema（任务管理/照片编辑/通信等类别）自动受益于 Siri 的后续进化——**App 零成本跟随模型升级**

### 1.3 Google：Function Calling 库

- [AI Edge Function Calling 库](https://developers.googleblog.com/en/google-ai-edge-small-language-models-multimodality-rag-function-calling/)：与 RAG 库并列的端侧标准件，配合 LiteRT-LM 模型（Gemma 系后训练支持）
- 安卓侧对应物：AICore（系统 Gemini Nano）+ intents 生态

### 1.4 MCP：协议层的变量

Model Context Protocol 成为工具接入的事实开放标准（云端为主）。端侧现状：**Apple/Google 都用自家 schema 体系而非 MCP**——端侧的"工具发现"绑定 OS 权限模型，短期难以协议化；但第三方端侧 Agent 框架（llama.cpp 生态等）已在接 MCP。观察点：OS 厂商是否最终提供 MCP 网关。

## 2. GUI Agent：屏幕作为通用接口

（[Ferret-UI Lite (arXiv:2509.26539)](https://arxiv.org/html/2509.26539)，Apple）

- 任务：直接从截图到动作（点击坐标/手势），跨 mobile/web/desktop
- **3B 端侧模型的配方**（对小模型 Agent 有普适参考价值）：
  1. 真实+合成混合的 GUI 数据（图标识别/find text/widget listing 等基础任务 → 描述/对话/功能推断等高阶任务）
  2. 推理期：CoT + **视觉工具**（放大镜式局部观察——用工具弥补小模型感知）
  3. RL with designed rewards（grounding 坐标精度、导航成功率）
- 成绩：ScreenSpot-V2 91.6% / ScreenSpot-Pro 53.3% / OSWorld-G 61.2%；导航 AndroidWorld 28.0%、OSWorld 19.8%
- 定位清醒：与"更大模型的多智能体系统"竞争不现实，端侧价值在**延迟、隐私、离线**（帮用户点按钮不需要 GPT 级世界知识）

## 3. 端云分工下的 Agent

Agent 是对 [[Hybrid AI架构]] 的最大压力测试：

- **规划上云、执行在端**：云模型拆解任务 → 端侧模型+App Intents 执行（与 MINIONS 的"云分解-端执行"同构，见 [[Hybrid AI架构]] §2.2）
- **隐私动作只留端侧**：读屏、翻相册、操作银行 App——Ferret-UI Lite 这类端侧 GUI agent 的不可替代场景
- **结构化输出是端云协作的粘合剂**：端侧 guided generation 保证工具调用合法，云端规划者才能信任端侧执行者

## 4. 关键洞察

1. **端侧 Agent 的瓶颈是规划不是调用**：工具调用已被 guided generation 工程化解决（可靠性是编译期保证的）；多步规划/自我纠错仍是 SLM 死穴——这解释了为什么各家都把"任务分解"交给云端或开发者
2. **"工具供给侧"是 OS 厂商的护城河**：Apple 的杀手锏不是 3B 模型而是 App Intents 十年积累的 intent/entity 生态——模型可以换，工具生态不可速成
3. **安全模型内建于 API 形态**：instructions/prompts 分离、类型安全调用、Evaluations 回归框架——Apple 把 Agent 安全当作 API 设计问题而非部署文档问题
4. **GUI agent 是"AI as UI"的实证**：当屏幕理解 + 意图执行在端侧闭环，App 不需要为 AI 改造（无障碍树之外零适配成本）——这与 App Intents 的"深度整合"路线形成有趣的对冲：**通用屏幕操作（无需适配）vs 语义化意图（深度整合）**

## 5. 开放问题

- [ ] 端侧 Agent 的权限模型：屏幕读取 + 工具执行 + 记忆的组合授权如何不变成监控软件
- [ ] 小模型多步规划的可行性边界（Ferret-UI 28% 成功率距离可用还远——多少步以内可靠？）
- [ ] MCP 与 OS intent 体系的互通（谁做网关）
- [ ] Agent 工作流与投机解码的协同（结构化任务高可预测性 = 高接受率，见 [[投机解码与加速]] §5）

## 6. 来源

- [WWDC25: Meet the Foundation Models framework](https://developer.apple.com/videos/play/wwdc2025/286/)（tool calling / guided generation / sessions）
- [WWDC25: Get to know App Intents](https://developer.apple.com/videos/play/wwdc2025/244/) / [What's New - Apple Intelligence](https://developer.apple.com/apple-intelligence/whats-new/)
- [Ferret-UI Lite: Small On-Device GUI Agents (arXiv:2509.26539)](https://arxiv.org/html/2509.26539) / [Ferret-UI 原始论文](https://machinelearning.apple.com/research/ferretui-mobile)
- [Google AI Edge：Function Calling 库公告](https://developers.googleblog.com/en/google-ai-edge-small-language-models-multimodality-rag-function-calling/)
- [Qualcomm 白皮书："AI 正在成为新的 UI"](https://www.qualcomm.cn/content/dam/qcomm-martech/dm-assets/documents/files/ai_whitepaper/ai_whitepaper_2025.pdf)
