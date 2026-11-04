# AGENTS.md — resource 笔记仓库

本仓库是**双端同步的 Markdown 笔记库**：

- **Windows 端**：用 Obsidian 预览与编辑（**唯一编辑端**）；
- **WSL 端**：AI 工具产出 Markdown，不装 Obsidian；
- 两端通过 git（`origin`）同步，统一用 `notes` 脚本命令操作。

## 每次会话的强制流程

1. **动手前先同步**：在本会话**第一次修改 / 写入 / 删除任何文件之前**，必须先执行：

   ```bash
   notes pull
   ```

   把 Windows 端 Obsidian 已推送的修改拉下来（等价 `git pull --rebase --autostash`）。确认无冲突后再开始修改。

2. **产出后推送**：完成产出后执行：

   ```bash
   notes push
   ```

   （等价 `git add -A` → commit → `pull --rebase` → push）

## 硬性约束

- **未经 `notes pull` 不得修改任何文件**，避免在旧版本上覆盖 Windows 端的新改动。
- 若 `notes pull` 失败（网络不可用 / 合并冲突）：
  - **停止修改**，把失败信息报告给用户，等待指示；
  - 严禁跳过该步骤，严禁在旧基础上继续改。
- 不要使用 `git reset --hard`、`git checkout -- .`、`git clean -f`、`git push --force` 等会丢弃工作或改写远端的命令，除非用户明确要求。
- 需要访问 GitHub 等境外服务时依赖主机 Clash 代理（`127.0.0.1:7890`）；但 **git 同步本身按 `origin` 配置直接进行，无需手工设置代理**。

## `notes` 命令

| 命令 | 作用 |
|---|---|
| `notes pull` | 从远端拉取（**开工前必做**） |
| `notes push` / `notes sync` | 提交本地改动并推送（产出后） |
| `notes status` | 查看状态与最近提交 |

脚本：`~/.local/bin/notes`（默认仓库 `~/resource`，可用环境变量 `NOTES_REPO` 覆盖）。

## 仓库其他约定

- 子目录 `AOV/` 有独立且更详细的 `AGENTS.md`；在 `AOV/` 内工作时以那一份为准。
- 文档一律使用**中文**。
- **参考源码克隆一律放在仓库外**：AI 需要克隆第三方源码仓库（如 GitHub 上的开源项目）作参考时，默认克隆到 `~/workspace/repo/` 目录下，**严禁克隆到本仓库内**，避免被 git 跟踪推送、占用远程仓库空间。笔记中引用源码时写清仓库名与来源链接即可，不依赖本地路径。
  - **不得直接散放在 `repo/` 顶层**：AI 在会话中自主决定下载/克隆的仓库，必须放入**为该任务新建的专属子文件夹**（命名体现用途，如 `~/workspace/repo/<任务名或主题-日期>/`，例：`openharmony-research-20261102/`），并在文件夹内放置 README 说明来源与是否可删；
  - 若不确定放置位置是否合适（如仓库体积巨大、与用户已有目录可能混淆、用途存疑），**先向用户征求意见**，不要擅自决定；
  - 任务收尾时如克隆仓已无留存价值，可提示用户归档或删除（涉及删除须用户确认）。
