# RT-Thread 开发工具与 IDE 支持现状（一手来源调研）

> 调研日期：2026-09-29
> 范围：仅采信 RT-Thread 官方文档/官方仓库、官方 VS Code Marketplace（认证发布者）、ARM/Keil 官方 pack 索引、RT-Thread 官方软件包站等一手来源。
> 标注约定：✅ 一手来源已确认 ｜ ⚠️ 一手来源之间存在不一致 ｜ ❓ 未找到一手来源（不确定）

## 〇、一句话结论

- RT-Thread 官方文档在 **“Supported IDE and Compiler”** 中明确列出的 IDE/编译器只有四类：**RT-Thread Studio IDE、MDK KEIL、IAR、GCC**。
  - 来源（官方文档）：<https://www.rt-thread.io/document/site/tutorial/quick-start/introduction/introduction/#supported-ide-and-compiler>
- RT-Thread 的“官方原生链路”是 **Env（menuconfig/pkgs）+ SCons 构建 + `scons --target=xxx` 导出各 IDE 工程**；RT-Thread Studio 是基于 **Eclipse** 的一站式 IDE；**VS Code 有官方扩展（RT-Thread 认证发布者下有 3 个）**。

## 一、工具清单表格

| 工具 | 官方/第三方/社区 | 覆盖环节 | 宿主 OS | 许可 | 主要来源 URL |
|---|---|---|---|---|---|
| **RT-Thread Studio**（Eclipse 基座 IDE） | 官方 | 工程创建向导 / 图形化配置 / 代码编辑 / 构建 / 下载 / **调试（J-Link、ST-Link）** / QEMU 仿真 / SDK 管理 / 包市场 | **Windows x86_64**（官网下载脚本仅指向 `RT-Thread-Studio-setup-x86_64-latest.exe`，未见 Linux/macOS 包） | 专有 EULA（*RT-Thread Studio Software License Agreement*）；官网称“Community version is free forever” | <https://www.rt-thread.io/studio.html> ｜ 安装包来源 <https://www.rt-thread.io/js/download.js> ｜ 手册 <https://www.rt-thread.io/document/site/rtthread-studio/um/studio-user-manual/> |
| **Env 工具**（menuconfig + pkgs） | 官方 | 配置裁剪 / 图形配置 / 软件包管理 / 调用 scons 构建 | **Linux、Windows**（`RT-Thread/env` 与 `RT-Thread/env-windows`；未见 macOS 说明） | GPLv2（`env` 仓库 LICENSE，已核） | <https://github.com/RT-Thread/env> ｜ <https://github.com/RT-Thread/env-windows> ｜ 文档 <https://www.rt-thread.io/document/site/programming-manual/env/env/> |
| **SCons 构建 + `scons --target=*` 导出** | 官方 | 构建 / 各 IDE 工程导出 | Windows、Linux 等（需 Python + SCons） | SCons 自身许可 ❓；RT-Thread 工程本体 Apache-2.0 | <https://github.com/RT-Thread/rt-thread/blob/master/tools/building.py> ｜ <https://github.com/RT-Thread/rt-thread/tree/master/tools/targets> |
| **VS Code 扩展 `RT-Thread.rt-thread-studio`**（“RT-Thread Studio For Vscode”，2023-06 最后更新） | 官方（认证发布者 RT-Thread） | 打开 BSP/Studio 工程、单/多工程管理、RT-Thread Settings 图形配置、构建/清理（scons）、**下载/调试（J-Link、ST-Link）**、QEMU；支持 GNU ARM GCC、ARMCC | 跟随 VS Code（Win/Linux/macOS） | **专有**（扩展 License 文本即 *RT-Thread Studio Software License Agreement*） | <https://marketplace.visualstudio.com/items?itemName=RT-Thread.rt-thread-studio> |
| **VS Code 扩展 `RT-Thread.rt-thread-smart`**（RT-Thread Smart Extension，持续更新至 2026-02） | 官方（认证发布者 RT-Thread） | 构建、env 脚本环境、工程文件/Groups 视图、ELF 符号分析；面向 RT-Thread 及 RT-Thread Smart（**要求 RT-Thread > v5.2.0**） | 跟随 VS Code（README 安装脚本给 Windows PowerShell） | GPLv2（仓库 LICENSE，已核） | <https://github.com/RT-Thread/vscode-rt-smart> ｜ <https://marketplace.visualstudio.com/items?itemName=RT-Thread.rt-thread-smart> |
| VS Code 扩展 `RT-Thread.rt-thread-micropython`（2022） | 官方（认证发布者 RT-Thread） | MicroPython 应用开发 | 跟随 VS Code | ❓ | <https://marketplace.visualstudio.com/items?itemName=RT-Thread.rt-thread-micropython> |
| VS Code 社区扩展：`rtthreadfans.rtthread-assistant`（Rt-Thread Assistant，2020）、`jswyll.jswyll-vscode-rtthread`（RT-Thread Project Assistant，更新至 2025-10） | 第三方/社区 | 配置 / 构建 / 调试辅助 | 跟随 VS Code | 各自（发布方未标明） | <https://marketplace.visualstudio.com/items?itemName=rtthreadfans.rtthread-assistant> ｜ <https://marketplace.visualstudio.com/items?itemName=jswyll.jswyll-vscode-rtthread> |
| **Keil MDK**（经 `scons --target=mdk5` 导出 `project.uvprojx` / `mdk4`→`uvproj` / `mdk`→`Uv2`）+ **官方 MDK 器件包** | 官方导出 + 官方 pack（vendor=RealThread, name=RT-Thread, v3.1.5） | 构建 / 烧录 / 调试 | Windows ❓（Arm 官方产品，本次未逐条核对系统要求） | MDK 为商业软件；pack 遵循 Keil 条款 | 导出见 <https://www.rt-thread.io/document/site/programming-manual/scons/scons/> ｜ pack 索引 <https://www.keil.com/pack/index.pidx>（条目 `url="https://www.rt-thread.org/download/mdk/"`） |
| **IAR EWARM**（`scons --target=iar` 导出 `project.eww`） | 官方导出 | 构建 / 烧录 / 调试 | Windows ❓（IAR 商业产品） | IAR 商业 | <https://www.rt-thread.io/document/site/programming-manual/scons/scons/> ｜ <https://github.com/RT-Thread/rt-thread/blob/master/tools/building.py> |
| **Eclipse CDT / RT-Thread Studio 工程**（`scons --target=eclipse`，`targets/eclipse.py` 内部 `import rt_studio`，生成 `.project`/`.cproject`/`projcfg.ini`） | 官方 target | 构建 / 调试（GCC/GDB 链路） | 跨平台 | Eclipse 系 EPL | <https://github.com/RT-Thread/rt-thread/blob/master/tools/targets/eclipse.py> |
| 其它 `scons` 导出目标：**SES、CDK、vs/vs2012、cb、ua、makefile、cmake/cmake-armclang、xmake、codelite、esp-idf、vsc/vsc_workspace、zig**| 官方 target | 构建 / 工程导出 | 依目标工具 | 依目标工具 | `tgt_dict` 见 <https://github.com/RT-Thread/rt-thread/blob/master/tools/building.py> ｜ `tools/targets/` 目录 |
| **CMake**（`scons --target=cmake` / `cmake-armclang`，生成 `CMakeLists.txt` 与编译数据库） | 官方 target | 生成 CMake 工程/编译数据库 → 可被 **CLion、VS Code CMake Tools** 等消费 | 跨平台 | — | <https://github.com/RT-Thread/rt-thread/blob/master/tools/targets/cmake.py>（CLion 支持为推论，官方未文档化，见四） |
| **QEMU BSP 仿真**（BSP 提供 `qemu.bat`/`qemu.sh`，Env 与 Studio 均支持） | 官方 | 仿真运行 / 调试 | Windows（.bat）/ Linux（.sh） | QEMU GPLv2 | <https://www.rt-thread.io/document/site/tutorial/quick-start/stm32f103-simulator/stm32f103-simulator/> |
| **ulog**（内核日志组件） | 官方 | 日志 / 跟踪 | — | Apache-2.0（RT-Thread 本体） | <https://www.rt-thread.io/document/site/programming-manual/ulog/ulog/> |
| **SEGGER SystemView**（官方软件包，发布者 RealThread） | 官方包 | 跟踪 / 可视化 | — | — | <https://packages.rt-thread.org/en/search.html?search=SystemView> |
| **CmBacktrace**（官方软件包，armink，v1.2.0，MIT） | 官方包 | 故障回溯（Cortex-M） | — | MIT | <https://packages.rt-thread.org/en/search.html?search=CmBacktrace> |
| **Percepio Tracealyzer** | ❓ 未找到官方包/官方文档条目 | — | — | 商业 | 官方包站搜索无结果（见四） |

