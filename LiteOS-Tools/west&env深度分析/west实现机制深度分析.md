# west 实现机制深度分析

> 调研日期：2026-10-08 ｜ 代码基线：west **v1.4.0**（`zephyrproject-rtos/west`，commit `746e1b19`）+ Zephyr **v4.4.2**（commit `dccb0959`）
> 源码位置：`~/workspace/repo/west`、`~/workspace/repo/zephyr`
> 证据约定：`文件:行号` 相对上述仓库根；✅ 源码证实 ｜ ⚠️ 源码与文档不一致 ｜ ❓ 未核实
> 本文档为《west与Env深度调研计划》W1–W9 问题的回答，实操验证见文末。

---

## 一、总体架构（W1）："通用壳 + 领域扩展"的两段式

### 1.1 关键事实：west 本体是独立 pip 包，且**不含任何构建逻辑**

- west 源码在**独立仓** `zephyrproject-rtos/west`（不在 zephyr 主仓）；zephyr 经 `scripts/requirements-west.txt` 锁定 `west==1.4.0`。
- west 的内建命令只有两类（`west/src/west/app/main.py:1204-1225` `BUILTIN_COMMAND_GROUPS`）：
  1. **多仓管理**：`init / update / list / manifest / compare / diff / status / forall / grep / topdir`
  2. **工具自身**：`help / config` + 隐藏的 `selfupdate`
- 全包 grep "build/flash" 仅命中一处 config 注释示例——**`west build/flash/debug/boards/sign/sdk` 全部是 zephyr 主仓经扩展机制注入的"领域命令"**。这是对调研计划预判 #1 的最强证实。

### 1.2 模块地图（`west/src/west/`）

| 模块                    | 职责                                                            |
| --------------------- | ------------------------------------------------------------- |
| `util.py`             | `.west` 目录发现（`west_topdir` 向上遍历）、路径穿越检查 `escapes_directory()` |
| `configuration.py`    | 三层配置（见 §五），configparser INI 实现                                |
| `manifest.py`（2784 行） | west.yml 解析/校验/import 递归解析、`Project`/`ManifestProject`        |
| `commands.py`         | `WestCommand` 基类 + **扩展命令发现/加载**（见 §三）                        |
| `app/main.py`         | CLI 应用 `WestApp`：入口分发、内建注册、帮助系统                               |
| `app/project.py`      | `Init`/`Update` 等多仓命令的 git 操作实现                               |

### 1.3 启动分发流程（`app/main.py`）

```
west 命令 → main()(:1196) → WestApp() 实例化内建命令(:218)
  → run()(:235)：parse_early_args → west_topdir() 发现 workspace
  → Configuration(topdir) → Manifest.from_topdir()（失败延迟处理）
  → load_extension_specs()(:388) → setup_parsers()(:457)
  → run_command()(:534)：命令名在内建表→run_builtin；否则→run_extension
```

### 1.4 WestCommand 基类契约（`commands.py:122`）

所有命令（内建+扩展）统一继承，**必须实现两个抽象方法**：
- `do_add_parser(parser_adder)`：注册子命令参数
- `do_run(args, unknown)`：命令逻辑

`run(args, unknown, topdir, manifest, config)` 由框架调用并注入运行上下文；提供 `dbg/inf/wrn/err/die` 日志、`check_call/check_output` 子进程封装、`requires_workspace`（无 workspace 是否报错）、`accepts_unknown_args`（是否接收透传参数）等能力。**扩展命令类必须零参构造**（`commands.py:549-582` `_ExtFactory`）。

---

## 二、manifest 多仓管理（W2）

### 2.1 schema 与解析顺序

