# DevEco Code 与 DevEco CLI 调研

> 调研日期：2026-11-18
> 调研方式：官方文档（developer.huawei.com）+ 本地安装包源码（npm 包 0.1.9 / deveco-cli 1.2.2）+ 开源仓库（gitcode.com/openharmony-sig/deveco-code）+ 媒体评测（少数派、InfoQ、51CTO 等）

## 一句话总览

两者都是华为 HDC 2026（2026-06）发布的鸿蒙 AI 开发工具，分工不同：

| 工具 | 定位 | 一句话 |
|---|---|---|
| **DevEco Code** | 终端 AI Agent（TUI）+ DevEco Studio 插件 | 基于 OpenCode 二次开发的**开箱即用**鸿蒙 AI 编程工具，你直接跟它对话 |
| **DevEco CLI** | 命令行工具链封装 | 把 DevEco Studio 工具链封装成 **AI 可调用的标准化命令**（`devecocli`），DevEco Code 内部调的就是它，也能给 Cursor/OpenCode/Claude Code 等第三方 Agent 用 |

关系图：`DevEco Code (Agent 外壳) → DevEco CLI (命令层) → hvigor / ohpm / hdc / emulator / hilog (DevEco Studio 工具链)`

---

## 1. DevEco Code

### 1.1 基本情况

- 基于华为 BitFun 技术 + 开源 OpenCode 构建，MIT 协议，**本身开源**：https://gitcode.com/openharmony-sig/deveco-code
- npm 分发：`npm install -g @deveco/deveco-code`（最新 stable 0.3.0 / latest 0.2.5；本地装的 0.1.9）
- 平台：Windows 11、macOS（arm64/x64）、鸿蒙电脑（HarmonyOS 7+）；**不支持 Linux**（华为云/官方 npm 镜像均无 linux-x64 平台包）
- 依赖：Node.js ≥22；构建/推包/模拟器需 DevEco Studio ≥6.1（`DEVECO_HOME` 环境变量）
- 登录华为账号后免费用内置 GLM 模型通道（当前 GLM-5.1，50 req/min）

### 1.2 两种交互形态

| 形态 | 说明 |
|---|---|
| **TUI**（主力） | 终端对话式 Agent，`deveco` 命令启动；完整保留 OpenCode 的 Model/Provider/MCP/Skill/Plugin 配置体系，无需打开 DevEco Studio |
| **Plugin** | 嵌入 DevEco Studio 的可视化面板（侧边栏图标）；**当前仅鸿蒙电脑版**支持在 IDE 内安装，Windows/macOS 只能用 TUI |

Plugin 面板能力（官方文档）：会话管理（新建/重命名/收藏/归档）、模型与 Agent 模式下拉切换、`@文件` 引用、`+` 添加图片附件、编辑器选中代码右键 Quick Chat、以及特色功能 **UX 设计稿生成代码**（`hmos-design-to-arkts` Skill，输入 Pixso 链接自动完成设计稿解析→方案设计→页面实现→多轮视觉校准，分"完整工作流/精简工作流"两档）。

### 1.3 三种 Agent 模式（Tab 键切换）

| 模式 | 自动化程度 | 流程 | 适用 |
|---|---|---|---|
| **Build**（默认） | 中 | 需求理解 → 代码生成 → 修复 → 构建出包 → 推模拟器 | 明确的小需求、页面增量、修 Bug |
| **Plan + Build** | 低→中 | Plan 只读分析、主动追问模糊点、产出任务列表确认后，切 Build 执行 | 复杂需求、跨模块改动 |
| **Goal** | 高 | 交互式需求分析/架构设计/任务拆分 → 生成结构化 spec 文档 → 闭环跑代码生成、语法校验、编译打包、模拟器部署、UI 自动验证、问题修复，迭代到达标 | 完整特性交付、从零建项目（SDD 规格-驱动范式） |

注：Build/Goal 推包验证需先有模拟器（`devecocli emulator list`）。

### 1.4 集成的 HarmonyOS 工具能力（对话流内闭环）

| 工具 | 说明 |
|---|---|
| `build_project` | 编译构建并导出产物 |
| `start_app` | 模拟器/真机运行应用 |
| `hdc_log` | 收集/清理设备日志、查看模拟器 |
| `verify_ui` | UI 自动化操作 + 多模态模型验证界面正确性（默认内置 Qwen3-VL 做视觉判断） |
| `arkts_check` | ArkTS 静态语法检查 |
| `arkts_knowledge_search` | HarmonyOS 知识库搜索 |
| `switch_cwd` | 切换构建项目路径 |

### 1.5 扩展生态（兼容 OpenCode）