## 二、各工具优劣与适用场景

### 1) RT-Thread Studio（官方主推 IDE）
- **定位**：官方一站式 IDE，含工程创建向导、图形化配置（支持 schema 图与树状图）、包市场、SDK Manager、J-Link/ST-Link 调试、QEMU 仿真。
- **基座**：Eclipse（FAQ 明确出现 “Eclipse Platform Launcher Executables”；手册提到 “native Eclipse” 的 virtual folder / linked file 概念）。
  - 来源：<https://www.rt-thread.io/document/site/rtthread-studio/faq/studio-faq/>
- **优势**：开箱即用、与 RT-Thread 包/配置深度集成、图形化配置降低门槛、社区版免费、支持导入并同步 MDK 工程（v2.1.0 起）。
- **局限**：**专有许可**、**官网安装包仅 Windows x86_64**、扩展/插件生态与开放度不如 VS Code；对“非 Windows 宿主”基本不可用。
- **适用**：Windows 上以 RT-Thread 为主、希望图形化配置 + 一体化调试的个人/团队。

### 2) Env 工具（menuconfig / pkgs + scons）
- **定位**：命令行套件，提供构建环境、图形系统配置（menuconfig）、软件包管理（pkgs）。Windows 版自带 Python + SCons + ARM GCC。
- **优势**：轻量、Windows 与 Linux 均支持、是 `scons --target=*` 导出各 IDE 工程的前置工具；包管理 `pkgs --update/--upgrade` 成熟。
- **局限**：命令行交互、学习曲线；v2.0 与旧内核兼容性有约束——**env v2.0 / env-windows v2.0 仅完整支持 RT-Thread > v5.1.0 或 master**，旧版本需用 v1.5.x（GPLv2 许可）。
  - 来源：<https://github.com/RT-Thread/env>（README）
