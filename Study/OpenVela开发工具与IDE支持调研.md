# OpenVela（openvela）开发工具与 IDE 支持现状（一手来源调研）

> 调研日期：2026-09-29
> 范围：仅采信 openvela 官方文档站/官方仓库（github.com/open-vela、iot.mi.com/vela、openvela.com）、Apache NuttX 官方文档站/官方仓库（nuttx.apache.org、github.com/apache/nuttx），以及官方 VS Code Marketplace 页面等一手来源。
> 标注约定：✅ 一手来源已确认 ｜ ⚠️ 一手来源之间存在不一致/表述过时 ｜ ❓ 未找到一手来源（不确定，勿当结论）
> 背景：openvela 是小米开源的 AIoT 操作系统，**内核基于 Apache NuttX**（README 原文 “openvela Kernel is built upon Apache NuttX”），因此其工具链大量继承自 NuttX。

## 〇、一句话结论

- **openvela（C/C++ 系统开发）没有自研 IDE**，官方主推链路是 **VS Code + 官方扩展 + 命令行（build.sh / CMake / menuconfig）+ GDB**；官方文档明确给出了 **VS Code 图形化全流程**与 **CLion 远程 GDB 调试**用法。✅
  - 来源：<https://github.com/open-vela/docs/blob/dev/en/quickstart/vscode_plugin_usage.md> ｜ <https://github.com/open-vela/docs/blob/dev/en/quickstart/emulator/Debugging_Vela_with_Vela_Emulator.md>
- **JS 快应用（Xiaomi Vela JS 应用）**另有官方独立 IDE **AIoT-IDE**，官方明确“建立在 Visual Studio Code 的基础上”，支持 Windows/macOS/Ubuntu。✅
  - 来源：<https://iot.mi.com/vela/quickapp/zh/tools/> ｜ <https://iot.mi.com/vela/quickapp/zh/guide/start/use-ide.html>
- **NuttX 上游（Apache 官方）没有官方 IDE，也没有官方 VS Code 扩展**；官方工作流是命令行（`configure.sh` + `make`，或 CMake）+ OpenOCD/GDB，且**官方支持导出 IAR / Keil uVision 工程**（`tools/ide_exporter.py`）。Marketplace 里 "nuttx" 仅 2 个第三方扩展，其中 "NuttX Dev Pack" 明确声明“非 NuttX 团队官方运营”。✅
  - 来源：<https://nuttx.apache.org/docs/latest/quickstart/index.html> ｜ <https://nuttx.apache.org/docs/latest/components/tools/ide_exporter.html> ｜ <https://marketplace.visualstudio.com/items?itemName=NuttX.nuttx-dev-pack>
- **NuttX 官方文档确有“Windows 原生构建”描述**（`CONFIG_WINDOWS_NATIVE=y` + `CMD.exe` + GNUWin32/MinGW），但标注为“work in progress”；当前主推的是 Linux（最自然）与 macOS。**openvela 侧则仅支持 Ubuntu 22.04，官方明确不支持 WSL/Docker**。✅/⚠️

## 一、工具清单表格