- 配置文件：`.deveco/deveco.jsonc` > `deveco.jsonc` > `~/.config/deveco/deveco.jsonc`（schema 与 opencode.jsonc 一致）
- Skills：`~/.config/deveco/skills/`，`npx skills add ...` 可装；内置 `deveco-create-project`、`arkts-grammar-standards`、`arkts-error-fixes`、`arkts-runtime-fix` 等
- MCP：deveco.jsonc 配置（如 Playwright MCP）；另有 `devecocli init --mcp` 一键接入 deveco-mcp（ArkTS/C++ 静态检查）
- 绿灯模式：`"permission": "allow"` 免逐次确认

### 1.6 UI 设计评价

**TUI（一手源码证据，packages/tui）：**

- **主题**：内置 39 套主题（dracula、catppuccin、nord、tokyonight 等主流方案全都有），自研默认主题 `deveco.json`：深色背景 `#0a0a0a`、主色暖橙 `#fab283`、次色蓝 `#5c9cf5`、强调紫 `#9d7cd8`——整体是"深色 + 暖橙主色"的观感，diff 增删行有独立配色与行号背景
- **开场动画**：ASCII 字符画 "DEVECO CODE" 字母标（三层灰度 `▮` 做渐变），挂载时约 4.4s 的多阶段动画（块扫描→逐行揭示→左右收拢→居中定格）+ 扫描线效果，标语 "AI copilot for HarmonyOS application development / Powered by BitFun & OpenCode"
- **组件体系**：完整对话框族（agent/model/provider/mcp/skill/sound/stash/session 等 20+ dialog）、命令面板（command palette）、banner、按钮脉冲动画、i18n（中英）、音效系统（sound-registry）、release-notes 内嵌查看
- **布局**：顶部会话与状态、中部对话流、底部输入框；输入框集成斜杠命令（`/agents` `/models` `/skills` `/connect`）、Tab 切模式、`@` 引用文件；内容最大宽度 110 列自适应收缩

**评价：** 继承 OpenCode 成熟 TUI 骨架（这点直接决定其 TUI 质感在同类 CLI Agent 里属第一梯队），华为的增量主要是品牌层（LOGO 动画、默认主题）和鸿蒙工具链闭环（对话里能直接跑构建/推包/截图验证）。Plugin 形态目前偏"嵌入式聊天面板"，与 Cursor 这类 AI IDE 相比 diff 可视化、任务规划可视化还有空间，且仅鸿蒙电脑可用。

---

## 2. DevEco CLI

### 2.1 基本情况

- npm 包：`@deveco/deveco-cli`（1.2.0 于 2026-07 首发，2026-08 出 1.3.0；**也开源**：gitcode.com/openharmony-sig/deveco-cli）
- 命令名：`devecocli`；Node ≥18（推荐 22）；DevEco Studio ≥6.0 或 Command Line Tools ≥26.0（Linux 必须用 CLT）
- 官方自述：把 hvigor、ohpm、hdc、emulator 工具链 + 2000 多万字 HarmonyOS 知识库 + Skills 安装器封装为一个入口，"Prefer devecocli over invoking underlying tools directly"

### 2.2 命令全景（源自本地 SKILL.md 一手材料）

| 命令 | 能力要点 |
|---|---|
| `create` | 创建工程（Empty Ability 模板，`--app-name` 必填，`--api-level ≥17`） |
| `build` | 编译打包（`--modules`、`--product`、`--build-mode`、`clean`；底层 hvigor） |
| `run` | 构建+安装+启动；**`--apply` 增量推包**（只重编译改动文件打成 hqf 快速补丁安装）；**`--hotreload` 热重载**（后台守护 + socket 连 hvigor daemon，改 `.fontColor` 等非状态代码不重启生效；`@State` 等状态装饰器变更不支持热重载） |
| `signature generate` | 自动生成调试签名全套材料（p12/csr/cer/p7b 写入 build-profile.json5，密码 AES 加密） |
| `check lint` | Code Linter 检查（`--fix` 自动修复，支持 json 输出） |
| `check compat` | SDK 版本间 API 兼容性扫描（基于 arkanalyzer-apiscan） |
| `log` | hilog/崩溃日志（`--level D/I/W/E/F`、`--crash`、`--tail`、`--follow`、`--from 5m`） |
| `device` | `list`/`view`（table 或 json 输出） |
| `emulator` | 模拟器全生命周期：start/stop/create/delete、image download；1.3.0 加场景模拟：`shake`/`rotate`/`fold`（折叠屏三态）/`battery`/`geolocation`/`sensor`/`scene`（跑步/骑行/导航运动模拟） |
| `ui` | UI 自动化：`layout`（ArkUI 无障碍树，simplified 模式折叠无意义容器）、`screenshot`、`click/doubleclick/longclick`、`swipe/fling/dircfling/drag`、`text` 输入（特殊字符 Base64 编码传 shell）；坐标与 `--id` 互斥 |
| `docs` | 本地知识库：`search`/`read`/`catalog`（版本说明/指南/API 参考/最佳实践/FAQ/变更预告六大类，离线可用） |
| `skills` | Skill 市场：`list/find/add/remove`，支持指定 agent（opencode/cursor/trae/atomcode/codebuddy/qoder）安装 |
| `init` | 把 deveco-cli Skill（`--skill`）或 MCP（`--mcp`）配置进第三方 Agent |
| `auth` | 华为账号 OAuth（login/status/logout/team list） |
| `serve mcp` | 启动 stdio MCP server（check/hover/definition/references 等 ArkTS/C++ 语言能力） |

