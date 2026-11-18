# DevEco Code + DevEco CLI 使用攻略：对照 DevEco Studio 完成同样的工作

> 撰写日期：2026-11-18
> 前置阅读：[[DevEco Code 与 DevEco CLI 调研]]（工具定位与功能全景）
> 适用版本：DevEco Code 0.2.x / DevEco CLI 1.3.x / DevEco Studio ≥6.1

## 0. 核心心智模型

DevEco Studio 的工作方式是**你在 GUI 里点**；DevEco Code + CLI 的工作方式是**你说需求，AI 调命令**。三者能力分层：

```
你 ──对话──> DevEco Code (AI Agent，决定"做什么")
                │
                └──调用──> DevEco CLI (devecocli，原子命令，决定"怎么做")
                              │
                              └──驱动──> hvigor / hdc / emulator / hilog (DevEco Studio 工具链)
```

所以对照关系很简单：**Studio 里每个按钮 ≈ CLI 里一条命令 ≈ Code 里一句话**。记住这个映射，就能无障碍迁移。

---

## 1. 环境准备（一次性，10 分钟）

| 步骤 | 命令/操作 | 对应 Studio 的什么 |
|---|---|---|
| 装 Code | `npm install -g @deveco/deveco-code@stable` | 装 Studio 本体 |
| 装 Studio 工具链 | 装 DevEco Studio ≥6.1，设 `DEVECO_HOME` | （Studio 本身） |
| 登录 | `deveco` 首启引导登录华为账号（送免费 GLM 通道） | Studio 登录华为账号 |
| 模拟器协议 | `devecocli emulator license accept` | 首次开模拟器弹的协议勾选 |
| （可选）接入第三方 Agent | `devecocli init --agent cursor,claude-code` | 无对应 |

> WSL/Linux 用户注意：DevEco Code 无 Linux 包，只能在 Windows/macOS 侧跑。

---

## 2. 项目全生命周期对照表（核心章节）

以下按一个 HarmonyOS 项目的实际开发顺序，逐环节对照。

### 2.1 新建工程

- **Studio**：File → New → Create Project → 选模板 → 填 App name / Bundle name / SDK 版本
- **Code（推荐）**：直接对话——
  > "创建一个待办事项应用，包名 com.myname.todo，保存到 D:\projects\todo"
- **CLI**：
  ```bash
  devecocli create --app-name ToDo --project-path ./todo \
    --bundle-name com.myname.todo --api-level 23
  ```

差异提示：CLI 目前只有 Empty Ability 模板；但用 Code 对话可以让 AI 在空模板上生成页面结构，实际比选模板更灵活。

### 2.2 日常写代码 / 改功能

- **Studio**：编辑器手写 ArkTS + ArkUI，靠代码补全和预览器反馈
- **Code（Build 模式，默认）**：描述需求即可——
  > "首页加一个搜索框，输入后过滤下方列表"（它会改代码 → 编译 → 修错 → 推包）
  > "帮我重构 login_check 这个函数"
- **提效技巧**：
  - 输入框按 `Tab` 切 Build / Plan / Goal 模式；输入 `/` 调出命令面板（`/agents` `/models` `/skills`）
  - `@文件名` 精确引用上下文，避免 AI 瞎猜
  - 需求大且模糊 → 先切 **Plan** 模式让它追问、出任务清单，确认后切 **Build** 执行

### 2.3 看界面效果（替代 Studio 预览器的工作流）

Code/CLI **没有 Previewer**，这是与 Studio 最大的体验差异。替代方案是"真模拟器即时反馈"闭环，实测体验不差：

```bash
# 一次全量部署（构建+安装+启动）
devecocli run --module entry

# 之后每改一轮代码，增量热更新（秒级，不重启应用）：
echo entry/src/main/ets/pages/Index.ets > .hvigor/changes.txt
devecocli run --module entry --hotreload-apply changes.txt
```

- 热重载需先起守护进程：`devecocli run --module entry --hotreload`（后台运行），结束时 kill 掉 + `devecocli run --hotreload stop`
- 限制：改 `@State` 等状态装饰器、资源文件、native 代码不支持热重载，需走全量 `run`
- 在 **Code** 里不用手敲：直接说"改一下列表标题颜色"（Build 模式自己走 build → 推包），或"验证 UI"让它截图+点击自检

### 2.4 编译构建

- **Studio**：Build → Build Hap(s)/App(s)
- **Code**：> "帮我编译当前工程"
- **CLI**：
  ```bash
  devecocli build                              # 单模块
  devecocli build --modules entry library      # 多模块
  devecocli build --product default --build-mode release   # 发布包
  devecocli build clean                        # 清理
  ```

### 2.5 签名（Studio 自动签名按钮的等价物）