| 工具 | 官方 / 第三方 / 社区 | 覆盖环节 | 宿主 OS | 许可 | 主要来源 URL |
|---|---|---|---|---|---|
| **openvela VS Code 扩展 `vela.vs-aiot-ide-vela`** | 官方（发布者 `vela` = xiaomi-vela） | 创建工程（repo 拉源码）/ 配置 defconfig / 构建 / 运行模拟器 / **调试** / 创建原生 App | 随 VS Code；官方指南限定 **Ubuntu 22.04**（arm64/x86_64），VS Code ≥ 1.99.0 | 免费；**专有**（未标注开源许可） | <https://github.com/open-vela/docs/blob/dev/en/quickstart/vscode_plugin_usage.md> ｜ <https://marketplace.visualstudio.com/items?itemName=vela.vs-aiot-ide-vela> |
| **openvela VS Code 扩展 `vela.vela-preview`** | 官方（同上） | 资源可视化预览（图片 / `.bin` / `.ttf`）、模拟器文件系统挂载 | 同上（跟随 VS Code） | 免费；专有 | <https://github.com/open-vela/docs/blob/dev/en/quickstart/vscode_plugin_usage.md> ｜ <https://marketplace.visualstudio.com/items?itemName=vela.vela-preview> |
| **VS Code + Microsoft C/C++ 扩展**（openvela 官方调试指引） | 官方文档指引 + Microsoft 扩展 | **调试**（cppdbg / GDB MI）：断点、调用栈、变量/内存、SMP 场景 | VS Code 本身跨平台；文档示例为 Linux（sim/emulator） | C/C++ 扩展为 Microsoft **专有**（免费） | <https://github.com/open-vela/docs/blob/dev/en/debugging_tools/GDB/VSCODE_debugging.md> ｜ <https://github.com/open-vela/docs/blob/dev/en/quickstart/emulator/Debugging_Vela_with_Vela_Emulator.md> |
| **AIoT-IDE**（Xiaomi Vela JS 应用 IDE，基于 VS Code） | 官方（小米） | JS 快应用：工程初始化 / 编码 / 调试 / 内置模拟器 / 真机调试 / 打包发布 | **Windows 10+、macOS 14+、Ubuntu 20.04+** | 免费；**专有**（官网仅提供安装包） | <https://iot.mi.com/vela/quickapp/zh/tools/> ｜ <https://iot.mi.com/vela/quickapp/zh/guide/start/use-ide.html> |
| **CLion**（JetBrains） | 第三方；**openvela 官方文档给出用法** | 远程 GDB 调试（Vela Emulator）；CMake 工程 | Win/mac/Linux（CLion 自身） | 商业 | <https://github.com/open-vela/docs/blob/dev/en/quickstart/emulator/Debugging_Vela_with_Vela_Emulator.md> ｜ <https://github.com/open-vela/docs/blob/dev/en/device_dev_guide/build/CMake_quick_start.md> |
| **NuttX 命令行**（`tools/configure.sh` + `make`） | 官方（NuttX） | 配置 + 构建 | Linux（最自然）、macOS、Windows（Cygwin / 原生 MinGW / WSL） | Apache-2.0 | <https://nuttx.apache.org/docs/latest/quickstart/compiling_make.html> ｜ <https://nuttx.apache.org/docs/latest/quickstart/install.html> |
| **CMake 构建**（NuttX 上游 & openvela） | 官方（双端） | 配置 / out-of-tree 构建 / 生成 IDE 工程（VS Code、CLion、Ninja/Makefile 生成器） | 跨平台（生成器） | Apache-2.0 | <https://nuttx.apache.org/docs/latest/quickstart/compiling_cmake.html> ｜ <https://github.com/open-vela/docs/blob/dev/en/device_dev_guide/build/CMake_quick_start.md> |
| **Kconfig 配置前端**：`kconfig-frontends`(menuconfig/`kconfig-tweak`) 与 `kconfiglib`(Python) | 官方依赖的第三方工具 | 配置（menuconfig 图形化） | kconfig-frontends：Linux；**kconfiglib：可 Windows 原生/Visual Studio 配置** | kconfiglib = ISC（已核）；kconfig-frontends ❓ | <https://nuttx.apache.org/docs/latest/quickstart/install.html> ｜ <https://github.com/open-vela/docs/blob/dev/en/device_dev_guide/build/Kconfig.md> |
| **OpenOCD + GDB**（SWD/JTAG） | 官方文档推荐（第三方工具） | 调试 / 烧录 / NuttX 感知（`-rtos nuttx`） | Linux/macOS/Windows | OpenOCD GPL-2.0-or-later；GDB GPL | <https://nuttx.apache.org/docs/latest/quickstart/debugging.html> |
| **pynuttx（GDB Python 扩展）+ `tools/gdbserver.py`** | 官方（NuttX tools） | NuttX 感知调试（线程）、coredump / 崩溃日志 / rawfile 离线分析、`nxgcore` | Linux 等（需 GDB 支持 Python3.8+） | Apache-2.0 | <https://nuttx.apache.org/docs/latest/debugging/gdbwithpython.html> ｜ <https://nuttx.apache.org/docs/latest/debugging/gdbserver.html> |
| **SEGGER J-Link GDB Server + `jlink-nuttx.so` 插件** | 官方（NuttX 提供插件源码）+ SEGGER 工具 | 调试 / **线程感知**（`info threads`） | Linux（指南提供 `JLink_Linux_V688a_x86_64.deb`） | J-Link 专有；插件源码随 NuttX（Apache-2.0） | <https://github.com/open-vela/docs/blob/dev/en/debugging_tools/crash/JLINK/J_Link.md> ｜ <https://nuttx.apache.org/docs/latest/debugging/gdbserver.html> |
| **IAR Embedded Workbench**（经 `tools/ide_exporter.py` 导出） | 官方导出器（NuttX） | 工程导出 / 构建 | Windows（IAR 自身） | IAR 商业 | <https://nuttx.apache.org/docs/latest/components/tools/ide_exporter.html> |
| **Keil MDK / uVision**（经 `tools/ide_exporter.py` 导出） | 官方导出器（NuttX） | 工程导出 / 构建 | Windows（Keil 自身） | Keil 商业 | <https://nuttx.apache.org/docs/latest/components/tools/ide_exporter.html> |
| **Eclipse Trace Compass** | 官方文档推荐（第三方工具） | 跟踪可视化（消费 NuttX `trace dump` 输出） | 跨平台（Eclipse RCP） | EPL-2.0 | <https://nuttx.apache.org/docs/latest/debugging/tasktraceuser.html> |
| **QEMU** | 官方文档推荐（第三方工具） | 仿真运行 + GDB 调试（`debugging/qemugdb`） | 跨平台 | GPL-2.0 | <https://nuttx.apache.org/docs/latest/debugging/qemugdb.html> |
| **Renode** | 官方文档推荐（第三方工具） | 仿真（部分板卡可用） | 跨平台 | MIT | <https://nuttx.apache.org/docs/latest/guides/renode.html> |
| **Vela Emulator（基于 QEMU，goldfish）** | 官方（openvela） | 仿真运行 / GDB 调试 / ADB / 控制台命令 | Ubuntu（随 openvela） | ❓ 未见单独许可说明 | <https://github.com/open-vela/docs/blob/dev/en/quickstart/emulator/Debugging_Vela_with_Vela_Emulator.md> |
| **esptool** | 官方文档推荐（第三方，Espressif） | 烧录（ESP32-S3） | 跨平台（Python） | GPL-2.0 | <https://github.com/open-vela/docs/blob/dev/en/quickstart/development_board/ESP32-S3-EYE.md> |
| **STM32CubeProgrammer** | 官方文档推荐（第三方，ST） | 烧录（STM32 系列） | Win/Linux/macOS | ST 专有（免费） | <https://github.com/open-vela/docs/blob/dev/en/quickstart/development_board/STM32F411.md> ｜ <https://github.com/open-vela/docs/blob/dev/en/quickstart/development_board/STM32H750.md> |
| **GNU gprof** | 官方文档（NuttX） | 性能剖析（函数级 profiling） | 宿主侧分析 | GPL | <https://nuttx.apache.org/docs/latest/debugging/gprof.html> |
| **openvela cpuload / critmon / irqinfo**（结合性能分析文档） | 官方（openvela） | CPU 负载 / 性能分析 / 中断与临界区分析 | 目标侧 + 宿主分析 | Apache-2.0 | <https://github.com/open-vela/docs/blob/dev/en/debugging_tools/performance/analysis/cpuload.md> |
| 社区 VS Code 扩展 `NuttX.nuttx-dev-pack`（“NuttX Dev Pack”） | **第三方/社区**（页面自述“非 NuttX 团队官方运营”） | Makefile 相关开发辅助 | 随 VS Code | 免费（未标开源） | <https://marketplace.visualstudio.com/items?itemName=NuttX.nuttx-dev-pack> |
| 社区 VS Code 扩展 `MicroHobby.nuttx-helpers`（“NuttX Helpers”，Preview） | **第三方/社区** | checkpatch 代码检查（Lint） | 随 VS Code | 免费（未标开源） | <https://marketplace.visualstudio.com/items?itemName=MicroHobby.nuttx-helpers> |

