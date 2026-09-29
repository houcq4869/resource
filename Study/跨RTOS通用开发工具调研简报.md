# 嵌入式跨 RTOS / 跨平台通用开发工具（IDE / 编辑器 / 插件）调研简报

> 调研范围：嵌入式开发中**跨 RTOS、跨芯片原厂可复用**的通用开发工具（IDE / 编辑器 / 插件 / 调试器 / 工具链组件）。
> 原则：只采信**官方一手来源**（厂商官网、官方文档、官方 marketplace 页面）；凡本页未能从一手来源直接确认的，一律以 **⚠️ 待核实** 标注，不臆断。
> 覆盖环节缩写：**配置 / 构建 / 烧录 / 调试 / 跟踪**。
> 调研日期：2026-09（各页面版本/许可可能随时间变化，以官网为准）。

---

## 一、通用工具总表

### 1.1 VS Code 生态（编辑器 + 原厂扩展 + 通用调试扩展）

| 工具 | 类型 | 宿主 OS | 许可 | 覆盖环节 | 通用性 | 来源 URL |
|---|---|---|---|---|---|---|
| VS Code | 编辑器（非 IDE） | Windows / Linux / macOS | 免费（微软，专有） | 配置 / 构建(终端) / 调试(经扩展) | 与 RTOS/芯片无关 | https://code.visualstudio.com/ |
| C/C++ 扩展（ms-vscode.cpptools） | 编辑器扩展 | 随 VS Code | 免费（微软，专有） | 配置 / 调试 | 通用；支持 MSVC/Clang/GCC，x64/x86/arm64/arm；**不含编译器与调试器** | https://marketplace.visualstudio.com/items?itemName=ms-vscode.cpptools |
| clangd 扩展（llvm-vs-code-extensions.vscode-clangd） | 编辑器扩展 | 随 VS Code | 开源（LLVM） | 配置（补全/诊断/clang-tidy/格式化） | 通用；依赖 `compile_commands.json` | https://marketplace.visualstudio.com/items?itemName=llvm-vs-code-extensions.vscode-clangd |
| Cortex-Debug（marus25.cortex-debug） | 调试扩展 | 随 VS Code | 开源 | 调试 / 跟踪 | ARM Cortex-M 通用；支持 J-Link、OpenOCD、ST-LINK GDB server、pyOCD、Black Magic、st-util；SWO/RTT 解码；CALL STACK 中 RTOS 线程支持（取决于 GDB server） | https://marketplace.visualstudio.com/items?itemName=marus25.cortex-debug |
| STM32CubeIDE for VS Code（stmicroelectronics.stm32-vscode-extension） | 原厂扩展包 | 随 VS Code | 免费（ST，专有） | 配置 / 构建 / 烧录 / 调试 / 跟踪 | 绑定 STM32；调试支持 ST-LINK 与 J-Link；RTOS 调试支持 **FreeRTOS / ThreadX**；设备支持经 CMSIS-PACK DFP | https://marketplace.visualstudio.com/items?itemName=stmicroelectronics.stm32-vscode-extension |
| STM32CubeCLT | CLI 工具集 | Windows / Linux / macOS（64 位） | 免费（ST，专有） | 构建 / 烧录 / 调试 | 绑定 STM32；含 GNU Arm 工具链、GDB、STM32CubeProgrammer、全系 SVD | https://www.st.com/en/development-tools/stm32cubeclt.html |
| MCUXpresso for VS Code | 原厂扩展 | Windows 10/11、macOS（Big Sur–Ventura，⚠️页面列出至 13.x） | 免费（NXP，专有） | 配置 / 构建 / 烧录 / 调试 | 绑定 NXP Cortex-M（MCX/LPC/Kinetis/i.MX RT）；支持 Zephyr／Matter／MCUXpresso SDK；线程感知，支持 **FreeRTOS / Zephyr**；探针 NXP/PEmicro/SEGGER；要求 VS Code ≥1.75.1 | https://www.nxp.com/design/design-center/software/development-software/mcuxpresso-software-and-tools-/mcuxpresso-for-visual-studio-code:MCUXPRESSO-VSC |
| ESP-IDF 扩展（espressif.esp-idf-extension） | 原厂扩展 | Windows / Linux / macOS | 开源（Apache-2.0） | 配置 / 构建 / 烧录 / 调试 / 监控 | 绑定 Espressif；CMake + Ninja 构建，OpenOCD + GDB 调试 | https://marketplace.visualstudio.com/items?itemName=espressif.esp-idf-extension |
| nRF Connect for VS Code（nordic-semiconductor.nrf-connect） | 原厂扩展 | 随 VS Code | 免费（Nordic，专有） | 配置 / 构建 / 烧录 / 调试 / 内存分析 | 绑定 nRF Connect SDK / Zephyr；自带 `nrf-debug`（GDB/MI）**RTOS 感知调试器**，Thread Viewer | https://marketplace.visualstudio.com/items?itemName=nordic-semiconductor.nrf-connect |
| Arm Keil Studio Pack（= MDK v6，Arm.keil-studio-pack） | 原厂扩展包 | 随 VS Code | 非商用免费（MDK-Community）；商用需 Essential/Professional | 配置 / 构建 / 烧录 / 调试 / 跟踪 | 绑定 Arm Cortex-M/Ethos-U；CMSIS 工作流；调试经 pyOCD（ST-Link/CMSIS-DAP/ULink）或 J-Link；**RTOS 内核感知**（RTX/FreeRTOS/Zephyr） | https://marketplace.visualstudio.com/items?itemName=Arm.keil-studio-pack |
| ModusToolbox（Infineon） | 原厂工具生态（多 IDE 支持） | Windows / Linux / macOS | 免费（Infineon） | 配置 / 构建 / 烧录 / 调试 | 绑定 Infineon；**同时支持 Eclipse / VS Code / IAR EW / Arm MDK µVision**；GNU make 构建，支持 CLI/CI | https://www.infineon.com/cms/en/design-resources/development-tools/sdk/modustoolbox-software/ |
| Simplicity Studio 6（Silicon Labs） | 原厂工具生态（VS Code 为主） | Windows / macOS / Linux | ⚠️ 许可条款待核实（厂商工具） | 配置 / 构建 / 烧录 / 调试 / 分析 | 绑定 Silicon Labs；**以 VS Code 为主 IDE**，生成 CWake/Makefile/VS Code/IAR 工程 | https://www.silabs.com/software-and-tools/simplicity-studio |
| IAR VS Code 扩展（IAR Build + C-SPY Debug） | 原厂扩展 | 随 VS Code | 商业（随 IAR EW / Build Tools 授权） | 构建 / 调试 / 跟踪 / 静态分析 | 通用（多架构）：Arm、RISC-V、AVR、RL78、RX、RH850、MSP430、8051；含 C-STAT、C-SPY Listwindows、RTOS 感知 | https://www.iar.com/embedded-development-tools/iar-visual-studio-code-extension |
| IDE for Zephyr（mylonics.zephyr-ide，社区） | 调试/工程扩展 | Windows / Linux / macOS | 开源 ⚠️（许可待核实） | 配置 / 构建 / 烧录 / 调试 | 绑定 Zephyr；集成 Cortex-Debug（ST-Link/J-Link/OpenOCD/BMP）；主机工具与 SDK 自动安装 | https://docs.zephyrproject.org/latest/develop/tools/ide_for_zephyr_vscode_ext.html |