- **Studio**：File → Project Structure → Signing Configs → 勾 Auto signature
- **CLI（一次配好，永久生效）**：
  ```bash
  devecocli auth login              # 先登录华为账号
  devecocli signature generate      # 自动生成 p12/csr/cer/p7b 并写入 build-profile.json5
  ```
- 之后 `run` 推真机/模拟器自动带签名。签名材料变化导致装不上时：`devecocli run --uninstall`

### 2.6 运行到模拟器/真机

- **Studio**：Device Manager 选设备 → 点 Run ▶
- **Code**：> "把应用跑到模拟器上"（内部走 start_app → devecocli run）
- **CLI**：
  ```bash
  devecocli emulator list                      # 看有哪些模拟器
  devecocli emulator start "Phone"             # 启动
  devecocli run                                # 唯一设备时全自动；多设备加 --device
  devecocli run --device 127.0.0.1:5555 --module entry
  devecocli device list                        # 看真机连接
  ```

### 2.7 调试：看日志、查崩溃

- **Studio**：底部 Log 窗口（hilog 过滤）/ DevEco Studio 的 crash 分析面板
- **Code**：> "应用闪退了，帮我查一下"（AI 自己抓崩溃日志→定位→改→重新推）
- **CLI**：
  ```bash
  devecocli log --follow --bundle-name com.myname.todo    # 实时日志（等价 Studio Log 过滤）
  devecocli log --crash --bundle-name com.myname.todo    # 崩溃日志
  devecocli log --level E --from 5m --tail 200           # 最近 5 分钟 ERROR 级
  ```

⚠️ **断点调试仍是 Studio 独占**。Code/CLI 没有调试器，复杂逻辑问题（异步时序、内存）回 Studio 挂断点。

### 2.8 修编译报错

- **Studio**：看 Problems 面板 → 逐个点过去手改
- **Code（这是它最甜的场景）**：> "修复编译报错"——AI 读报错 → 改代码 → 重编译 → 直到通过 → 推包，全程不用你管。ArkTS 语法规范还会被 `arkts_check` / `devecocli check lint --fix` 兜底。

### 2.9 代码规范 & API 兼容检查

- **Studio**：Code Linter 面板 / SDK 升级时的迁移向导
- **CLI**：
  ```bash
  devecocli check lint --fix                # 规范检查+自动修复
  devecocli check compat versions           # 看可升级的目标 SDK
  devecocli check compat --source-version "API 23" --target-version "API 26" \
    --output-path ./report                  # 扫描两版本间的破坏性变更，出 csv/json 报告
  ```

### 2.10 查开发文档

- **Studio**：跳浏览器搜 developer.huawei.com
- **Code**：> "沉浸光感怎么用"（走 arkts_knowledge_search）
- **CLI**：
  ```bash
  devecocli docs catalog
  devecocli docs search "@State" "@Prop" --catalog best-practices --limit 5
  devecocli docs read 开发指南/.../某文档ID     # 读全文，离线可用（2000万字本地库）
  ```

### 2.11 UI 功能验证（Studio 里得手动点的活）

- **Studio**：人肉点模拟器逐项验证
- **Code**：Build/Goal 模式收尾时自动做，或手动说 > "验证 UI"——AI 在模拟器上执行点击/滑动/输入，截图交给多模态模型判断对错，输出问题报告
- **CLI 手动版**：
  ```bash
  devecocli ui screenshot --path ./shots           # 截图
  devecocli ui layout --mode simplified            # 拉无障碍树（只含可见节点，带 id/坐标/文本）
  devecocli ui click --id submit_button            # 点它
  devecocli ui text "hello" --id search_box        # 输入
  devecocli ui dircfling down                      # 滚一下
  ```
- 验证完的截图可作为证据发回给 Code：> "看看这张截图，列表间距是不是不对"

### 2.12 需求级交付（Studio 完全没有的能力）

这是两个新工具真正的增量，Studio 没有对应物：

| 模式 | 用法 | 适合 |
|---|---|---|
| **Plan** | > "我想加一个用户头像上传功能" → 它追问细节出任务清单 → 确认后切 Build 执行 | 复杂需求，想可控 |
| **Goal** | > "从零做一个天气应用：定位+3日预报+城市管理页" → 交互确认方案后生成 spec 文档 → 全自动编码/编译/部署/UI 验证迭代到底 | 完整特性、从零建项目 |

多人协作场景，Goal 产出的 spec 文档可直接作为任务分配和验收依据。

---

## 3. 三种人设的推荐工作流

### A. 纯终端党（不再开 Studio 日常窗口）
```
deveco  →  一条龙（写码/编译/推包/日志/UI验证全在对话里）
```
Studio 只保留两个用途：装它（工具链依赖）+ 断点调试。