## 二、各工具优劣与适用场景

### 1) openvela 官方 VS Code 链路（官方主推）
- **能力（官方指南逐一列出）**：Create Project（通过 repo 拉取全量源码）/ Configure（选 `defconfig` 等）/ Build / Run（启动模拟器）/ Debug（运行模拟器并 attach）/ Create Native App（模板）/ 资源预览与文件系统挂载。✅
  - 来源：<https://github.com/open-vela/docs/blob/dev/en/quickstart/vscode_plugin_usage.md>
- **前置**：Ubuntu 22.04、磁盘 ≥ 40 GB、内存 ≥ 16 GB、VS Code ≥ 1.99.0、安装 `vela.vs-aiot-ide-vela` 与 `vela.vela-preview`，**调试依赖 C/C++ 扩展**。工程绝对路径不得含中文/空格。
- **优势**：官方维护、把“拉码 + 配置 + 构建 + 仿真 + 调试”收敛进一个 GUI，降低上手门槛；配合 `.claude` AI 技能集还可用自然语言做环境搭建/驱动适配/调试。✅
  - 来源：<https://github.com/open-vela/docs/blob/dev/README.md>（“Enhanced AI-Assisted Development”）
- **局限**：宿主仅 Ubuntu 22.04（arm64/x86_64）；扩展为**专有免费**、非开源；调试仍依赖 Microsoft C/C++ 扩展。

