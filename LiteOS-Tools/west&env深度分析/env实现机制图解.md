# env 实现机制图解

> 撰写日期：2026-10-12 ｜ 代码基线：env **v2.0.2**（commit `ec2c251`）+ env-windows **v2.1.0**（commit `fc857c5a`）+ rt-thread **v5.3.0**
> 源码位置：`~/workspace/repo/env`、`~/workspace/repo/env-windows`、`~/workspace/repo/rt-thread`
> 本文是《Env实现机制深度分析.md》的**图解配套版**：以图为主重建全部结论，行号引证与文字版一致。
> 图类型：mermaid 流程图 / 时序图 / 类图 / 状态图（VSCode、Typora、GitHub 可直接渲染）+ ASCII 目录图。
> 阅读路线：§1 总览 → §2 安装与激活 → §3 venv 自举 → §4 menuconfig → §5 pkgs → §6 SDK → §7 插件与 WebUI → §8 构建与导出 → §9 Windows 链 → §10 设计评价。

---

## 1. 总体架构：一张图看懂 env 是什么

### 1.1 分层架构图

```mermaid
flowchart TB
    subgraph ENTRY["入口层"]
        CS["pyproject.toml console-scripts<br/>rt-env / menuconfig / pkgs / sdk / system / webui"]
        WRAP["~/.env/tools/scripts/{menuconfig,pkgs,sdk}<br/>3 行 bash 转发脚本"]
    end

    subgraph APP["应用层 env.py + cmds/（命令编排）"]
        ENV["env.py (297行)<br/>argparse 分发 / 版本警告<br/>BSP_ROOT=cwd / RTT_ROOT 发现"]
        MENU["cmd_menuconfig.py<br/>(350行)"]
        PKG["cmd_package/*<br/>(2173行)"]
        SDK["cmd_sdk.py (81行)"]
        PLUG["cmd_plugin.py + cmd_webui.py"]
        SYS["cmd_system.py (60行)"]
    end

    subgraph CORE["核心库层（可独立 import）"]
        VENV["env_venv.py (521行) ★<br/>venv 自举/指纹"]
        SDKM["sdk_manager.py (1134行) ★<br/>SDK plan/apply"]
        TCM["toolchain_manager.py<br/>sdk_cfg.json 登记簿"]
        PKGCORE["package.py / pkgsdb.py<br/>archive.py / network.py"]
        KC["kconfig.py (100行)<br/>.config 字符串解析"]
        PLUGINS["plugins/ (~4000行)<br/>epack / market / dispatcher / webui"]
    end

    subgraph DATA["数据层 ~/.env（三仓 + venv）"]
        REPO1["tools/scripts<br/>(env 仓 clone)"]
        REPO2["packages/packages<br/>(包索引仓)"]
        REPO3["packages/sdk<br/>(SDK 索引仓)"]
        VENVDIR[".venv<br/>(rt-env 安装处)"]
    end

    subgraph RTT["rt-thread 仓（消费方）"]
        BUILD["tools/building.py<br/>PrepareBuilding/DoBuilding"]
        EXP["tools/targets/<br/>21 个 IDE 导出器"]
        ENVU["tools/env_utility.py<br/>GetSDKPath"]
    end

    GIT["git + HTTP（全部外部依赖）"]

    ENTRY --> APP --> CORE --> DATA
    PKG --> REPO2
    SDKM --> REPO3
    VENV --> VENVDIR
    APP -. "构建时" .-> RTT
    BUILD --> ENVU
    ENVU -. "查 pkgs.json / sdk_cfg.json" .-> SDKM
    PKGCORE --> GIT
    PLUGINS --> GIT
```

**要点**：
- env 与 west 最深的差异：**west 是"全局 pip 包 + workspace"，env 是"venv 自举 + ~/.env 数据目录"**——env 的代码本身就是 `~/.env/tools/scripts` 这个 git clone，激活时装进 venv。
- **BSP 根 = cwd**（`env.py:209-210`），无任何向上搜索机制；RTT 根靠扫描 BSP Kconfig 的 `lines[i+3]`（`env.py:171`）。
- 核心外部依赖仅 git + HTTP；构建/烧录全部由 rt-thread 侧 SCons 世界承担。