- `west.yml` 结构：`manifest: { defaults, remotes, projects, self, group-filter }`，pykwalify 校验（`manifest-schema.yml`）。
- **解析顺序**（`manifest.py:1992-1999`）：`self: import` → 本 manifest `projects:` → 各 project 的 `import:`（递归）。
- **import 四种形态**：str（路径）/ list / bool（报错）/ **import map**（`name_allowlist / path_allowlist / name_blocklist / path_blocklist / path_prefix`）——支持"导入子集 + 路径前缀"，是**最小源码集减重的机制基础**。
- **project import 从 git 读**（`manifest.py:2610` `_import_content_from_project`）：按 `manifest-rev` 分支用 `git ls-tree`/`git show` 直接读子 manifest，无需先 checkout。

### 2.2 revision 语义：manifest-rev 而非直接 checkout

`west update` **不把项目 checkout 到 revision 本身**，而是：fetch revision → 解析为 SHA → 写入项目本地 `refs/heads/manifest-rev` → detached checkout 该 SHA（`app/project.py:1044-1046, 1662-1663, 1436`）。好处：用户分支不被覆盖，`manifest-rev` 始终是"上游锁定的版本"。

### 2.3 west update 的动态重解析

带 import 的 manifest 中，新 revision 可能引入新项目。`update_all()` 用**自定义 importer 重新解析 manifest**（`ImportFlag.FORCE_PROJECTS`），边更新边解析（`app/project.py:1178-1244`）。限制：`west update <project>` 拒绝 imported 项目（`:1246-1309`），只能整体 `west update`。

### 2.4 workspace 发现

`west_topdir()` 从 cwd **逐级向上**找含 `.west/` 的目录（`util.py:65-86`）；`.west/config` 记录 `manifest.path/file`。找不到时回退用 `ZEPHYR_BASE` 再搜一次（⚠️ west 核心内嵌了 Zephyr 特化逻辑，见 §三）。

---

## 三、扩展命令机制（W3）★ LiteOS 最重要借鉴点

### 3.1 声明与发现链

```
west.yml 项目字段 west-commands: <yml路径>        ← 声明（project 级 + self 级均可用）
  → west 启动时 extension_commands() 遍历 manifest.projects（commands.py:604）
  → _ext_specs()：pykwalify 校验 + 路径穿越防护 + 未克隆项目静默跳过（:633-670）
  → WestExtCommandSpec(name, project, help, factory)（:672-692）
  → 注册进 WestApp.extensions / extension_groups（app/main.py:388-429）
```

`west-commands.yml` schema（极简，`west-commands-schema.yml`）：

```yaml
west-commands:
  - file: scripts/west_commands/build.py     # Python 文件（相对项目根）
    commands:
      - name: build
        class: Build                          # 缺省时 = name
        help: compile a Zephyr application
```

### 3.2 四个关键设计

1. **惰性加载**：启动时只为扩展注册"占位 parser"（`add_parser(name, add_help=False)`，`main.py:474-478`），**不 import 任何扩展代码**；真正执行 `run_extension()`（`:700-740`）时才经 `_ExtFactory` 用 `importlib.util.spec_from_file_location` 导入模块、实例化类、重建 parser、二次解析 argv。→ `west -h` 极快，扩展坏了不影响其他命令。
2. **名称优先级**：内建命令名 > 扩展名；同名扩展**先到先得**（manifest 项目顺序），冲突只告警不报错（`main.py:409-427`）。
3. **帮助集成**：`west help <ext>` 通过 `run_extension(name, [name,'--help'])` 触发真实加载打印帮助；顶层帮助列出各项目扩展组及 YAML 里的 `help` 文本。
4. **安全防护**：yml 文件与 py 文件都做 `escapes_directory()` 路径穿越检查（`commands.py:644,678`）。

### 3.3 zephyr 的 22 个扩展命令（`zephyr/scripts/west-commands.yml`）

`build / boards / shields / flash / debug / debugserver / attach / rtt / reset / sign / twister / sdk / spdx / blobs / bindesc / robot / simulate / zephyr-export / packages / patch / gtags / completion`——**Zephyr 把自己变成 west 的一个"插件包"**，west 对 build 一无所知。

### 3.4 外部模块的扩展路径（不经 west-commands.yml）