### 2) openvela 官方 VS Code 调试（不装插件，纯 `launch.json`）
- `sim` 环境：`cppdbg` + `program=${workspaceFolder}/nuttx/nuttx`、`console=externalTerminal`，`F5` 启动后在外部终端敲 NSH 命令触发断点；SMP 需 `handle SIGUSR1 nostop noprint`；sim 联网需 root（用 GDB 包装脚本 + `miDebuggerPath`）。✅
  - 来源：<https://github.com/open-vela/docs/blob/dev/en/debugging_tools/GDB/VSCODE_debugging.md>
- Emulator 环境：`./emulator.sh vela -qemu -S -s` 后，VS Code 用 `miDebuggerPath=/usr/bin/gdb-multiarch`、`miDebuggerServerAddress=localhost:1234` 远程调试。✅
  - 来源：<https://github.com/open-vela/docs/blob/dev/en/quickstart/emulator/Debugging_Vela_with_Vela_Emulator.md>
- **优势**：不锁定专有插件，调试体验现代；**局限**：仍需 gdb-multiarch、需自行维护 `launch.json`。

### 3) AIoT-IDE（JS 快应用专用，官方独立 IDE）
- **定位**：“用于开发 Xiaomi Vela JS 应用的官方集成开发环境”，“**建立在 Visual Studio Code 的基础上**，继承了 VS Code 的全部功能”，并增强：智能编码提示、Vela JS 应用调试、实时编译预览、打包发布、真机调试；内置多屏 UI 模拟器。✅
  - 来源：<https://iot.mi.com/vela/quickapp/zh/tools/>