### 1.2 商业（含免费/社区版）IDE

| 工具 | 类型 | 宿主 OS | 许可 | 覆盖环节 | 通用性 | 来源 URL |
|---|---|---|---|---|---|---|
| IAR Embedded Workbench | 一体化 IDE（编译器＋链接器＋C-SPY 调试器） | **原生 Linux 与 Windows** | 商业（各产品线试用/免费版另见官网） | 配置 / 构建 / 烧录 / 调试 / 跟踪 / 静态+运行时分析 | 高：20+ 架构（Arm、RISC-V、8051、MSP430、AVR、STM8、Renesas RX/RL78/RH850/V850/M16C-R8C/78K 等）；RTOS 感知插件（PX5、Zephyr；另支持 FreeRTOS/Azure RTOS 扩展）；探针 I-jet/J-Link/PE Micro/ST-LINK；可集成 VS Code/Eclipse；CMake + IAR Build Tools CLI；FuSa（TÜV SÜD） | https://www.iar.com/embedded-development-tools/iar-embedded-workbench |
| Keil MDK v6（µVision / Keil Studio / CMSIS-Toolbox） | IDE + 工具链 + CLI | µVision **仅 Windows**；MDK v6 整体“跨主流 OS”（Keil Studio 经 VS Code） | 社区版非商用免费；Essential/Professional 商用 | 配置 / 构建 / 烧录 / 调试 / 跟踪 | 绑定 Arm Cortex-M/Ethos-U；CMSIS-Pack 生态；Arm Compiler for Embedded；RTX5 / CMSIS-FreeRTOS / MDK-Middleware；CLI 经 CMSIS-Toolbox（cbuild）；FuSa 版 | https://www.keil.arm.com/keil-mdk/ |
| Arm Development Studio | 嵌入式 C/C++ 工具链（含调试/性能分析/FVP） | ⚠️ Windows/Linux 待核实 | 商业（UBL：Gold、Gold FuSa、Success Kits）；有免费试用 | 配置 / 构建 / 烧录 / 调试 / 跟踪 | 绑定 Arm（Cortex-M/R/A、Cortex-X、Neoverse）；探针 ULINKpro、DSTREAM-ST | https://www.arm.com/products/development-tools/embedded-and-software/arm-development-studio |
| SEGGER Embedded Studio | 一体化 IDE + 工具链 | Windows / macOS / Linux | 商业 CUL（可携式）；非商用/教育 Friendly License；部分芯片厂商买断版**商用免费** | 配置 / 构建 / 烧录 / 调试 / 跟踪 / 仿真 | 高：Arm、RISC-V 等；内置 SEGGER + GCC 工具链，可用 LLVM/IAR/Arm 编译器；RTOS 感知插件；指令集仿真器 emSim | https://www.segger.com/products/development-tools/embedded-studio/ |
| GHS MULTI | 一体化 IDE（含编译器、TimeMachine、DoubleCheck） | Windows / Linux | 商业 | 配置 / 构建 / 烧录 / 调试 / 跟踪 / 静态+运行时分析 | 高：Arm、Power、Intel、RH850、RISC-V、TriCore；OS 感知（INTEGRITY、Linux、µ-velOSity、FreeRTOS、VxWorks、AUTOSAR）；FuSa（ISO 26262/IEC 61508/EN 50128） | https://www.ghs.com/products/MULTI_IDE.html |
| CLion | 跨平台 C/C++ IDE | Windows / Linux / macOS | 订阅制；**非商用免费** | 配置 / 构建 / 调试 / 跟踪 | 高：CMake/Make/Bazel/Meson；GDB/LLDB；嵌入式支持 GCC ARM、IAR、自定义工具链、GDB server；内置 PlatformIO/STM32CubeMX/Zephyr/FreeRTOS 集成 | https://www.jetbrains.com/clion/ |