### 1.2 三个核心抽象（后文所有图围绕它们）

```mermaid
mindmap
  root((env 三大抽象))
    venv 自举状态机
      源指纹 SHA-256 驱动
      created repaired upgraded current
      git pull 即升级
    .config 单一事实源
      menuconfig 人机层
      rtconfig.h 编译层
      pkgs.json / sdk 选择 派生物
    目录即安装
      packages name-ver
      SDK name-version
      SConscript 桥接约定
```

---

## 2. 生命周期：从安装到命令执行

### 2.1 安装 + 激活总流程（POSIX）

```mermaid
flowchart TD
    A["curl install_ubuntu.sh | bash"] --> B["宿主只装基础包<br/>python3 python3-venv gcc git libncurses5-dev<br/>(install_ubuntu.sh:14-16，不碰宿主 pip)"]
    B --> C["touch_env.sh"]
    C --> C1{"ipinfo.io/country<br/>== CN?"}
    C1 -->|是| C2["三仓 URL 换 Gitee<br/>(touch_env.sh:7-11)"]
    C1 -->|否| C3["保持 GitHub URL"]
    C2 & C3 --> D["git clone --depth=1 ×3<br/>packages/packages, packages/sdk, tools/scripts"]
    D --> E["生成 packages/Kconfig<br/>source $PKGS_DIR/packages/Kconfig"]
    E --> F["⚠️ 三个 origin 全部 set-url 回 GitHub<br/>(touch_env.sh:36-38)"]
    F --> G["~/.env 就绪"]

    G --> H["每次新会话: source ~/.env/env.sh"]
    H --> I["选引导 python3<br/>(env.sh:19-25)"]
    I --> J["python env_venv.py --venv ... --source ...<br/>(env.sh:34-38)"]
    J --> K{自举判定 §3}
    K -->|current| L["零开销通过"]
    K -->|需安装/升级| M["install_env + 确认"]
    L & M --> N["source .venv/bin/activate"]
    N --> O["PATH=$ENV_SCRIPTS_ROOT:$PATH<br/>RTT_EXEC_PATH=/usr/bin (env.sh:55-56)"]
    O --> P["rt-env --info 横幅"]

    style K fill:#f9f,stroke-width:2px
    style F fill:#ff9
```

**会话级承诺**：env.sh 全部 `export` 只影响当前 shell；不写 rc 文件、不写系统配置——每次新终端都要重新 source。

### 2.2 命令执行链（`main()`，env.py:249-266）

```mermaid
sequenceDiagram
    participant U as 用户 (BSP 目录内)
    participant E as env.py
    participant C as cmds/cmd_*.py
    participant V as vars.Export

    U->>E: pkgs --update
    E->>E: show_version_warning()<br/>rtdef.h 版本 ≤5.1.0 只警告不阻断 (:83-103)
    E->>E: export_environment_variable()<br/>ENV_ROOT/PKGS_ROOT/PKGS_DIR/BSP_ROOT → os.environ (:213-228)
    E->>V: Export(env_root/pkgs_root/bsp_root)<br/>sys._getframe(1).f_locals 抓局部变量 (:26-33)
    E->>C: run_command → args.func(args)
    alt PluginError
        C-->>E: exit_code 透传 (:51-53)
    else CalledProcessError
        C-->>E: 命令+返回码打印 (:54-56)
    end
    Note over E: 返回值翻译：bool→0/1，负 int→1 (:60-64)
```

---

## 3. venv 自举子系统——env 的"心跳"（env_venv.py）★

### 3.1 源指纹算法

```
iter_runtime_files(source_root)                          (env_venv.py:43-67)
  ├─ 根目录：所有 *.py + MANIFEST.in/env.json/env.sh/env.ps1/pyproject.toml/setup.py
  ├─ 目录：cmds/、plugins/ 整树
  └─ 排除：.git / __pycache__ / build / dist / node_modules /
           plugins/examples / plugins/tests / plugins/webui/frontend / *.md / *.rst

source_fingerprint()  (env_venv.py:113-131)
  digest = SHA-256()
  for file in runtime_files:
      digest ← utf8(相对路径) ← b"\0" ← 文件内容(1MiB 块) ← b"\0"
  return digest.hexdigest()

  ⇒ 指纹 = "运行时源文件集合 × 路径 × 内容" 的总 digest
  ⇒ 改任何一行脚本 ⇒ 指纹变 ⇒ 下次激活触发重装
```