- **宿主**：Windows 10+ / macOS 14+ / Ubuntu 20.04+（官网下载）。✅
  - 来源：<https://iot.mi.com/vela/quickapp/zh/guide/start/use-ide.html>
- **注意**：**面向 JS 快应用，不用于 openvela 内核/C 应用开发**；与 VS Code 扩展是两条并行链路。

### 4) CLion（第三方，但 openvela 官方文档给出用法）
- openvela 官方“Debugging with Emulator”文档专设 **III. Using CLion (Remote Debugging)**：SSH 远程开发 + `Add Configuration | Remote GDB Server` + 连接 `-qemu -S -s` 的模拟器。✅
  - 来源：<https://github.com/open-vela/docs/blob/dev/en/quickstart/emulator/Debugging_Vela_with_Vela_Emulator.md>
- openvela CMake 迁移文档明确写道：CMake “与 **VSCode 和 CLion** 等主流 IDE 深度集成，提供图形化构建配置与调试”。✅
  - 来源：<https://github.com/open-vela/docs/blob/dev/en/device_dev_guide/build/CMake_quick_start.md>
- **优势**：Linux/macOS/Windows 均可用、CMake 工程直接打开、调试器成熟；**局限**：商业软件；NuttX **上游**文档未提及 CLion（仅 openvela 文档有）。

### 5) NuttX 上游命令行链路（`configure.sh` / `make` / CMake）
- `./tools/configure.sh <board>:<config>` 选择配置，`make menuconfig` 图形配置，`make` 构建；或 CMake：`cmake -B build -DBOARD_CONFIG=<board>:<config> -GNinja` → `cmake --build build`，`cmake --build build -t menuconfig`。✅
  - 来源：<https://nuttx.apache.org/docs/latest/quickstart/compiling_make.html> ｜ <https://nuttx.apache.org/docs/latest/quickstart/compiling_cmake.html> ｜ <https://nuttx.apache.org/docs/latest/quickstart/configuring.html>
- openvela 侧额外提供 `build.sh` 包装：`./build.sh <config 路径> --cmake -j$(nproc)`（CMake）或 `./build.sh <config 路径> -j8`（Makefile），`menuconfig` 通过 `./build.sh <config> --cmake menuconfig`。✅
  - 来源：<https://github.com/open-vela/docs/blob/dev/en/quickstart/openvela_ubuntu_quick_start.md> ｜ <https://github.com/open-vela/docs/blob/dev/en/device_dev_guide/build/CMake_quick_start.md>
- 便捷配置：`kconfig-tweak`、`tools/merge_config.py`、`#include` 片段合并。✅
- **优势**：零 IDE 依赖、适合 CI/容器/服务器；**局限**：无图形化工程管理，需自备编辑器。

### 6) IAR / Keil（NuttX 官方“工程导出”，openvela 未见配套）
- NuttX 官方工具 `tools/ide_exporter.py`：由 `make V=1` 的 build log + 板级模板，导出 **IAR**（`.eww/.ewp`）或 **Keil uVision**（`.uvmpw/.uvproj`）工程。✅
  - 用法示例：`./tools/ide_exporter.py makelog_f2nsh_c iar ./boards/<arch>/<chip>/<board>/ide/template/iar -o ./boards/.../nsh/iar`
- **已知限制（官方原文）**：IAR **仅支持 C、且仅 armv7-m**；`uvision_armcc` 无法编译 NuttX 汇编；`uvision_gcc` 需在 uVision 中指定 GNU 工具链路径。模板名固定（`template_nuttx.eww`、`template_nuttx.uvproj` 等）。✅
- **注意**：文档标注，部分板卡（stm3220g-eval、stm32f429-disco）的模板因 “bit rot” 已从 NuttX 仓库移除。✅
- **openvela 侧**：本次未在 open-vela/docs 中发现 IAR/Keil 的官方文档；官方推荐的是 ARM GCC、VS Code、CLion、STM32CubeProgrammer。❓（不等于不支持，只是未文档化）