- **适用**：所有宿主的“配置 + 构建 + 导出 IDE 工程”中台，尤其 Linux/CI。

### 3) SCons + `scons --target=*`（官方构建与“IDE 桥接”）
- `scons` 真编译（默认 ARM GCC）；`scons --target=<IDE>` 生成对应该 IDE 的工程文件（前提是 BSP 里有工程模板）。
- `options.py` 帮助串与 `building.py` 的 `tgt_dict` 给出的目标集合（**代码为准**）：`mdk / mdk4 / mdk5 / iar / vs / vs2012 / vsc / vsc_workspace / cb / ua / cdk / makefile / eclipse / ses / cmake / cmake-armclang / xmake / codelite / esp-idf / zig`。
- **优势**：一套脚本覆盖几乎所有主流 IDE；工程可随 `menuconfig` 配置变化而“重新生成”，避免手改 IDE 工程。
- **局限**：导出依赖 BSP 提供模板文件；文档与实际代码存在不一致（见四）。
- 来源：<https://github.com/RT-Thread/rt-thread/blob/master/tools/building.py> ｜ <https://github.com/RT-Thread/rt-thread/blob/master/tools/options.py>

### 4) VS Code（官方 3 扩展 + 社区）
- **官方 `rt-thread-studio` 扩展**：把 Studio 的核心能力搬进 VS Code——打开 BSP/Studio 工程、RT-Thread Settings 图形配置、scons 构建、J-Link/ST-Link 下载调试、QEMU；支持 GNU ARM GCC / ARMCC。**注意：为专有许可**，且最后更新停留在 2023-06。
- **官方 `rt-thread-smart` 扩展**：面向 RT-Thread 及 RT-Thread Smart，**GPLv2**，2026-02 仍在更新；含工程视图、构建、env 环境、ELF 符号分析，但 README 明示要求 **RT-Thread > v5.2.0**。
- **社区扩展**：`rtthread-assistant`（2020）、`RT-Thread Project Assistant`（jswyll，更新至 2025-10）——非官方，功能与维护状态各异。
- **适用**：习惯 VS Code、需要跨平台（Linux/macOS）编辑 + 调试的用户；建议按内核版本选 `rt-thread-smart`（新）或 `rt-thread-studio`（旧、专有）。