### 3.2 `ensure_environment()` 决策图（:410-469）

```mermaid
flowchart TD
    A["ensure_environment()"] --> B["initial_install =<br/>not venv_is_usable (python+activate 都在?)"]
    B --> C["fingerprint = source_fingerprint()"]
    C --> D["state = read_state(.venv/.rt-thread-env-state.json)"]
    D --> E["source_changed = 指纹 ≠ state.fingerprint"]
    E --> F["activation_changed = env.sh 源 ≠ 激活目标 (filecmp)"]
    F --> G["package_missing = venv 内无 rt-env 命令"]
    G --> H{"initial_install?"}
    H -->|是| I["python -m venv .venv<br/>(host python = sys._base_executable)"]
    H -->|否| J{"upgrade_required<br/>且非 --yes/ENV_VENV_AUTO_UPGRADE?"}
    J -->|是| K["交互确认 confirm_upgrade()<br/>拒绝 → return 'declined'"]
    J -->|否| L{"initial_install ∨ package_missing<br/>∨ upgrade_required ?"}
    K -->|确认| L
    L -->|全否| M["return 'current' ✅ 零开销快路径"]
    L -->|是| N["select_index_url() → 镜像 §3.3"]
    N --> O["install_env()：ensurepip --upgrade<br/>→ (首次) pip upgrade pip<br/>→ pip install --upgrade-strategy only-if-needed<br/>　<本地 tools/scripts 源码目录> (:347-377)"]
    O --> P["rt-env 命令仍不存在 → BootstrapError"]
    P --> Q["sync_activation_script + write_state<br/>{schema:1, source, fingerprint, version, index}"]
    Q --> R["return created / repaired / upgraded"]

    style M fill:#9f9
    style O fill:#ff9
```

### 3.3 PyPI 镜像三级决策（`select_index_url()`，:265-284）

```mermaid
flowchart LR
    A["ENV_PYPI_INDEX_URL<br/>环境变量"] -->|设置| Z["直接用"]
    A -->|未设| B["network.pypi_index_url()<br/>~/.env/var/network.json"]
    B -->|pypi_mode=default| Z2["用 PyPI 官方源"]
    B -->|auto/mirror| C["ipinfo.io/country<br/>UA=RT-Thread-Env/2<br/>强制绕代理 3s 超时 (:256-262)"]
    C -->|CN| D["阿里云镜像<br/>mirrors.aliyun.com/pypi/simple"]
    C -->|其他/失败| Z2
```

### 3.4 自举状态机

```mermaid
stateDiagram-v2
    [*] --> created: 首次（venv 不存在）
    created --> current: 无变化
    current --> upgraded: 源指纹变 / 激活脚本变<br/>(git pull 后)
    current --> repaired: rt-env 命令丢失
    upgraded --> current
    repaired --> current
    current --> declined: 升级确认被拒（保持旧版可用）
```

---

## 4. menuconfig 数据流：一条 `.config`，两个消费者

### 4.1 配置生成与分流

```mermaid
flowchart TD
    subgraph GEN["生成（cmd_menuconfig.py）"]
        A["cwd/Kconfig (BSP 入口)"] --> B["source $PKGS_DIR/packages/Kconfig<br/>（包索引菜单接入）"]
        B --> C{"模式"}
        C -->|交互| D["menuconfig._main() (kconfiglib TUI)<br/>kconfiglib_fix_locale 先行 (:179-189)"]
        C -->|--silent| E["defconfig.main() 非交互 (:253-255)"]
        C -->|--generate| F["直接 mk_rtconfig"]
        D & E --> G[".config"]
        G --> H{"mtime 变了?"}
        H -->|是| I["mk_rtconfig() → rtconfig.h (:112-176)"]
    end

    G --> J{"SYS_AUTO_UPDATE_PKGS?<br/>(cmds/.config)"}
    J -->|y| K["自动 env.py pkg --update (:272-284)"]
    J -->|n| L["等待用户手动"]
    I --> M{"SYS_CREATE_MDK_IAR_PROJECT?"}
    M -->|y| N["自动 scons --target=mdk5/... (:285-303)"]

    subgraph CONS1["消费者①：编译层"]
        O["rtconfig.h"] --> P["building.py:351-356 SCons 预处理<br/>→ BuildOptions dict"]
        P --> Q["GetDepend() (:511-527)<br/>门控 DefineGroup"]
    end

    subgraph CONS2["消费者②：包生命周期"]
        R[".config"] --> S["kconfig.py:51-96 字符串解析<br/>只取 CONFIG_PKG_*_PATH / _VER<br/>⚠️ USING_ 行被丢弃 (:74-75)"]
        S --> T["newpkgs 列表 → §5 差集"]
    end

    style I fill:#ff9
    style S fill:#f9f
```