west module 的 `module.yml` 可声明 `runners:`，由 `run_common.py:240-248` 用 `import_from_path` 动态加载——**第三方（如 Nordic）不改 Zephyr 树即可注入 runner**。LiteOS 的厂商/开发板仓可用同样模式。

### 3.5 值得注意的瑕疵

- **west 核心内嵌 ZEPHYR_BASE 特化**：`set_zephyr_base()`（`main.py:742-859`）在扩展运行前自动推断/设置 `ZEPHYR_BASE`（含 `zephyr.base-prefer` 配置）。LiteOS 仿制时应把这类"默认 manifest 项目定位"做成通用机制而非硬编码。
- **模块缓存 bug**：`_commands_module_from_file()` 读缓存用 `Path` 键、写用 `str` 键（`commands.py:712` vs `:719`），永不命中——无害但缓存失效，同一扩展文件可能被重复 exec。LiteOS 实现时修正即可。

---

## 四、west build 封装（W4）

### 4.1 "壳不碰构建逻辑"的三件事

`scripts/west_commands/build.py`（zephyr 侧）只做：
1. **解析/规范化 CLI**：`-b/--board`、`-d/--build-dir`、`--shield`、`--snippet`、`--extra-conf`、`-t/--target`、`-p/--pristine`、`--sysbuild`、`--domain` 等（`build.py:100-189`）；
2. **参数→子进程命令行映射**（`_run_cmake()`，`build.py:629-686`）：

| west 参数 | CMake 参数 |
|---|---|
| `-b BOARD` | `-DBOARD=` |
| `--shield a b` | `-DSHIELD=a;b` |
| `--extra-conf f` | `-DEXTRA_CONF_FILE=` |
| `--snippet s` | `-DSNIPPET=a;b` |
| （恒定） | `-DWEST_PYTHON=<python> -B<builddir> -GNinja -S<src>` |

3. **构建目录/增量判定**：`find_build_dir()` + `build.dir-fmt` 占位符（`{west_topdir}{source_dir}{app}{board}`，`build_helpers.py:41-114`）；`is_zephyr_build()` 用 CMakeCache 哨兵键（`ZEPHYR_BASE`/`ZEPHYR_TOOLCHAIN_VARIANT`）判断目录性质；pristine 三态（`auto/always/never`，app/board 变更触发 auto pristine，执行 `cmake -P pristine.cmake` 清目录）。

**目标透传**：`west build -t menuconfig` → `cmake --build <dir> --target menuconfig`（`zcmake.py:80-112`）——menuconfig target 由 CMake 侧 kconfig.cmake:223-242 定义，**west 完全不理解 target 语义**。compile_commands.json 同理由 CMake 强制开启（`kernel.cmake:124-127`），非 west 职责。

### 4.2 sysbuild 多镜像

`west build --sysbuild` 只是把 `-S` 换成 `share/sysbuild` 并把 app 路径放进 `APP_DIR` 环境变量（`build.py:666-673`）；镜像编排全部在 CMake 层（ExternalProject + `sysbuild_cache` 变量传递）。产物 `domains.yaml`（`domains.cmake:19`）是**与 CMake 解耦的通用多镜像抽象**：`default/build_dir/domains/flash_order`，west 侧 `Domains` 类（`pylib/build_helpers/domains.py:60-126`）解析，`--domain` 选择构建对象。**LiteOS 多目标（L0/L1、多核）可直接借用该 yaml 模型**。

### 4.3 boards 发现（HWMv2）

- `west boards`（`boards.py`）→ `list_boards.find_v2_boards()`：对每个 board root 只 `rglob('board.yml')`（`list_boards.py:244`），JSON Schema 校验（`board-schema.yaml`），构建 `Board` dataclass（name/vendor/revisions/socs/variants，qualifier 按 soc→cpucluster→variant 链生成）。
- `-n` 正则过滤、`-f` Python format 自定义输出（`boards.py:63,114-125`）。
- **同一脚本被 CMake 复用**（`boards.cmake:152-160` 调 `list_boards.py --cmakeformat`，`ninja boards` 可用）——源码注释明确 "keep west optional"（`list_boards.py:34-41`）。**发现逻辑与构建系统解耦、单一实现两端复用**，是 LiteOS 板卡发现的直接模板。