### 5) Keil MDK / IAR（商业 IDE，经 scons 导出接入）
- `scons --target=mdk5` 生成 `project.uvprojx`（MDK4→`project.uvproj`，MDK2→`project.Uv2`）；`scons --target=iar` 生成 `project.eww`。
- 另外 ARM/Keil 官方 pack 索引中存在 **vendor=RealThread、name=RT-Thread、version=3.1.5** 的器件包（`https://www.rt-thread.org/download/mdk/`）——即 RT-Thread 官方提供的 MDK 支持包（版本较旧）。
- **优势**：编译器/调试器成熟、生态广、商业支持；**局限**：商业授权、Windows 为主、与 RT-Thread 配置系统的联动需靠重新导出工程。

### 6) Eclipse / CMake / Makefile / 其它
- `--target=eclipse`：生成 Eclipse（及 RT-Thread Studio 同构的 `.project/.cproject/projcfg.ini`）工程；跨平台、可用于 GCC/GDB 链路。
- `--target=cmake|cmake-armclang`：生成 `CMakeLists.txt` 与编译数据库，理论上可被 CLion / VS Code CMake Tools 使用（**官方文档未把 CLion 列为支持项，属推论**）。
- `--target=makefile`：生成 Makefile 构建。
- 其余（SES/CDK/vs/vs2012/cb/ua/vsc/xmake/codelite/esp-idf）为特定 IDE/工具链导出。

### 7) 跟踪与调试
- **调试**：Studio 官方支持 **J-Link、ST-Link**；RT-Thread-Studio 官方组织下另有 `sdk-debuger-jlink`、`sdk-debugger-pyocd` 仓库（暗示 pyOCD 支撑）。官方 VS Code 扩展也提供 J-Link/ST-Link 调试。
  - 来源：<https://www.rt-thread.io/document/site/rtthread-studio/um/studio-user-manual/> ｜ <https://github.com/RT-Thread-Studio>
- **跟踪/日志**：`ulog` 为内核日志组件；**SEGGER SystemView 有官方包**；**CmBacktrace** 官方包用于故障回溯。**未发现 Percepio Tracealyzer 的官方包或官方文档**（见四）。

## 三、通用（跨 RTOS）vs RT-Thread 专属

**跨 RTOS 通用（本身不绑定 RT-Thread，接入需适配/导出）**
- Keil MDK、IAR EWARM、Eclipse CDT、VS Code（编辑器本体）、CLion（经 CMake）、CMake / Makefile、GDB / OpenOCD / pyOCD / J-Link、QEMU、SEGGER SystemView（工具本身跨 RTOS，需 RTOS 侧适配）、Percepio Tracealyzer（工具本身跨 RTOS，RT-Thread 适配情况未确认）。
- 说明：这些工具通过 `scons --target=...` 生成的“标准工程文件”与 RT-Thread 对接，工具本身并不认识 RT-Thread。