**设计要点**：`.config` 是唯一事实源，但派生两条独立消费链——`rtconfig.h`（编译层，走 C 头）与 `newpkgs`（包层，走字符串解析）。两链各自容错（`mk_rtconfig` 过滤 `PKG_*_PATH/_VER`，:160-162）。

### 4.2 `mk_rtconfig()` 转换规则速查

| `.config` | `rtconfig.h` |
|---|---|
| `CONFIG_FOO=y` | `#define FOO 1` |
| `CONFIG_FOO=123` | `#define FOO 123` |
| `# CONFIG_FOO is not set` | `/* FOO is not set */` |
| `CONFIG_PKG_X_PATH/_VER` | （跳过） |
| 目录有 `rtconfig_project.h` | 追加 `#include` |

---

## 5. pkgs 安装流水线（cmd_package_update.py:1200-1288）

### 5.1 差集决策

```mermaid
flowchart TD
    A["kconfig.parse('.config')<br/>→ newpkgs [{name,path,ver}]"] --> C["读 <bsp>/packages/pkgs.json<br/>→ oldpkgs（上次状态）"]
    C --> D{"old − new"}
    D -->|有| E["remove_packages()<br/>git 包整目录删 (:1101-1134)<br/>归档包逐文件 md5 确认 (pkgsdb)"]
    D -->|无| F{"new − old"}
    F -->|有| G["install_packages()"]
    F -->|同包异版本| H["删 <name>-<oldver> 再装 <name>-<newver><br/>（无版本解析器）"]
    G & H --> I["ver==latest 的 git 包<br/>→ update_latest_packages() git pull (:787-839)"]
    I --> J["失败包 → download_fail_list<br/>写回 pkgs.json → 提示重跑"]

    style H fill:#ff9
```

### 5.2 安装双轨（`install_package()`，:614-710）

```mermaid
flowchart TD
    A["package.json site[] 按 ver 匹配<br/>（大小写不敏感，package.py:144-153）"] --> B{"镜像决策<br/>need_using_mirror_download (:430-476)"}
    B -->|命中| C["POST api.rt-thread.org/packages/queries<br/>{userName:RT-Thread, packages:[{name}]}<br/>→ 镜像 site 列表 (cmd_package_utils.py:203-256)"]
    B -->|未命中| D["用原始 URL"]
    C & D --> E{"URL 以 .git 结尾?"}
    E -->|是·git 包| F["install_git_package (:518-574)"]
    E -->|否·归档包| G["install_not_git_package (:577-602)"]

    subgraph F2["git 轨"]
        F --> F1{"目标目录<br/>已存在?"}
        F1 -->|是| F2["⚠️ 直接 return True<br/>幂等跳过不更新 (:534-536)"]
        F1 -->|否| F3["git clone（全量无 depth）"]
        F3 --> F4["set-branches origin <ver_sha><br/>fetch --depth 1 origin <ver_sha><br/>checkout -q <ver_sha>"]
        F4 --> F5["镜像换过 URL → set-url 恢复 origin (:562-566)"]
        F5 --> F6[".gitmodules → 子模块 init"]
    end

    subgraph G2["归档轨"]
        G --> G1["下载 ~/.env/local_pkgs/<filename><br/>重试 5 次 (package.py:217-230)"]
        G1 --> G2["package_integrity_test：<br/>仅 zip/tar 结构校验，无哈希 (archive.py:181-208)"]
        G2 --> G3["解压 package_temp → 顶层改名 <name>-<ver>"]
        G3 --> G4["每个文件 md5 → sqlite<br/>(packages.dbsqlite)"]
    end

    F2 & F6 & G4 --> H2["<bsp>/packages/<name>-<ver>"]

    style F2 fill:#ff9
    style G2 fill:#f99
```