### 4.4 CMake 侧唯一集成点 west.cmake

`cmake/modules/west.cmake`（97 行）：校验 west 版本 ≥0.14.0、Python 一致性、`WEST_TOPDIR` 探测。**不参与命令注册**——双向探测而非依赖。

---

## 五、west config 三层配置（W7）

- 三层与位置（`configuration.py:559-629`）：SYSTEM（`/etc/westconfig`）→ GLOBAL（`~/.config/west/config` 或 `~/.westconfig`）→ LOCAL（`<topdir>/.west/config`）；环境变量 `WEST_CONFIG_SYSTEM/GLOBAL/LOCAL` 可覆盖。
- **实现是 configparser INI**，不是 git 二进制格式——"git config 风格"仅是约定（`section.key` 寻址、local>global>system 优先级、写默认 LOCAL）。
- `west config` 命令 `requires_workspace=False`——manifest 坏了也能修配置。

---

## 六、runner 烧录/调试抽象（W5）★ LiteOS CLI 烧录直接对标

### 6.1 核心契约（`runners/core.py`）

- `ZephyrBinaryRunner(abc.ABC)`（`:430`），子类必须实现 4 钩子：`name()` / `do_add_parser()` / `do_create()` / `do_run()`；可选覆盖 `capabilities()`。
- **注册机制**：无装饰器、无注册表 dict——`get_runners()` 用 `__subclasses__()` 递归发现（`:529-544`），配 `runners/__init__.py:24-82` 的显式 import 清单（49 模块 → 50 个具体 runner）。外部模块经 module.yml 注入（§3.4）。
- **RunnerCaps 能力声明**（`:264-362`）：`commands` 合法集合 = `{flash, debug, debugserver, attach, simulate, robot, rtt, reset}` + `dev_id / flash_addr / erase / reset / file / tool_opt / rtt / dry_run / skip_load` 等开关。**公共参数按能力动态增删**（`add_parser()`，`:564-695`；不支持的能力仍注册选项但 SUPPRESS，防止子类挪用）。
- **RunnerConfig**（NamedTuple，`:381-401`）：`build_dir / board_dir / elf·hex·bin·uf2·mot 文件 / gdb / openocd / openocd_search`——值来自"命令行 > runners.yaml"（`run_common.py:655-730`）。

### 6.2 runner 解析优先级（精确链）

```
west flash [-r R]
  → runner = args.runner 或 runners.yaml['flash-runner'/'debug-runner']   ← ①命令行 ②构建产物
  → 必须在 runners.yaml['runners'] 白名单内（board.cmake 构建期写入）      ← ③板级声明
  → get_runner_cls() 全局类表 → capabilities().commands 校验               ← ④能力校验
```
（`run_common.py:624-653` `use_runner_cls()`；runner_key：flash.py:25、debug.py:27 等）

### 6.3 runners.yaml：构建期生成、运行期消费

- **生成**：CMake configure 阶段，板级 `board.cmake` 调 `board_finalize_runner_args()` 把 runner 与默认参数写入全局属性（`extensions.cmake:876-901`），`cmake/flash/CMakeLists.txt:87-139` `create_runners_yaml()` 拼装后 `file(GENERATE)` 写出至 **`<build>/zephyr/runners.yaml`**。
- **格式**：`runners`（白名单）/ `flash-runner` / `debug-runner` / `config`（board_dir、各格式产物路径、gdb、openocd）/ `args`（每 runner 默认参数）。
- **意义**："烧录配置是构建产物的一部分"——板级默认在构建时已定格，CLI 只需覆盖。LiteOS 应同样在构建期产出一份 `runners.yaml` 等价物。