### 1.3 原厂 Eclipse 基座 IDE

| 工具 | 类型 | 宿主 OS | 许可 | 覆盖环节 | 通用性 | 来源 URL |
|---|---|---|---|---|---|---|
| STM32CubeIDE | Eclipse 基座 IDE | Windows / Linux / macOS（64 位） | 免费（ST，专有） | 配置 / 构建 / 烧录 / 调试 | 绑定 STM32（全系 MCU/MPU）；GCC & Clang；ST-LINK 与 J-Link；RTOS 调试。**ST 官方声明资源正转向 VS Code 版，后者将成为主 IDE** | https://www.st.com/en/development-tools/stm32cubeide.html |
| MCUXpresso IDE | Eclipse 基座 IDE | Ubuntu 22.04/24.04、macOS 14/15、Windows 10/11 | 免费（NXP，专有） | 配置 / 构建 / 烧录 / 调试 / 跟踪 | 绑定 NXP Cortex-M（含跨界 MCU）；GNU 工具链；支持 **FreeRTOS 与 MQX**；SWO 跟踪/性能分析；探针 MCU-Link/J-Link/PE Micro/LPC-Link2 | https://www.nxp.com/design/design-center/software/development-software/mcuxpresso-software-and-tools-/mcuxpresso-integrated-development-environment-ide:MCUXpresso-IDE |
| e² studio（Renesas） | Eclipse CDT 基座 IDE | Windows / Linux（macOS 部分器件） | ⚠️ 免费（许可条款待核实） | 配置 / 构建 / 烧录 / 调试 | 绑定 Renesas（RA/RZ/RL78/RX/RH850/RISC-V）；标准 GNU GDB 调试；可选择 Renesas 或第三方编译器；E2/E2 Lite/J-Link 等仿真器 | https://www.renesas.com/en/software-tool/e-studio |
| RT-Thread Studio | 一体化 IDE（图形化配置＋SDK 管理＋调试） | ⚠️ Windows/Linux/macOS 待核实 | 社区版永久免费 | 配置 / 构建 / 烧录 / 调试 | 绑定 RT-Thread；内置图形化配置、软件包市场、SDK Manager。⚠️「基于 Eclipse」需以官方文档为准 | https://www.rt-thread.io/studio.html |