### 5.3 SConscript 桥接与 hal-sdk 双位安装

```
<bsp>/packages/
├── SConscript            ← env 生成（若不存在，package.py:39-51）
│     for item in os.listdir(cwd):
│         if exists(item/SConscript): SConscript(item/SConscript)
│     ⇒ "目录约定"式桥接：包必须自带 SConscript
├── hello-v1.0.0/         ← 普通包：源码直接在此
│   └── SConscript
└── STM32F1-HAL-latest/   ← hal-sdk 包（BSP 有 libraries/ 时）
    └── SConscript        ← 仅桥接脚本，运行时去 libraries/ 找真身
                            (HAL_SDK_BRIDGE_SCONSCRIPT, :62-133)

<bsp>/libraries/STM32F1-HAL-latest/   ← hal-sdk 真实源码
                                      卸载只删桥接、保留源码 (:1155-1163)
```

---

## 6. SDK 与工具链管理

### 6.1 SdkManager plan/apply 两阶段原子应用（sdk_manager.py:940-1088）★

```mermaid
flowchart TD
    subgraph PLAN["阶段① plan(selection) :331-381"]
        A["期望选择（每个 SDK 的版本）"] --> B["对比 _config_snapshot()"]
        B --> C["操作列表：install / switch /<br/>remove / disable / enable"]
        C --> D["⚠️ 必须覆盖索引内全部包 (:304-309)<br/>不支持单包局部更新"]
    end

    subgraph APPLY["阶段② start_apply → _execute（后台线程）"]
        E["① 逐操作：下载（stream,60s）<br/>→ 成员名校验（仅 ../ 与绝对路径）<br/>→ 解压 .sdk-staging<br/>→ 单顶层目录展平为 <name>-<ver>.ready"]
        E --> F["② _render_config() 渲染新 .config<br/>kconfiglib + 旧 kconfig.py 双重验证 (:705-756)"]
        F --> G["③ 原子替换：旧目录 → 备份位<br/>staging → packages/<name>-<ver> (:1033-1045)"]
        G --> H["④ 写状态：pkgs.json /<br/>pkgs_error.json(恒[]) / sdk_list.json"]
        H --> I["⑤ 异常回滚：删已就位、<br/>恢复备份、恢复 .config (:1064-1086)"]
    end

    D --> APPLY
    style D fill:#ff9
    style I fill:#9f9
```

### 6.2 构建侧工具链发现链（rt-thread building.py:246-272）

```mermaid
sequenceDiagram
    participant B as building.py
    participant EU as env_utility
    participant F1 as ~/.env/tools/scripts

    B->>B: 先 del RTT_EXEC_PATH（防旧值）(:250-252)
    B->>B: rtconfig.EXEC_PATH 下 CC 不存在?
    B->>EU: GetSDKPath(rtconfig.CC)
    EU->>F1: ① 读 sdk_cfg.json（用户手工登记优先）
    EU->>F1: ② 读 packages/pkgs.json<br/>逐项开索引 package.json 比对 name
    EU-->>B: packages/<name>-<ver>
    B->>B: gcc 系补 /bin → 校验存在
    B->>B: rtconfig.EXEC_PATH = 路径<br/>os.environ['RTT_EXEC_PATH'] = 路径
```

**选择链本质**：`.config`（Kconfig）→ `pkgs.json` → `GetSDKPath` → `RTT_EXEC_PATH`——配置文件是唯一事实源，`sdk_cfg.json` 是用户覆盖通道（ToolchainManager 维护，Windows 下自动扫注册表发现 Keil/IAR，toolchain_manager.py:173-251）。

### 6.3 SDK 索引与安装布局