### 6.4 后端清单（50 个，节选关键项）

| 类别 | runner |
|---|---|
| **通用探针** | `openocd`、`pyocd`、`jlink`、`probe-rs`、`blackmagicprobe`、`stlink_gdbserver`、`linkserver` |
| **原厂工具** | `nrfjprog`/`nrfutil`、`stm32cubeprogrammer`、`stm32flash`、`dediprog`、`sftool`、`silabs_commander`、`rfp`、`trace32`、`mdb-*`、`xtensa`、`xsdb` |
| **USB/串口** | `dfu-util`、`bossac`、`teensy`、`wchisp`、`ezflashcli`、`minichlink`、`esp32` |
| **仿真** | `native`、`qemu`（stub）、`renode`、`renode-robot` |

**openocd 后端深挖**（`runners/openocd.py`）：cfg 文件三级搜索（`--openocd-search` > runners.yaml `openocd_search` > board_dir 支持）→ 组装 `openocd -f interface.cfg -f target.cfg -c "adapter speed ..." [-c "program ..."]` → flash 地址取 `--flash-address`（BIN 需显式地址）。**RTOS 感知**：`CONFIG_DEBUG_THREAD_INFO` 开启时注入 `$_TARGETNAME configure -rtos Zephyr`（`:409`）；jlink 用 `-rtos RTOSPlugin_Zephyr`；pyocd 内建 Zephyr 感知。

### 6.5 dry-run 的真相（⚠️ 重要发现）

`--dry-run` 是 **per-runner 能力**（`RunnerCaps.dry_run`），v4.4.2 中**仅 `nrfutil` 等极少数后端声明**——`west flash --dry-run` 对 openocd/pyocd/jlink **会直接报错**！通用 dry-run 基础设施其实存在（`core.py:45 _DRY_RUN` 全局 + `_log_cmd/call/check_call` 封装 `:913-976`），只是未对所有 runner 开放。**LiteOS 设计应把 dry-run 做成全局能力**（所有后端统一支持，打印将执行的完整命令行），这是 Zephyr 的明显短板，容易超越。

### 6.6 west debug 流程

`run_server_and_client()` 模式（`core.py:885-903`）：起 GDB server（openocd/pyocd/JLinkGDBServer）→ `gdb -ex 'target extended-remote :PORT' [-ex load]` → 退出时杀 server。`--gdb`/`--gdb-port` 可覆盖。

### 6.7 west sign（imgtool）

v4.4.2 中 imgtool 是 `sign.py` 内的 `ImgtoolSigner`（`sign.py:256-439`，**不是 runner**）：从 Kconfig/DT 取 slot 大小/对齐/偏移，调 imgtool 生成 `zephyr.signed.bin/hex`；MCUboot 场景下 `mcuboot.cmake:13-18` 在**构建期自动签名**并让 runners.yaml 指向签名产物（`zephyr_runner_file()` 属性魔法）。

### 6.8 新增后端 recipe（LiteOS 直接套用）

1. 新建 `runners/xxx.py`，继承 `ZephyrBinaryRunner`，实现 4 钩子（用 `self.check_call(cmd)` 执行——自动享受日志/dry-run 封装）；
2. 在 `runners/__init__.py` 的 `_names` 清单加一行；
3. 板级 `board.cmake` 写 `board_runner_args(xxx ...)`。
**最小真实后端参考**：`ecpprog.py` 仅 ~41 行（含 capabilities 与参数解析）；`hifive1.py` ~47 行含 debug 支持；最大 `openocd.py` ~600 行。预判 #2（<300 行/后端）✅ 证实。

---

## 七、west sdk 工具链分发（W6）

### 7.1 命令面：只有 `list` 和 `install`

无 validate/uninstall/update（`sdk.py:60-203`，⚠️ 与部分文档描述不符）。

### 7.2 `west sdk install` 数据流（`sdk.py:461-553`）