### 1.4 开源 / 免费通用工具链组件

| 工具 | 类型 | 宿主 OS | 许可 | 覆盖环节 | 通用性 | 来源 URL |
|---|---|---|---|---|---|---|
| GDB（GNU Debugger） | 调试器 | 多数 UNIX、Windows、macOS | GNU GPL（GNU 项目） | 调试 | 通用；支持 Ada/汇编/C/C++/D/Fortran/Go/ObjC/OpenCL/Modula-2/Pascal/Rust；最新 18.1；含 DAP 支持 | https://sourceware.org/gdb/ |
| OpenOCD | 片上调试器 / GDB server | Windows / Linux / macOS | ⚠️ GPL 待核实 | 烧录 / 调试 | 通用；JTAG/SWD；支持 CMSIS-DAP、ST-Link、J-Link、FTDI 等；多器件/多核；RTOS 支持（0.12.0 起含 Zephyr） | https://openocd.org/ |
| pyOCD | Python 调试/烧录工具 + API | Windows / Linux / macOS | 开源（Apache-2.0，页面明示） | 烧录 / 调试 | 通用（Arm Cortex-M）；GDB server；CMSIS-Packs；Semi-hosting/SWV；被 VS Code（Arm CMSIS Debugger、Cortex-Debug）与 Eclipse Embedded CDT 支持 | https://pyocd.io/ |
| J-Link GDB Server | GDB server（GUI + CL） | Windows / Linux / macOS | 免费（随 J-Link 软件包；需 SEGGER 探针） | 烧录 / 调试 / 跟踪 | 通用（J-Link 支持的目标）；GDB remote 协议；SWO/RTT；`-rtos` 插件加载；semihosting | https://wiki.segger.com/J-Link_GDB_Server |
| CMake | 跨平台构建系统生成器 | 跨平台 | 开源（BSD 风格）⚠️ | 构建 | 通用；生成原生构建环境（可后端 Ninja/Make） | https://cmake.org/overview/ |
| Ninja | 小型高速构建系统 | 跨平台 | 开源（Apache-2.0）⚠️ | 构建 | 通用；常作 CMake 后端 | https://ninja-build.org/ |
| ccache | 编译缓存 | Linux / Windows / macOS 等 | 开源（GPLv3+，页面明示） | 构建加速 | 通用；支持 GCC/Clang/MSVC 等 | https://ccache.dev/ |