```
~/.env/
├── packages/sdk/Linux/                  ← 索引（git 仓，按 hostos 分）
│   ├── arm-none-eabi-gcc/
│   │   ├── package.json  {name, site:[{version,URL,filename,size}]}  ⚠️无 sha
│   │   └── Kconfig       PKG_USING_* + 版本 choice
│   └── riscv-none-elf-gcc/ ...
└── tools/scripts/
    ├── .config                          ← SDK 选择落点
    └── packages/
        ├── arm-none-eabi-gcc-v10.3/     ← 实际安装（= 工具链本体）
        ├── pkgs.json                    ← {name(大写), path(索引路径), ver}
        └── .sdk-staging/                ← 原子应用暂存区
```

⚠️ 两个反直觉：SDK 装在 **env 源码仓内**；tarball 下载**无镜像无校验**（Gitee 只加速索引克隆，`sdk_manager.py:764` 直连上游 URL）。

---

## 7. 插件系统与 WebUI

### 7.1 `.epack` 包结构与 CLI 扩展链

```mermaid
flowchart LR
    subgraph EPACK[".epack v1 (ZIP)"]
        M["manifest.json<br/>id 反域名/semver/compatibility/<br/>permissions 枚举/commands 正则<br/>(manifest.py:254-359 严格校验)"]
        I["integrity.json<br/>SHA-256 清单 (:69-92)<br/>⚠️ v1 无签名 (:160-163)"]
        W["backend/*.whl"]
        FE["frontend/ 静态资源"]
    end

    EPACK -->|"安装（--yes 或 TTY 确认）"| INST["${ENV_ROOT}/var/plugins/<br/>installed/&lt;id&gt;/&lt;version&gt;/"]

    subgraph DISP["命令扩展（dispatcher 解耦）"]
        L["launcher 脚本"] --> D["python -m plugins.dispatcher &lt;cmd&gt;<br/>(launchers.py:111-148)"]
        D --> S["state-v1.json commands 映射<br/>→ 插件 ID (:46-53)"]
        S --> P["wheel 的 site-packages<br/>插入 sys.path (:70-80)"]
        P --> X["entry = 'module:callable'<br/>独立进程执行 (:78-91)"]
    end

    MKT["市场 /api/v1<br/>ENV_PLUGIN_MARKET_URL ><br/>var/plugins/market.json (market.py:68-82)<br/>health/plugins/resolve/artifacts"] -.->|"下载 .epack"| EPACK
```

**关键设计**：插件代码永不进入 env 主进程——launcher→dispatcher→独立 wheel 进程。

### 7.2 WebUI BFF 架构与安全模型（plugins/webui/server.py）

```mermaid
flowchart TB
    subgraph SRV["ThreadingHTTPServer（纯标准库 :502-510）"]
        B["默认 127.0.0.1:0 随机端口<br/>-g 才 0.0.0.0 (cmd_webui.py:576-589)"]
        LT["_launch/&lt;一次性token&gt; → HttpOnly+SameSite=Strict Cookie (:627-648)"]
        CSRF["写请求：X-Env-CSRF 头 + Origin==Host + Sec-Fetch-Site (:1093-1107)"]
        API["/api/v1/*：session / plugins(装/卸/启停/doctor) /<br/>market / workspace(build/clean) / sdk(plan/apply) /<br/>settings(toolchains/network/右键菜单) (:667-815)"]
        PROXY["插件后端代理：仅随机回环端口<br/>/plugins/&lt;id&gt;/backend/ (:850-933)"]
    end

    subgraph FE["浏览器"]
        BR["env 前端页面"]
        IF["插件前端：sandbox iframe<br/>无 allow-same-origin"]
    end

    BR --> SRV
    IF --> PROXY
```

---

## 8. 构建与导出数据流（rt-thread 侧）

### 8.1 统一中间表示（所有导出器的地基）

```mermaid
flowchart LR
    subgraph IN["输入"]
        RT["rtconfig.h<br/>(BuildOptions)"]
        SC["组件 SConscript<br/>DefineGroup(name, src, CPPPATH, ...)"]
    end
    subgraph MID["中间表示 building.py"]
        PR["Projects = [group dict]<br/>(name/path/src/CPPPATH/...)<br/>同名 MergeGroup (:592-673)<br/>字母序 PriorityInsert (:791)"]
        EN["Env = 全局聚合 flags"]
    end
    subgraph OUT["导出器（三范式）"]
        T1["模板填充：mdk5/iar/vs/cdk/ses<br/>BSP 内 template.* (:204-223)"]
        T2["程序化：vsc/cmake/makefile<br/>(vsc.py:234-274)"]
        T3["原地更新+哨兵：eclipse<br/>(eclipse.py:236,279-283)"]
    end
    RT -->|"GetDepend 门控 (:511-527)"| SC
    SC --> PR
    PR --> OUT
    EN --> OUT
```