### B. 已有 AI 工具党（主力用 Cursor/Claude Code/OpenCode）
```bash
npm i -g @deveco/deveco-cli
devecocli init --agent cursor        # 注入 Skill；--agent 支持 opencode/cursor/trae/atomcode/codebuddy/qoder
# 需要静态检查能力再挂 MCP：
devecocli init --mcp --agent cursor --project ./
```
你的 Agent 从此会说"鸿蒙话"：直接调 devecocli 全套命令 + 离线知识库检索。

### C. 混合党（推荐大多数人）
- **写码、改码、修编译错、闭环验证** → Code（效率碾压手改）
- **预览器看 UI** → Studio（或改用 2.3 节热重载流）
- **断点调试、可视化重构、工程结构配置** → Studio
- **需求级新特性** → Code Goal 模式
- **发版**：> "出个 release 包"（CLI：`devecocli build --product default --build-mode release`）

---

## 4. 提效与避坑清单

**必开的配置**（`~/.config/deveco/deveco.jsonc` 或项目 `.deveco/deveco.jsonc`）：
```jsonc
{ "permission": "allow" }   // 绿灯模式：工具调用免逐次确认，否则每步都要按 y
```

**高频技巧**：
- 迭代改 UI 属性（颜色/字号/文案/方法体）→ 热重载 `--hotreload-apply`，秒级生效
- 改动较大但不想全量 → `--apply changes.txt` 增量补丁（hqf），远快于全量 run
- CLI 输出接脚本/CI → 加 `--format json`
- 模拟器疑难杂症（传感器/GPS/折叠态测试）：`devecocli emulator fold open / geolocation / sensor` 一条命令模拟，真机做不到

**常见坑**：
| 症状 | 解法 |
|---|---|
| `install sign info inconsistent` | 签名变了：`devecocli run --uninstall` 或 `signature generate --force` |
| 模拟器启动卡住/镜像下载超时 | 官方明确**不要自动重试**，自己终端手动跑 `emulator image download` |
| 热重载改动不生效 | 检查改动是否含 `@State`/资源/native——这些必须全量 run |
| 多设备连着，run 报错 | 加 `--device <serial>`（`device list` 查） |
| 知识库/模型突然 401 | Token 过期，重新 `devecocli auth login` |
| 敏感信息 | 私钥/ClientSecret/生产凭据**永远不进对话框**，需要展示结构就用 `${CLIENT_SECRET}` 占位符 |

**仍是 Studio 不可替代的**：Previewer 预览器、断点调试器、可视化重构、多模块工程结构配置界面、专属模拟器高级管理面板。遇到这些需求别硬用 Code/CLI。

---

## 5. 一个真实需求的全流程示例

以"给现有应用加夜间模式开关"为例：

| 步骤 | 传统 Studio 做法 | Code + CLI 做法 |
|---|---|---|
| 1. 理解现状 | 人肉翻代码找主题相关逻辑 | Code: "当前应用的主题色在哪里定义的？" |
| 2. 方案 | 自己想 | 切 Plan: "加一个夜间模式设置项，持久化保存" → 追问 → 出清单 |
| 3. 实现 | 手写 ArkTS + 改资源 | 切 Build: "按刚才的清单实现" |
| 4. 看效果 | 预览器/手动跑 | 自动：build → run 推包（或热重载秒更） |
| 5. 验证 | 手动点 | 自动 verify_ui：切开关→截图→多模态判断 |
| 6. 出问题 | 看日志面板 | `devecocli log --crash --bundle-name ...` 或直接说"帮我查" |
| 7. 回归 | 自己点一遍 | "再整体验证一遍 UI" |

全程 Studio 可以一次都不开（除非要断点调试）。

---

## 附：CLI 速查表（按 Studio 菜单分组）

| Studio 操作 | CLI 命令 |
|---|---|
| New Project | `devecocli create --app-name X` |
| Build 菜单 | `devecocli build [--modules --product --build-mode release\|clean]` |
| Auto Signing | `devecocli auth login` → `devecocli signature generate` |
| Run ▶ | `devecocli run [--module --device --uninstall --apply --hotreload]` |
| Device Manager | `devecocli device list` / `emulator list\|start\|stop\|image download` |
| Log 窗口 | `devecocli log [--crash --level --follow --tail --bundle-name]` |
| Code Linter | `devecocli check lint [--fix --incremental]` |
| API 迁移向导 | `devecocli check compat --source-version .. --target-version ..` |
| 预览器（无） | `run --hotreload-apply` + `ui screenshot/layout` 替代 |
| 官网文档搜索 | `devecocli docs search <关键词>` |
| —（AI 集成） | `devecocli init --agent <cursor\|opencode\|...>` / `serve mcp` |