### 7) 调试 / 跟踪 / 性能
- **GDB 家族**：openvela 官方 GDB 指南（命令参考 + 崩溃/死锁/变量修改/优化变量/coredump 五大场景）；NuttX 官方 OpenOCD+GDB、`pynuttx`（`tools/pynuttx/gdbinit.py`）、`tools/gdbserver.py`（从崩溃日志/rawfile/coredump 重建现场、多核 AMP 分析）；J-Link `-rtos jlink-nuttx.so` 实现线程感知。✅
- **跟踪**：NuttX `trace` 内建命令（基于 `sched_note` / `/dev/note` / noteram），`trace dump` 输出可导入 **Eclipse Trace Compass**；另有 Coresight 硬件跟踪、`sched_note` 内部机制文档。✅
  - 来源：<https://nuttx.apache.org/docs/latest/debugging/tasktraceuser.html> ｜ <https://nuttx.apache.org/docs/latest/debugging/tasktraceinternal.html> ｜ <https://nuttx.apache.org/docs/latest/debugging/coresight.html>
- **性能**：NuttX `gprof`；openvela `cpuload`（3 种统计模式）、`SCHED_CRITMONITOR`、`irqinfo`、Dhrystone/CoreMark/Whetstone 等基准。✅
- **说明**：本次**未发现** NuttX/openvela 官方文档中的独立 `perf` 工具（Linux `perf` 风格的采样器）；如需 CPU 性能分析，官方提供的是 cpuload/critmon 与 gprof。❓

### 8) 烧录
- ESP32-S3：官方指南用 **esptool**（虚拟环境安装），`make -j flash ESPTOOL_PORT=/dev/ttyACM0 ESPTOOL_BINDIR=./`。✅
- STM32F407/F411/H750：官方指南用 **STM32CubeProgrammer**（图形化，烧 `nuttx.hex`，勾选 “Skip flash erase”）。✅
- 通用 MCU：OpenOCD/`make flash`、ST-Link/J-Link。✅

## 三、跨 RTOS 通用 vs OpenVela/NuttX 专属

**跨 RTOS 通用（工具本身不绑定 NuttX/openvela，需适配/标准化接入）**
- 编辑器/IDE 本体：**VS Code**、**CLion**（经 CMake）、**IAR**、**Keil MDK**、**Eclipse（Trace Compass）**；
- 构建：**CMake**、**GNU Make**；
- 调试：**GDB**、**OpenOCD**、**J-Link**、**pynuttx**（NuttX 感知脚本，工具链可复用其思路）、**QEMU**、**Renode**；
- 烧录：**esptool**、**STM32CubeProgrammer**、OpenOCD/ST-Link/J-Link；
- 跟踪/性能：**Trace Compass**、**gprof**、**SystemView** 类工具；
- 配置：**Kconfig 体系**（Linux 系通用，NuttX 直接沿用）。
> 这些工具通过“标准工程文件（CMakeLists）/标准调试协议（GDB RSP）/标准烧录接口”与 openvela 对接，工具本身并不“认识”openvela。

**OpenVela / NuttX 专属**
- **openvela 官方 VS Code 扩展**（`vela.vs-aiot-ide-vela`、`vela.vela-preview`）——仅服务 openvela 工程模型；
- **AIoT-IDE**（Xiaomi Vela JS 应用专用；虽是 VS Code 基座，但增强功能为 Vela 专属）；
- **Vela Emulator**（openvela 自带 goldfish 仿真器）；
- **`build.sh` / `emulator.sh`**（openvela 工作区脚本）、**defconfig 目录约定**、**openvela.xml manifest**；
- **NuttX 专属**：`tools/configure.sh`、`tools/ide_exporter.py`（IAR/uVision 导出）、`tools/pynuttx/gdbinit.py`、`tools/gdbserver.py`、`tools/Makefile.host`（`jlink-nuttx.so`）、`tools/Win.mk`、`sched_note`/`trace` 内建、`CONFIG_ALLOW_*` 许可开关；
- **openvela 专属**：`vendor/openvela/boards/...` 板级配置、`.claude` AI 技能集、`packages`/`frameworks` 预置组件。