**分工原则**：器件/Flash 算法/调试器等**不可推导**的板级硬信息固定在 BSP 模板；**可推导**的（分组/源文件/头路径/宏）从 Projects/Env 动态注入。

### 8.2 ebuild 与 building.py 的关系（env 仓内的下一代重写）

```mermaid
flowchart LR
    subgraph OLD["rt-thread tools/building.py（现行）"]
        O1["全局变量 Env/Projects/BuildOptions"]
        O2["过程式，Change Log 至 2025-03-02"]
    end
    subgraph NEW["env/ebuild/（重写，2025-12-27）"]
        N1["BuildSystem 类 + Group dataclass<br/>+ 类型注解 (system.py:26-404)"]
        N2["configs/ 工具链数据模块 ×7"]
        N3["exporter: 仅 vscode/cmake/mdk"]
    end
    OLD -->|"AST diff：5 个关键函数<br/>零共享代码体（完全重写）"| NEW
    OLD -->|"targets/keil.py 直接 fork<br/>（函数体基本一致）"| N4["ebuild/targets/keil.py<br/>+ KeilProjectGenerator 包装"]
    NEW -.->|"⚠️ 全仓零 import、不打包<br/>（pyproject 不含 ebuild）<br/>经 env-windows 子模块随源码分发"| USER["用户项目 SConstruct<br/>from ebuild import ..."]
```

---

## 9. env-windows 引导链（免装机制现场）

### 9.1 启动时序

```mermaid
sequenceDiagram
    participant U as 用户双击
    participant EB as env.bat
    participant CE as ConEmu64
    participant CI as CmdInit.cmd
    participant EI as env-init.bat
    participant V as .venv

    U->>EB: 双击
    EB->>EB: %processor_architecture% 判架构 (:3-10)
    EB->>CE: start ConEmu64.exe
    CE->>CE: 任务 {rtt-env} (ConEmu.xml:602-612)
    CE->>CI: cmd.exe /k CmdInit.cmd
    CI->>EI: env-init.bat
    EI->>EI: ENV_ROOT 已设置? → 跳过 (:3)
    EI->>EI: 写 %USERPROFILE%\.conemu\CmdInit.cmd 样本<br/>（★唯一持久化动作 :9-27）
    EI->>EI: ENV_ROOT/RTT_EXEC_PATH/RTT_CC/PKGS_ROOT (:31-36)
    EI->>EI: :AddPath ×5（git/tools\bin/dtc/gcc/qemu）(:39-46)
    EI->>EI: chcp 65001（中文横幅）→ chcp 437 (:50,:97)
    EI->>EI: 空格/中文字符路径检测（cscript JScript）(:58-85)
    alt 首次
        EI->>V: pip uninstall pip → ensurepip → venv → activate<br/>→ pip install tools\scripts（本地子模块，离线可装）(:100-117)
    else 之后
        EI->>V: 仅 activate
    end
    EI->>EI: 非 ConEmu 时 clink inject (:142-145)
```

### 9.2 `:AddPath` 去重置顶算法（env-init.bat:123-140）

```
输入 new_path
  ├─ for %%A → %%~fA          相对路径转绝对
  ├─ echo %PATH% | findstr /i /c:"%new_path%;"
  │     未命中 → PATH = new_path;PATH           （前置）
  │     命中   → PATH = new_path;!PATH:new_path;=!（删旧项再前置 ★去重+置顶）
  └─ endlocal & set "PATH=%PATH%"   局部变量回写父进程
```

---

## 10. 设计评价一图流