```
版本决议：--version > $ZEPHYR_BASE/SDK_VERSION 文件（最低 0.14.1）
  → GitHub API（sdk-ng releases，--api-url 可指自建镜像 ← LiteOS 内网分发可借鉴）
  → 匹配 minimal 资产：zephyr-sdk-<ver>_<os>-<arch>_minimal.{7z|tar.xz}
  → 下载（tqdm 进度）+ sha256.sum 校验（hashlib）
  → patoolib 解压 → 移动到 $HOME/zephyr-sdk-<ver>（--install-base/--install-dir 可改）
  → 运行 SDK 自带 setup.cmd/sh：
       -c   注册 CMake 包（user package registry）
       -t all | -t <tc>...  选装 GNU 工具链（minimal 包按需下载）
       -l LLVM  -h hosttools
```

### 7.3 SDK 布局与构建发现

- 布局：`gnu/<toolchain>/bin/<tc>-gcc`（≥1.0.0）、`llvm/`、`hosttools/`、`sdk_version`、`sdk_gnu_toolchains`（可用清单）、`cmake/zephyr/host-tools.cmake`。
- 构建发现（`cmake/modules/FindZephyr-sdk.cmake`）：`ZEPHYR_SDK_INSTALL_DIR` 显式指定 > 搜索 `/usr /usr/local /opt $HOME $HOME/.local...` + CMake 包注册表；**多版本并存，降序选最高兼容版**。
- ⚠️ udev 规则**不自动安装**（需手工 `sudo cp 60-openocd.rules`）；`west sdk list` 实现只列已安装（文档称列可用 release，不符）。

---

## 八、Windows 原生支持（W9）

- **依赖安装**：官方 winget 清单（`doc/develop/getting_started/index.rst:174`）：`Kitware.CMake、Ninja-build.Ninja、Python.Python.3.12、Git.Git、gperf、dtc、wget、7zip`。
- **原生可用**：build / flash / debug 全链（Zephyr SDK 有 Windows 版 .7z）；MSYS2 环境亦支持（west release-notes:419）。
- **明确排除**：`native_sim`（POSIX 架构，需 WSL2 且 WSL1 不支持 32 位）、BabbleSim（Linux 可执行）、单元测试（Linux-only）、twister 的 serial-pty/remote 模式、Coccinelle；**WSL 内烧录不被支持**（flash 需 Windows 原生）；bossac Windows 为 experimental。
- **工程约束**：源码路径不能含空格（`doc/develop/application/index.rst:316-321`）。
- **west 自身 Windows 处理**：colorama 依赖（ANSI 颜色）；`os.execv` 不可用 → `west packages` 有专门的 Windows 包装脚本（`scripts/utils/west-packages-pip-install.cmd`）。
- **版本策略**：zephyr 对 west 是"最低版本 + 锁定版本"双控（cmake 检查 ≥0.14.0 + requirements-west.txt 锁 ==1.4.0）；安装用 pip（⚠️ v4.4.2 文档无 pipx 推荐）。

---

## 九、调研计划预判验证汇总

| # | 预判 | 结论 |
|---|---|---|
| 1 | west 本体纯 pip 包、不含构建逻辑，build/flash 为扩展注入 | ✅ **完全证实**（§1.1、§3.3），且比预判更彻底：west 连 boards/sdk/sign 都是扩展 |
| 2 | runner 契约在 ZephyrBinaryRunner，新增后端 <300 行 | ✅ 证实：最小 41 行（ecpprog），3 触点接入（§6.8） |
| 3 | west manifest 机制支撑"最小源码集" | 🔷 **机制证实**（import map 的 allowlist/path-prefix/subset），但 zephyr 自身 west.yml 未利用子集能力，LiteOS 需自行做仓库切分设计 |
| 4 | west 与 CMake 深耦合、GN 主线不能直接套 west build | ✅ 证实，但**边界清晰可移植**：build.py/zcmake.py 中"目录启发式、哨兵检测、进程包装、参数映射"均与 CMake 无强绑定，替换为 `gn gen/ninja -C` 即可（§4.1） |
| 5 | dry-run 全局可用 | ❌ **证伪**：v4.4.2 dry-run 是 per-runner 能力，主流后端不支持（§6.5）——LiteOS 的超越点 |