## 四、关键核实结论（对应调研问题 4）

1. **NuttX 是否官方支持 Windows 原生构建？** —— **官方文档有描述但标注为“work in progress”**。`introduction/development_environments` 列出：Windows + Cygwin、**Windows Native（CMD.exe）+ GNUWin32 + MinGW 宿主 GCC**（由 `CONFIG_WINDOWS_NATIVE=y` 触发）、Wine、MSYS（MSYS 不可用于原生构建）。`install.html` 亦指出 `kconfiglib` 可实现“**Windows native / Visual Studio** 下的配置”，并提示 Windows 需 `pip install windows-curses`。⚠️ 该页面顶部有 “Todo: revise and update links”，属偏历史文档；**当前主推宿主仍是 Linux 与 macOS**。✅/⚠️
   - 来源：<https://nuttx.apache.org/docs/latest/introduction/development_environments.html> ｜ <https://nuttx.apache.org/docs/latest/quickstart/install.html>
2. **是否有官方 VS Code 扩展？** —— **NuttX 无官方扩展**（Marketplace 搜 "nuttx" 仅 2 个，均第三方；"NuttX Dev Pack" 页面自述“非官方”）；**openvela 有官方扩展** `vela.vs-aiot-ide-vela` + `vela.vela-preview`。✅
3. **CLion 对 NuttX 的 CMake 支持？** —— **openvela 官方文档已给出 CLion 远程 GDB 调试用法**，并在 CMake 文档中把 CLion 列为集成 IDE；**NuttX 上游**仅提供 CMake 构建（可用于 CLion），但未文档化 CLion。✅/❓
4. **OpenVela 官方开发环境要求？** —— 官方 Quick Start 明确：**仅 Ubuntu 22.04（arm64/x86_64）**，磁盘 ≥ 40 GB、内存 ≥ 16 GB，`git/curl/cmake/python3/libc++abi-dev/build-essential`、**Git LFS**、`repo` 工具；**明确“不支持 WSL、不支持 Docker 容器环境”**。VS Code 插件指南同此要求。✅
   - 来源：<https://github.com/open-vela/docs/blob/dev/en/quickstart/openvela_ubuntu_quick_start.md>

## 五、待核实项（不确定 / 来源冲突）

1. **IAR/Keil 是否可用于 openvela**：open-vela/docs 未见 IAR/Keil 文档；NuttX 侧导出器存在但限制多（IAR 仅 armv7-m/C、部分模板已移除）。❓
2. **NuttX Windows 原生构建的现状**：`development_environments` 页面年代久、标注待修订；`CONFIG_WINDOWS_NATIVE=y` 在当今是否仍被积极维护/测试，未见明确官方结论。⚠️
3. **openvela 官方是否支持 macOS 宿主做系统级（C/C++）开发**：Quick Start 仅列 Ubuntu 22.04（macOS 仅出现在 JS 快应用的 AIoT-IDE 支持列表）。❓
4. **openvela 官方是否支持 IAR/Keil 之外的商业 IDE（如 Segger Embedded Studio）**：未见文档。❓
5. **NuttX 是否有独立 `perf` 风格采样器**：文档中只见 gprof 与 `osperf` 基准，未见 Linux `perf` 类工具。❓
6. **openvela 是否有独立 trace 工具文档**：en/zh-cn `debugging_tools` 下为 GDB / crash / offline_debugging / performance / stress_testing，**未见独立 trace 章节**；NuttX 侧 trace 文档完善。❓
7. **VS Code 扩展与 AIoT-IDE 的具体许可证文本**：Marketplace 标 “Free”，官方未提供开源许可声明；AIoT-IDE 基于 VS Code（Code OSS）但自身是否开源未见一手说明。❓
8. **`kconfig-frontends` 的具体许可证**：未从一手来源确认（`kconfiglib` 已核为 ISC）。❓
9. **openvela `build.sh`/`emulator.sh` 的仓库归属**：官方 quickstart 以 `./build.sh`、`./emulator.sh` 为入口；本次未能在 `open-vela/build` 仓库根定位到同名文件（GitHub 目录页未完整展示），归属待核。❓