```mermaid
quadrantChart
    title env 设计决策定位（主观评估）
    x-axis 实现朴素 --> 实现精巧
    y-axis 局部取舍 --> 架构价值
    源指纹venv自举: [0.80, 0.90]
    SDK plan apply原子应用: [0.85, 0.80]
    config单一事实源: [0.60, 0.85]
    目录即安装约定: [0.40, 0.70]
    插件dispatcher解耦: [0.75, 0.65]
    WebUI纯标准库BFF: [0.70, 0.60]
    镜像双层策略: [0.55, 0.50]
    lines+3文本扫描: [0.10, 0.10]
    pkgs差集无lockfile: [0.25, 0.30]
    statistics exit 0: [0.05, 0.05]
```

### 亮点

1. **源指纹自举**（§3）：SHA-256(路径+内容) 驱动 venv 状态机，"git pull 即升级"零配置实现，created/repaired/upgraded/current 四态清晰。
2. **SDK 两阶段原子应用**（§6.1）：staging + 备份 + 回滚 + 双重配置验证，env 仓工程质量之最。
3. **`.config` 单一事实源**（§4.1）：人机层/编译层/包层三条消费链从一个文件派生，互不干扰。
4. **Windows 免装四件套**（§9）：便携 Python + venv + 会话级 PATH + 本地 pip 安装，编码/路径防御细节多年踩坑沉淀。
5. **插件进程隔离**（§7.1）：wheel 独立进程 + sandbox iframe + 回环代理，CLI 工具长出 GUI 与插件生态的最低成本路径。

### 不足与 quirks（节选，全表见文字版 §八）

| # | 问题 | 引证 |
|---|---|---|
| 1 | BSP 根=cwd，无 workspace 发现机制 | env.py:209-210 |
| 2 | RTT 根靠 `lines[i+3]` 硬编码偏移，两处重复实现 | env.py:171, cmd_menuconfig.py:65 |
| 3 | pkgs 无 lockfile/依赖解析/多版本共存 | §5.1 |
| 4 | 全链路无哈希校验（包结构校验、SDK 无 sha） | archive.py:181-208, sdk_manager.py:761-855 |
| 5 | statistics 异常 `exit(0)` 杀进程；上报 MAC 默认开启 | statistics.py:62-67 |
| 6 | pkgsdb 路径双重拼接 bug | pkgsdb.py:212-213 |
| 7 | sdk CLI 与 SdkManager 双轨并存不互通 | cmd_sdk.py |
| 8 | ebuild 与 building.py 双轨不收敛，未打包 | §8.2 |
| 9 | env.exe 3.6MB 零引用；touch_env.py 0 字节 | §2 |
| 10 | 插件 v1 无签名，TTY 下未签名自动放行 | cmd_plugin.py:60-63 |

---

## 11. 一页速查（TL;DR）

```
env = venv 自举的 RT-Thread 开发环境工具 + ~/.env 三仓数据目录 + SCons 构建编排约定

  ~/.env/tools/scripts (env 仓 clone)
      │ 源指纹 SHA-256（env_venv.py:113-131）
      ▼
  ~/.env/.venv ← pip install 本地源码（离线可装，git pull 即升级）

  命令面 6 个（pyproject console-scripts）：
      menuconfig → .config ─┬→ rtconfig.h → building.py GetDepend（编译门控）
                            └→ kconfig.py  → pkgs 差集（包生命周期）
      pkgs   → .config 与 pkgs.json 差集 → git(clone/fetch sha/checkout)/归档(无哈希)双轨
               → <bsp>/packages/<name>-<ver> + 桥接 SConscript（hal-sdk → libraries/）
      sdk    → Kconfig 选择 → SdkManager plan/apply（staging+备份+回滚）
               → tools/scripts/packages/<name>-<ver> → GetSDKPath → RTT_EXEC_PATH
      plugin/webui → .epack(ZIP+manifest+sha256清单，无签名) → dispatcher 独立进程
               → WebUI 纯标准库 BFF（localhost+一次性 token+CSRF）

  骨架 ~7800 行：sdk_manager(1134) > cmd_package_update(1288) > env_venv(521)
  两把钥匙：env_venv 的指纹状态机 + cmd_package_update 的差集双轨安装
  最大短板：无 workspace 发现、无 lockfile、无哈希校验、双轨并存
```

---

*本文所有行号基于 env v2.0.2（ec2c251）/ env-windows v2.1.0（fc857c5a）/ rt-thread v5.3.0；文字论证与实操验证见同目录《Env实现机制深度分析.md》。*