## 十、实操验证记录（本会话，WSL2 Ubuntu 22.04）

| 步骤 | 命令 | 结果 |
|---|---|---|
| 安装 | venv + `pip install west==1.4.0` | ✅（⚠️ zephyr v4.4 构建系统要求 **Python ≥3.12**，最终用 uv 装独立 CPython 3.12 建 venv；west 本体在 3.9 也能跑） |
| workspace 初始化 | `west init -l zephyr` | ✅ `.west/config` 生成（三层配置 local 层实证） |
| 模块同步 | `west update` | ✅ ~40 模块仓（~4 GB）；网络抖动需 `https_proxy` + `http.version=HTTP/1.1`，幂等可重试续传 |
| 帮助 | `west help` | ✅ 列出 zephyr 22 个扩展命令 + **hal_espressif 注入的第三方命令 `espressif`**（§3.4 外部注册机制的现场实证） |
| 板卡枚举 | `west boards` | ✅ **1014 块板**（board.yml 扫描，无需构建） |
| 构建 | `west build -b native_sim/native/64 zephyr/samples/hello_world` | ✅ CMake configure + Ninja 97 目标，产出 `zephyr.exe`（host 工具链，免 SDK；需 `ZEPHYR_TOOLCHAIN_VARIANT=host`） |
| 运行 | zephyr.exe | ✅ 输出 `*** Booting Zephyr OS build v4.4.2 ***` + `Hello World! native_sim/native/64` |
| 构建产物检查 | build/hello/ | ✅ `zephyr/runners.yaml`（§6.3 格式实证）、`build_info.yml`（west.command/topdir/version）、`compile_commands.json`（75 条，CMake 强制导出） |
| 构建 dry-run | `west build -n` | ✅ 打印将执行的 cmake 命令（**构建级** dry-run 可用） |
| **烧录 dry-run** | `west flash --dry-run` | ❌ `FATAL ERROR: native doesn't support --dry-run option`——**§6.5 结论现场验证**：dry-run 是 per-runner 能力 |
| 烧录上下文 | `west flash --context` | ✅ 打印 build 配置 + runners.yaml 路径 + 50 个支持 flash 的 runner（这是官方支持的 introspection 路径） |
| 配置 | `west config build.pristine auto` | ✅ 写入 `.west/config`（local 层），get 验证一致 |

---

## 十一、对 LiteOS L0/L1 的机制级启示（供 P3 对比文档引用）

1. **架构照搬**：独立 pip 包"lite"工具（仅多仓管理+config+help）+ `lite-commands.yml` 扩展注册（build/flash/boards/export/sdk 为 LiteOS 主仓扩展）→ 工具与领域解耦，扩展惰性加载。
2. **runner 抽象照搬**：`LiteRunner` 基类（4 钩子 + 能力声明）+ 构建期生成 runners.yaml + `--runner` 覆盖链；四后端（serial/JLink/OpenOCD/pyOCD）各 <300 行。
3. **超越点**：全局 dry-run（Zephyr 短板）；serial 后端（Zephyr 无通用串口 runner，仅有厂商工具）。
4. **GN 适配**：west build 的"三件事"（CLI 规范化→`gn gen --args`、build dir 哨兵检测→`args.gn`/`build.ninja` 特征、pristine→删 build 目录）可完整平移；`domains.yaml` 模型映射多目标。
5. **工具链分发**：`--api-url` 自建镜像 + minimal 包按需选装 + CMake/GN 注册的思路可用于 LiteOS Windows 一键安装包。
6. **不要学**：west 核心内嵌 ZEPHYR_BASE 硬编码（应通用化为"主项目定位"配置）；模块缓存键 bug。