注意平台差异：鸿蒙电脑版不支持 `emulator`、`check compat`。

### 2.3 CLI 的"UI"（命令行体验）评价

**做得好的：**

- 语义命名贴近 IDE 心智：`build`/`run`/`signature`/`emulator`/`docs`，与 DevEco Studio 菜单操作一一对应
- 全面支持 `--format table|json`（设备、模拟器、lint、compat、docs 均可），对 AI Agent 和 CI 极友好
- 错误提示带下一步动作："未登录 → Run devecocli auth login first"；"真机装未签名包 → 建议签名或 --uninstall"；签名相关还有华为云错误码映射（401 重新登录、cert limit 超限等）
- 增量/热重载设计（`--apply` hqf 快速补丁、`--hotreload` 不重启热更）在 AI 迭代场景下是杀手锏——Agent 高频改代码时省掉全量构建
- SKILL.md 官方文件本身就写明了给 AI 的用法约束（"[Outside sandbox]" 标记、明确禁止自动重试镜像下载等），说明其目标用户就是 Agent

**可挑刺的：**

- 命令层级不完全统一（`build clean` 动词后置 vs `emulator start` 动词后置但 `signature generate` 又是名词+动词），严格一致性欠佳
- 几乎无短选项（只有 `-f`/`-t`），人类高频敲会嫌长——但优先服务 AI，可接受
- `dircfling` 这类缩写词不直观；`--api-level` 无法拆分 target/compatible
- `create` 只有 Empty Ability 模板（截至 1.2/1.3），不支持元服务/NDK 工程创建

**总评：** 这不是给人用的传统 CLI，而是**给 AI Agent 设计的鸿蒙工具 API**——长选项自描述、JSON 输出、错误即指引、Skill 注入，人体工学取舍明确偏向 Agent 消费。

---

## 3. 两者关系与选型建议

- DevEco Code = OpenCode（Agent 外壳/交互/生态）+ DevEco CLI（鸿盟能力原子层）+ 预编排模式（Build/Plan/Goal）+ 内置免费模型
- 想一站式、免配置、终端对话闭环 → **DevEco Code**
- 已有习惯的 Agent（Claude Code/OpenCode/Cursor 等）想加鸿盟能力 → `npm i -g @deveco/deveco-cli && devecocli init --agent <你的agent>`
- 两者可同时安装，不冲突

## 4. 风险与注意事项

- AI 编程工具会读取代码/日志/对话：私钥、ClientSecret、生产凭据不要进对话框
- Build/Goal 推包验证依赖本地模拟器，需先 `devecocli emulator license accept` 接受协议
- UI 验证只是线索，深色模式对比度、安全区适配等设计规范仍需真机自查

## 5. 主要信息来源

- 官方文档：https://developer.huawei.com/consumer/cn/doc/HarmonyOS-Guides/ide-deveco-code-overview（及同目录 install/agent/model/common-configure/plugin-install 页）
- DevEco CLI 官方文档：https://developer.huawei.com/consumer/cn/doc/doccenter-deveco-studio/ide-deveco-cli-options
- 开源仓库：https://gitcode.com/openharmony-sig/deveco-code （本地克隆：~/workspace/repo/deveco-research-20261118/）
- 官方博客：https://developer.huawei.com/consumer/cn/blog/topic/03225653661217201
- 少数派评测（截图最全）：https://sspai.com/post/112886
- 本地一手材料：npm 包 `@deveco/deveco-code` 0.1.9 + 内置 `@deveco/deveco-cli` 1.2.2 的 README/SKILL.md/源码
- 截图证据：/tmp/opencode/deveco-research/（23 张，含 TUI 界面、Plugin 面板、官方文档页）

## 附：本地环境备忘

- WSL 下 `deveco` 命令报错（npm 无 linux-x64 平台包）——DevEco Code 不支持 Linux，须在 Windows/macOS 侧运行
- Windows 端 npm 全局已装 0.1.9（`/mnt/c/Users/26099/AppData/Roaming/npm/node_modules/@deveco/`）
- 华为云 npm 镜像（repo.huaweicloud.com）同步滞后于官方源，README 建议用 npmjs 或淘宝镜像安装