**RT-Thread 专属**
- **RT-Thread Studio IDE**（Eclipse 定制版，专有）、**Env 工具**（menuconfig/pkgs 为 RT-Thread 定制）、**SCons 构建体系与各 `--target` 导出器**、**ulog / FinSH(msh)**、**官方 MDK 器件包（RealThread pack）**、**官方 VS Code 扩展**（`rt-thread-studio` / `rt-thread-smart` / `rt-thread-micropython`）。

## 四、待核实项（不确定 / 来源冲突）

1. **Studio 宿主 OS 是否仅 Windows**：官网下载脚本只给出 `RT-Thread-Studio-setup-x86_64-latest.exe`（Windows x86_64），但用户手册/FAQ 未写明“仅 Windows”及最低系统版本。⚠️ 证据强但无官方明文结论。
2. **`--target=eclipse` 与官方 FAQ 冲突**：官方 Env 文档 FAQ 写 “There is **no** automatic generation of eclipse projects”，但代码 `building.py`/`targets/eclipse.py` 存在 `eclipse` 目标并会生成 Eclipse/RT-Thread Studio 工程文件。⚠️ FAQ 可能过时，需以官方最新说明为准。
3. **`--target` 目标集合以代码为准，文档滞后**：文档页仅举例 `iar / mdk4 / mdk5 / vs2012 / vs2005` 及提到 `ua / vs / cb / cdk`；代码 `tgt_dict` 还含 `mdk / vsc / vsc_workspace / makefile / eclipse / ses / cmake / cmake-armclang / xmake / codelite / esp-idf / zig`。其中 **`zig` 在 `tgt_dict` 中存在，但 `GenerateProject` 未见到对应分支**，是否真正可用待核实。
4. **Tracealyzer（Percepio）是否有官方 RT-Thread 支持**：官方包站搜索无结果；Percepio 官网是否将 RT-Thread 列为受支持 RTOS 未核实。❓
5. **CLion 官方支持**：RT-Thread 未在官方文档列出 CLion；`--target=cmake` 生成 CMake 工程可作为间接途径（推论）。❓
6. **SCons 自身许可**：未从一手来源确认（RT-Thread 本体为 Apache-2.0；`env` 仓库为 GPLv2）。
7. **官方 VS Code 扩展对“标准版 RT-Thread”的版本适配**：`rt-thread-smart` 明示需 > v5.2.0；`rt-thread-studio` 扩展最后更新 2023-06，其对新内核的兼容性未说明。❓
8. **Keil MDK / IAR 官方系统要求**：本次未逐条抓取 Arm/IAR 官方系统要求页，宿主 OS 以“Windows”记录但未一手核实。❓

## 附：核心一手来源清单

- 官方文档站（英文）：<https://www.rt-thread.io/document/site/>（“Supported IDE and Compiler”锚点见正文）
- 官方主仓（构建脚本/各 IDE 导出器）：<https://github.com/RT-Thread/rt-thread>
  - `tools/building.py`：`tgt_dict` 全量目标
  - `tools/options.py`：`--target` 帮助串
  - `tools/targets/`：`keil.py / iar.py / vsc.py / cmake.py / eclipse.py / rt_studio.py / ses.py / cdk.py / makefile.py …`
- Env：<https://github.com/RT-Thread/env>、<https://github.com/RT-Thread/env-windows>
- Studio：<https://www.rt-thread.io/studio.html>、<https://www.rt-thread.io/document/site/rtthread-studio/um/studio-user-manual/>、<https://github.com/RT-Thread-Studio>
- 官方 VS Code 扩展：<https://marketplace.visualstudio.com/items?itemName=RT-Thread.rt-thread-studio>、<https://marketplace.visualstudio.com/items?itemName=RT-Thread.rt-thread-smart>、<https://github.com/RT-Thread/vscode-rt-smart>
- Keil pack 索引：<https://www.keil.com/pack/index.pidx>
- 官方软件包站：<https://packages.rt-thread.org/>