> 说明：表中带 ⚠️ 的许可/宿主字段，是本次未能在所引一手页面直接读到明确表述的部分，建议二次核实（见第四节）。

---

## 二、分组对比与优劣

### 2.1 VS Code 生态：事实上的“跨 RTOS 主战场”

**结构**：VS Code 本身只是编辑器，**不含编译器与调试器**（C/C++ 扩展页面明确说明），实际能力由“通用扩展 + 原厂扩展 + 通用调试扩展”三层拼装：

- **语言层**：`clangd`（依赖 `compile_commands.json`，由 CMake 等生成）或微软 C/C++ 扩展。二者是几乎所有原厂 VS Code 方案的公共底座——ST 明确“改用 clangd 做 C/C++ 索引”，Keil Studio 扩展包也内置 clangd。
- **调试层**：`Cortex-Debug` 是社区通用调试适配器，支持 J-Link / OpenOCD / ST-LINK GDB server / pyOCD / Black Magic / st-util，并提供 SWO/RTT 解码与 **RTOS 线程视图（(J-Link、OpenOCD、pyOCD 各自支持哪些 RTOS 取决于其 GDB server 的 RTOS 支持）**。ESP-IDF、Zephyr-IDE 等都基于它。
- **原厂层**：ST／NXP／Nordic／Espressif／Arm／Infineon／Silicon Labs／IAR 均提供官方 VS Code 扩展。

**优势（跨 RTOS 复用性最高）**
- 同一编辑器、同一套源码体验（clangd/CMake/Ninja）可横跨几乎所有 RTOS 与芯片原厂。
- 原厂扩展负责“引脚/时钟/外设配置、烧录、原厂调试”，通用扩展负责“编辑、构建、通用调试”，职责清晰。
- 多数原厂正在**把 VS Code 当主力方向**：ST 公开表示资源聚焦 VS Code 版并把其作为主 IDE；NXP、Infineon、Silicon Labs（SS6 以 VS Code 为主 IDE）亦然。

**局限**
- **调试能力受 GDB server 与扩展实现制约**：RTOS 线程感知取决于后端 GDB server（Cortex-Debug 页面明确“支持的 RTOS 取决于 GDB server”），不如商业 IDE 的 RTOS 内核感知统一。
- **无原生跟踪深度**：指令 trace / ETM、系统级剖析等能力弱于 IAR/GHS 等商业工具（除非依赖 pyOCD/J-Link + 额外工具）。
- 需自行管理工具链（编译器、OpenOCD、pyOCD、CMake/Ninja）路径，环境搭建成本高于开箱即用的商业 IDE。

### 2.2 商业 IDE：深度调试与功能安全最强，但绑定架构/授权

- **IAR Embedded Workbench**：一手页面强调**原生 Linux 与 Windows**、20+ 架构、C-SPY 调试器（实时 trace、代码覆盖、函数剖析、**RTOS 感知**）、C-STAT（静态）与 C-RUN（运行时，限 Arm & RX）、FuSa 认证；且**同时提供 VS Code 扩展与 Eclipse 插件**，可与 CMake/CI 集成。局限：商业授权；部分旧架构仅按需提供；并非“一个 license 覆盖全部架构”（按产品线）。
- **Keil MDK v6**：以 CMSIS-Pack 生态见长，Community 版**非商用免费**是最大吸引力；µVision **仅 Windows**，跨平台能力主要靠 Keil Studio（VS Code）。局限：绑定 Arm Cortex-M/Ethos-U，面向其他架构不支持；商用需付费。
- **Arm Development Studio**：面向 Cortex-M/R/A、Cortex-X、Neoverse 的 SoC 级工具链，含 FVP 仿真与 FuSa 编译器；偏“顶层 SoC/高端”，授权为 UBL 商业模式。
- **SEGGER Embedded Studio**：一个 IDE 兼具自家与 GCC 工具链、可换用 LLVM/IAR/Arm 编译器；**部分芯片厂商买断版对商用免费**（GigaDevice、HPMicro、Nordic、Renesas、SemiDrive 等），是“免费商用 + 多架构”的少数选项；局限：生态与插件丰富度不如 VS Code。
- **GHS MULTI**：以 **TimeMachine 回溯调试、History viewer、DoubleCheck 静态分析、OS 感知**（含 FreeRTOS/AUTOSAR/Linux 等）与最高等级 FuSa 认证见长；定位高端安全关键领域，价格与门槛最高。
- **CLion**：跨平台、**非商用免费**、CMake 一等公民，嵌入式侧支持 GCC ARM/IAR/自定义工具链与 GDB server，并内置 PlatformIO/STM32CubeMX/Zephyr/FreeRTOS 集成；适合“以 CMake 为主、想要 IDE 级重构与调试”的团队。

### 2.3 原厂 Eclipse 基座系：开箱即用，但绑定原厂且被 VS Code 取代

- **共性**：STM32CubeIDE、MCUXpresso IDE、e² studio、RT-Thread Studio 都以 **Eclipse/CDT + GDB** 为基座，天然提供“工程向导 + 图形化配置 + 烧录 + 调试”，对**本厂器件开箱即用**，免费（或社区版免费）。
- **优势**：免去环境搭建；图形化配置（时钟/引脚/外设）成熟；调试体验统一。
- **局限**：
  - **强绑定单厂器件**，跨原厂/跨 RTOS 复用性低；
  - 重量级（Eclipse）、启动与索引偏慢，编辑器体验弱于 VS Code/clangd；
  - **厂商已在转向 VS Code**：ST 明确资源聚焦 VS Code 版；NXP 主推 MCUXpresso for VS Code；Silicon Labs SS6 直接以 VS Code 为主 IDE。原厂 Eclipse IDE 更像“存量维护/过渡”。

### 2.4 开源工具链：跨 RTOS 复用的“公共地基”

- **GDB + GDB server（OpenOCD / pyOCD / J-Link GDB Server）**：所有现代嵌入式 IDE/编辑器方案（VS Code、Eclipse、CLion、原厂 IDE）的调试底层几乎都基于 GDB remote 协议。三者分工：OpenOCD（开源、覆盖探针最多）、pyOCD（Python、Cortex-M、CMSIS-Pack、被 VS Code 官方 Arm 调试器与 Cortex-Debug 采用）、J-Link GDB Server（免费但需 SEGGER 探针，SWO/RTT/RTOS 插件成熟）。
- **CMake + Ninja**：已成为跨 RTOS 的**事实标准构建组合**——Zephyr、ESP-IDF、STM32Cube(VS Code)、ModusToolbox、CLion、IAR 等官方文档均以 CMake/Ninja 为主路径。**ccache** 进一步加速重复构建。
- **优势**：完全免费开源、跨平台、可脚本化、适合 CI；是“换 RTOS/换芯片后无需重学”的部分。
- **局限**：只是零件，**需要自己组装**（工具链路径、GDB server 配置、compile_commands.json、launch.json）；RTOS 感知、trace 深度有限。

---

## 三、结论：哪些是“一次投入、跨 RTOS 复用”的通用工具

**第一梯队（强烈建议作为通用底座，跨 RTOS/跨原厂复用性最高）**

1. **VS Code + clangd（或 C/C++ 扩展）+ Cortex-Debug**：编辑器与通用调试的事实标准；配合 CMake/Ninja 构建，可覆盖几乎所有 RTOS 与芯片。原厂扩展（ST/NXP/Nordic/Espressif/Arm/Infineon/Silabs/IAR）可随项目按需叠加，不影响通用底座。
2. **GDB + OpenOCD / pyOCD / J-Link GDB Server**：调试/烧录的公共地基，任何上层 IDE/编辑器都可用，换 RTOS 不需更换。
3. **CMake + Ninja + ccache**：跨 RTOS 的构建与加速标准组合，Zephyr/ESP-IDF/STM32Cube/ModusToolbox/CLion 官方均支持。

**第二梯队（按团队需求选择，通用性较好但有边界）**

4. **CLion**：非商用免费、CMake 一等公民、跨平台，适合“CMake 主导”的团队。
5. **IAR Embedded Workbench**：真正跨架构、跨 OS、带 RTOS 感知与 FuSa 的商业一体化方案；**且提供 VS Code/Eclipse 插件**，可既保留 IAR 调试深度又沿用 VS Code 体验。
6. **SEGGER Embedded Studio**：多架构、可换工具链，部分芯片厂商买断版**商用免费**，适合成本敏感又要商用授权的场景。
7. **pyOCD / J-Link GDB Server**：作为通用调试后端，配合任何编辑器均可。

**谨慎/非通用（存在绑定或方向性风险）**

- **原厂 Eclipse 基座 IDE（STM32CubeIDE / MCUXpresso IDE / e² studio / RT-Thread Studio）**：开箱即用但强绑定单厂/单 RTOS，跨原厂复用性低；且厂商资源已明显转向 VS Code，长期建议以 VS Code 为主线。
- **Keil MDK / Arm Development Studio / GHS MULTI**：能力顶尖，但分别绑定 Arm 架构 / 高端 SoC / 安全关键领域，且为商业授权，跨 RTOS 的“通用”属性有限。

**一句话结论**：**“编辑器 + 语言服务 + GDB 系调试 + CMake/Ninja”这一套（VS Code + clangd + Cortex-Debug + OpenOCD/pyOCD/J-Link + CMake/Ninja/ccache）是当前跨 RTOS、跨平台复用性最高、迁移成本最低的通用投入**；商业 IDE（IAR / SEGGER ES / CLion）则在需要更深调试/跟踪或授权保障时作为增强，且 IAR 还能以插件形式并入 VS Code，避免二次迁移。

---

## 四、待核实项（本次未能从一手来源直接确认）

1. **Arm Development Studio 的宿主 OS**：官网产品页未直接列出，需查其 System Requirements（是否 Windows/Linux 全覆盖、具体版本）。
2. **e² studio 许可条款与宿主 OS 完整列表**：官网英文页未给出明确许可文本；Linux 版有专门限制（RE 家族与 Synergy 不支持 Linux host）。
3. **Silicon Labs Simplicity Studio 6 的许可条款**：官网页面强调功能与宿主 OS，未读到明确许可表述。
4. **RT-Thread Studio 的技术基座与宿主 OS 列表**：官网英文页未说明“是否 Eclipse 基座”及 Windows/Linux/macOS 的完整支持情况。
5. **IAR 的 CLI 工具名称/文档（如 `iarbuild`）**：IAR 页面确认存在 “IAR Build Tools / 命令行构建”，但未直接给出 `iarbuild` 命令文档链接，建议以 IAR 官方文档为准。
6. **Keil MDK 的 Event Recorder（事件记录器）能力**：本次仅确认到 Keil Studio/MDK 的 **RTOS 内核感知与“软件组件查看器”**，Event Recorder 的明确定位与 RTOS 支持范围建议查 CMSIS/MDK 官方文档。
7. **Cortex-Debug 的 RTOS 具体清单**：官方 marketplace 页只说明“RTOS 线程支持取决于 GDB server（J-Link/OpenOCD/pyOCD）”，未给出 RTOS 明细。
8. **部分开源工具的许可细节**：OpenOCD、CMake、Ninja、VS Code、clangd、ESP-IDF 扩展、IDE for Zephyr、部分厂商工具的具体许可证文本，本页所引页面未完整明示，需以其官方 LICENSE/条款页为准。
9. **各工具最新版本号**：本页记录的时间点为 2026-09，版本号（如 GDB 18.1、pyOCD 0.44.0、Ninja 1.13.1、ccache 4.14.1、ModusToolbox 3.8、STM32CubeCLT 1.22.0）以官网实时为准。