## 附：核心一手来源清单

**openvela 官方**
- 组织与总览：<https://github.com/open-vela> ｜ 官网：<https://openvela.com/> ｜ 开发者站：<https://iot.mi.com/vela>
- 文档仓库：<https://github.com/open-vela/docs>（分支 `dev`；英文目录 `en/`）
  - Quick Start（Ubuntu）：`en/quickstart/openvela_ubuntu_quick_start.md`
  - VS Code 插件指南：`en/quickstart/vscode_plugin_usage.md`
  - VS Code 调试（sim）：`en/debugging_tools/GDB/VSCODE_debugging.md`
  - GDB 指南：`en/debugging_tools/GDB/GDB_debugging.md`
  - J-Link 线程调试：`en/debugging_tools/crash/JLINK/J_Link.md`
  - 模拟器调试（GDB / VS Code / **CLion**）：`en/quickstart/emulator/Debugging_Vela_with_Vela_Emulator.md`
  - 构建体系：`en/device_dev_guide/build/{CMake_quick_start,CMake_advanced_guide,Kconfig,Makefile_guide}.md`
  - 性能分析：`en/debugging_tools/performance/analysis/cpuload.md`
  - 开发板烧录：`en/quickstart/development_board/{ESP32-S3-EYE,STM32F407,STM32F411,STM32H750}.md`
  - AI 辅助开发技能集：<https://github.com/open-vela/.claude>
- JS 快应用 / AIoT-IDE：<https://iot.mi.com/vela/quickapp/zh/tools/> ｜ <https://iot.mi.com/vela/quickapp/zh/guide/start/use-ide.html>

**Apache NuttX 官方**
- 文档：<https://nuttx.apache.org/docs/latest/>
  - Getting Started：`quickstart/{index,install,compiling_make,compiling_cmake,configuring,debugging}.html`
  - 开发环境：`introduction/development_environments.html`
  - 调试：`debugging/{index,gdbwithpython,gdbserver,qemugdb,gprof,tasktraceuser,tasktraceinternal,coredump,coresight}.html`
  - IDE 导出：`components/tools/ide_exporter.html`
  - 仿真：`guides/{simulator,renode,qemu_tips}.html`
- 仓库：<https://github.com/apache/nuttx>（`tools/configure.sh`、`tools/Win.mk`、`tools/ide_exporter.py`、`tools/pynuttx/`、`tools/gdbserver.py`、`tools/Makefile.host`）｜ 应用：<https://github.com/apache/nuttx-apps>

**官方扩展 / 第三方工具页**
- openvela VS Code：<https://marketplace.visualstudio.com/items?itemName=vela.vs-aiot-ide-vela> ｜ <https://marketplace.visualstudio.com/items?itemName=vela.vela-preview>
- NuttX 社区扩展：<https://marketplace.visualstudio.com/items?itemName=NuttX.nuttx-dev-pack> ｜ <https://marketplace.visualstudio.com/items?itemName=MicroHobby.nuttx-helpers>
- 许可：OpenOCD（GPL-2.0-or-later）、QEMU（GPL-2.0）、esptool（GPL-2.0）、Renode（MIT）、Trace Compass（EPL-2.0）、kconfiglib（ISC）——均已在对应官方仓库 LICENSE 核实。
