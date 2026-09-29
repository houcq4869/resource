# FreeRTOS 开发工具与 IDE 支持现状（一手来源调研）

> 调研日期：2026-09-29
> 范围：仅采信 FreeRTOS 官方站（freertos.org，AWS open source）与官方 GitHub、Arm/Keil 官方文档与 pack 索引、IAR / SEGGER / Percepio / ST / NXP / Espressif / JetBrains / PlatformIO 等厂商官方页面、以及 VS Code Marketplace 官方 API。
> 标注约定：✅ 一手来源已确认 ｜ ⚠️ 一手来源之间存在不一致 ｜ ❓ 未找到一手来源（不确定）
> 说明：FreeRTOS 现由 AWS 维护，freertos.org 即其官方网站；下文“官方”指 FreeRTOS/AWS 官方（除非另注 Arm/IAR 等厂商官方）。

## 〇、一句话结论

- FreeRTOS 官方**不提供也无意绑定某个 IDE**：官方哲学是“让用户在自己选择的环境中消费我们的软件”，官方分发**内核源码 + 各 IDE/编译器对应的官方 demo**；官方“Supported Devices”页按芯片厂商列出其支持的**工具（编译器/IDE）**，明确点名 **IAR、GCC、Keil、Eclipse、Visual Studio、MCUXpresso IDE、e2 studio、Code Composer Studio、Simplicity Studio、Rowley CrossWorks、Atollic TrueStudio** 等。
  - 来源：<https://www.freertos.org/Documentation/02-Kernel/03-Supported-devices/00-Supported-devices>；<https://www.freertos.org/Documentation/01-FreeRTOS-quick-start/01-Beginners-guide/03-Build-your-first-project>
- FreeRTOS 官方**提供 CMSIS-Pack**：2022 年官方公告将 FreeRTOS LTS 库以 CMSIS-Pack 格式发布（内核此前已是 CMSIS-Pack），并点名可在 **Arm µVision IDE 与 Keil Studio** 中使用；Arm/Keil 侧维护 **`CMSIS-FreeRTOS` pack**（在 FreeRTOS 之上实现 **CMSIS-RTOS2 API**，支持 **Event Recorder** 跟踪）。
  - 来源：<https://www.freertos.org/Community/Blogs/2022/announcing-the-official-release-of-freertos-cmsis-packs>；<https://www.keil.arm.com/packs/cmsis-freertos-arm/overview/>
- 官方**未发布 VS Code 扩展**：FreeRTOS 官方博客（2021）推荐 VS Code 用 **C/C++ 扩展 + CMake Tools + Cortex-Debug** 自行搭建，而非官方封装扩展；本次经 VS Code Marketplace 官方 API 检索 `freertos` 也**未见 FreeRTOS/AWS 官方发布者**的扩展。内核感知（任务/队列/栈视图）实际由**第三方扩展（Cortex-Debug / RTOS Views）或芯片原厂扩展（STM32、NXP）**提供。
- Keil 与 IAR 的官方支持方式分别是：**Keil → CMSIS-Pack（CMSIS-FreeRTOS）+ MDK/Keil Studio**；**IAR → C-SPY 的 RTOS 感知插件（FreeRTOS/OPENRTOS 插件已内置）**。

## 一、工具清单表格

| 工具 | 属性（官方/第三方） | 覆盖环节 | 宿主 OS | 许可 | 主要来源 URL |
|---|---|---|---|---|---|
| **FreeRTOS 内核（官方源码分发）** | 官方（AWS） | 提供内核源码、移植层、官方 demo（**不含 IDE**） | 与工具无关（源码） | **MIT**（内核与库）；可选商业版 OPENRTOS/SAFERTOS（WITTENSTEIN） | 许可 <https://www.freertos.org/Documentation/02-Kernel/01-About-the-FreeRTOS-kernel/04-Licensing> |
| **FreeRTOS CMSIS-Packs（LTS 库）** | 官方（FreeRTOS/AWS） | 组件交付（CMSIS-Pack 格式），供 µVision / Keil Studio 等消费 | 依赖宿主工具 | MIT（库本体） | <https://www.freertos.org/Community/Blogs/2022/announcing-the-official-release-of-freertos-cmsis-packs> |
| **CMSIS-FreeRTOS pack**（Arm 维护） | 官方（Arm/Keil） | 配置（CMSIS-RTOS2 封装层）+ 构建 + 调试（**Event Recorder** 事件跟踪）；经 CMSIS-RTOS2 校验套件验证 | Arm Keil MDK（µVision / Keil Studio） | **Apache-2.0 AND MIT** | pack <https://www.keil.arm.com/packs/cmsis-freertos-arm/overview/> ｜ MDK 指南 <https://developer.arm.com/documentation/109350/v6/Software-components-in-CMSIS-Packs/CMSIS-FreeRTOS> ｜ 许可 <https://github.com/ARM-software/CMSIS-FreeRTOS> |
| **Keil MDK µVision**（传统 IDE） | 官方（Arm） | 配置（CMSIS-Pack 组件）/ 构建 / 烧录 / 调试；专用 RTOS 组件视图官方文档为 **RTX5**（FreeRTOS 经 CMSIS-RTOS2/Event Recorder） | Windows（❓ 未逐条核到系统要求明文） | 商业；**Community Edition 对非商业免费** | <https://www.keil.arm.com/keil-mdk/> ｜ <https://www.keil.arm.com/mdk-community/> ｜ RTX 感知（对应 RTX5）<https://support.arm.com/documentation/KAN345/1-0/RTOS-aware-Debugging> |
| **Arm Keil Studio Pack**（VS Code 扩展包，MDK v6） | 官方（Arm） | 配置（CMSIS 视图）/ 构建 / 烧录 / 调试（pyOCD 支持 ST-Link/CMSIS-DAP/ULink，或 J-Link）/ **Trace and Live 视图** | Windows / Linux / macOS（跟随 VS Code） | 扩展免费；MDK Community Edition 对非商业免费 | <https://marketplace.visualstudio.com/items?itemName=Arm.keil-studio-pack> |
| **IAR Embedded Workbench for Arm**（C-SPY 调试器） | 官方（IAR） | 配置 / 构建 / 烧录 / 调试；**RTOS-aware 调试**（任务级控制、任务列表/信号量队列查看），**FreeRTOS/OPENRTOS 插件随 EW for ARM 内置** | **Windows、Linux**（官网称跨平台 IDE） | 商业；30 天评估 / 尺寸受限 Kickstart；有教育许可 | RTOS 支持 <https://updates.iar.com/SuppDB/Public/UPDINFO/005585/arm/doc/infocenter/rtos.ENU.html> ｜ 产品页 <https://www.iar.com/embedded-development-tools/iar-embedded-workbench> ｜ 试用/教育 <https://www.iar.com/embedded-development-tools/free-trials> |
| **VS Code（本体 + C/C++ + CMake Tools + Cortex-Debug）** | 官方博客推荐组合（扩展为第三方） | 编辑 / 构建 / 调试（无官方 FreeRTOS 扩展） | Windows / Linux / macOS | VS Code 免费；Cortex-Debug 为 MIT 式开源许可 | 官方博客 <https://www.freertos.org/Community/Blogs/2021/using-visual-studio-code-for-freertos-development> ｜ Cortex-Debug <https://marketplace.visualstudio.com/items?itemName=marus25.cortex-debug> |
| **mcu-debug RTOS Views**（VS Code 扩展） | 第三方（社区，原出自 Cortex-Debug） | 调试：多 RTOS 任务/队列视图，**debugger agnostic**（支持 cortex-debug/cppdbg/cspy），支持 FreeRTOS | Windows / Linux / macOS（跟随 VS Code） | **MIT** | <https://marketplace.visualstudio.com/items?itemName=mcu-debug.rtos-views> |
| **STM32CubeIDE**（独立 IDE）与 **STM32CubeIDE for VS Code**（扩展包）+ **STM32Cube RTOS Views** | 官方（ST） | 配置（CubeMX）/ 构建 / 烧录 / 调试；**RTOS 视图支持 FreeRTOS 与 ThreadX**；VS Code 版有 RTOS 项目教程 | 独立 IDE：Windows/Linux/macOS（multi-OS）；扩展：跟随 VS Code | 免费 | IDE <https://wiki.st.com/stm32mcu/wiki/STM32CubeIDE:Introduction_to_STM32CubeIDE> ｜ 扩展 <https://marketplace.visualstudio.com/items?itemName=stmicroelectronics.stm32-vscode-extension> ｜ RTOS 视图 <https://marketplace.visualstudio.com/items?itemName=stmicroelectronics.stm32cube-ide-rtos> ｜ 教程 <https://dev.st.com/stm32cube-docs/stm32cubeide-vscode/1.0.1/en/docs/markup/tutorials/rtos_projects.html> |
| **MCUXpresso for VS Code**（NXP） | 官方（NXP） | 配置 / 构建 / 调试；**RTOS Details 视图支持 FreeRTOS 与 Zephyr**（任务/栈用量/运行时间） | Windows / Linux / macOS（跟随 VS Code） | 免费 | <https://mcuxpresso.nxp.com/mcux-vscode/26.03//html/RTOS-Details.html> |
| **ESP-IDF**（Espressif） | 官方（Espressif） | 提供 **IDF FreeRTOS（基于 Vanilla FreeRTOS v10.5.1 的双核 SMP 分支）**；构建 / 烧录 / 调试 | Windows / Linux / macOS | Apache-2.0（IDF） | <https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/freertos-smp.html> |
| **PlatformIO** | 第三方（社区） | 配置 / 构建 / 烧录 / 调试；声明 `framework = freertos`（**官方文档仅列 CHIPS Alliance、SiFive 两个平台**） | Windows / Linux / macOS（VS Code / CLI） | 开源（Apache-2.0）+ 可选 PlatformIO Plus | <https://docs.platformio.org/en/latest/frameworks/freertos.html> |
| **CLion**（JetBrains） | 官方（JetBrains） | 编辑 / 构建 / 调试；**RTOS 集成**：FreeRTOS / Azure RTOS / Zephyr 任务视图，**FreeRTOS 另有对象视图与堆视图** | Windows / Linux / macOS | 商业（学生/开源等免费档） | <https://www.jetbrains.com/help/clion/rtos-debug.html> |
| **SEGGER Embedded Studio（IDE）+ Ozone（调试器）** | 官方（SEGGER） | IDE + 独立调试器；**RTOS 感知脚本**（安装目录 `/samples`，Ozone 的脚本接口与 Embedded Studio/J-Link GDB Server 兼容） | Windows / Linux / macOS | **Friendly License**：非商业/教育免费、无功能/代码量/时间限制评估；商用需许可（部分 J-Link 型号附赠 Ozone 许可） | <https://www.segger.com/products/development-tools/embedded-studio/> ｜ 感知脚本 <https://kb.segger.com/Enable_RTOS_Awareness_in_Embedded_Studio> ｜ Ozone <https://www.segger.com/products/development-tools/ozone-j-link-debugger/> |
| **SEGGER SystemView** | 官方（SEGGER） | 跟踪 / 可视化（**跨 RTOS**：embOS、uC/OS-III、Micrium OS、**FreeRTOS**、NuttX、Zephyr、ThreadX；FreeRTOS V8–V11，**V11 起原生支持、无需改内核**） | Windows / Linux / macOS | Friendly License（同 SEGGER 条款） | <https://www.segger.com/products/development-tools/systemview/> ｜ <https://kb.segger.com/FreeRTOS_with_SystemView> ｜ 许可 <https://www.segger.com/news/seggers-systemview-now-available-under-friendly-licensing/> |
| **Percepio Tracealyzer（for FreeRTOS）** | 官方（Percepio；FreeRTOS 官方合作） | 跟踪 / 可视化 / 性能分析；**专为 FreeRTOS**（前身 FreeRTOS+Trace，2012 年起） | Windows / Linux（❓ macOS 未核） | 商业（提供免费评估） | <https://percepio.com/tracealyzer/freertostrace/> ｜ 官方文档 <https://www.freertos.org/Documentation/03-Libraries/02-FreeRTOS-plus/05-FreeRTOS_plus_Trace/00-FreeRTOS_Plus_Trace> |
| **Percepio View for FreeRTOS** | 官方（Percepio；FreeRTOS 官方文档收录） | 跟踪 / 可视化（**免费**；快照式记录，需配置 trace hooks 并重编，**无需改 FreeRTOS 源码**、无需专用跟踪硬件） | Windows / Linux | **免费** | 官方文档 <https://www.freertos.org/Documentation/03-Libraries/02-FreeRTOS-plus/05-FreeRTOS_plus_Trace/01-Percepio_View> ｜ <https://percepio.com/percepio-view-now-available-for-freertos/> |
| **Arm Development Studio**（Arm Debugger） | 官方（Arm） | 调试：**FreeRTOS OS 感知**（Debug Control 视图看任务、RTOS Data 视图看任务与队列；需 `portREMOVE_STATIC_QUALIFIER` 等编译宏） | Windows / Linux | 商业（❓ 版本/免费档未核） | <https://support.arm.com/documentation/101470/2022-1/Debugging-Embedded-Systems/About-OS-awareness/About-debugging-FreeRTOS> |
| **Eclipse + GNU MCU 及 Eclipse 派生 IDE**（STM32CubeIDE、MCUXpresso IDE、e2 studio、Simplicity Studio、Code Composer Studio、Atollic TrueStudio 等） | 官方 FreeRTOS 文档 + 各厂商官方 | 配置 / 构建 / 烧录 / 调试（GCC/GDB 链路）；官方指出“许多 IDE 现基于 Eclipse”并给出 Eclipse 工程相对路径用法 | 跨平台（依发行版） | 依发行版（多数厂商 IDE 免费） | <https://www.freertos.org/Documentation/02-Kernel/03-Supported-devices/04-Demos/IDE/Project_Workspace_Relative_File_Paths_Eclipse> ｜ 支持工具列表见官方 Supported Devices 页 |

## 二、各工具优劣与适用场景

### 1) 官方分发与 CMSIS-Pack（FreeRTOS / Arm）
- **定位**：FreeRTOS 官方只维护源码、移植层、库与官方 demo；**不自建 IDE**。“Supported Devices”页按厂商列出可用工具，官方 demo 覆盖“已知 IDE/编译器组合”。
- **CMSIS-Pack 路线（✅ 已确认）**：官方 2022 年公告将 LTS 库以 CMSIS-Pack 发布，内核此前已是 CMSIS-Pack；**Arm 侧 `CMSIS-FreeRTOS` pack 在 FreeRTOS 之上实现 CMSIS-RTOS2 API**，使应用代码可在不同内核（如 Keil RTX5）间移植，并**支持 Event Recorder** 做事件跟踪。
- **适用**：希望在不同 IDE/工具链之间迁移、或需要标准化组件交付（CMSIS-Pack）的项目；Arm Cortex-M 生态优先。

### 2) Keil MDK：µVision（传统）与 Keil Studio（VS Code，新）
- **Keil Studio Pack** 被 Arm 定位为 **µVision 的继任者**，作为 VS Code 扩展包交付 MDK v6 能力：CMSIS 视图管理工程/目标/调试配置，经 pyOCD（ST-Link/CMSIS-DAP/ULink）或 J-Link 调试，提供 Trace and Live 视图。
- **µVision** 仍是传统 Windows IDE；官方“RTOS 感知”文档主要面向 **RTX5**（Component Viewer / Event Recorder）。**FreeRTOS 经 `CMSIS-FreeRTOS` 以 CMSIS-RTOS2 封装接入并使用 Event Recorder**——µVision 是否有“FreeRTOS 专用视图”未找到一手明文（见四）。
- **许可**：MDK 商业；**Community Edition 对非商业免费**，可在 µVision 或 Keil Studio 中激活。
- **适用**：Cortex-M 主流商用/教学开发；偏爱商业级编译调试 + Arm 生态。

### 3) IAR Embedded Workbench（C-SPY）
- **RTOS-aware 调试**是 AWR 内置能力：需对应 RTOS 插件；文档明确 **FreeRTOS/OPENRTOS 插件“included（随 EW for ARM 内置）”**，可做任务级执行控制、查看任务列表与信号量队列。
- **宿主**：IAR 官方产品页现称 EW 为**跨平台 IDE（Linux + Windows）**；但本次抓到的某一 arm 版本安装文档仍写 Windows 7/10/11 64 位（见四）。
- **许可**：商业；评估 30 天或尺寸受限 Kickstart；有教育许可。
- **适用**：对代码质量/安全合规（IAR 有功能安全版）和成熟调试有要求的商业项目。

### 4) VS Code 生态（无官方 FreeRTOS 扩展）
- FreeRTOS 官方博客 2021 给出的做法：装 **C/C++ + CMake Tools + Cortex-Debug**，用 GCC/Makefile 工程接入；**并非官方封装扩展**。
- **内核感知**来自第三方/原厂：
  - **Cortex-Debug**（第三方，MIT 式许可）：J-Link / OpenOCD / ST-LINK / pyOCD 调试、SWO/ITM 解码、多核调试；RTOS 视图能力已抽离为 **RTOS Views**。
  - **RTOS Views**（mcu-debug，MIT）：**debugger-agnostic** 的多 RTOS 任务/队列视图，支持 FreeRTOS，可与其他调试器（cppdbg/cspy）配合。
  - **原厂扩展**：STM32CubeIDE for VS Code（**FreeRTOS + ThreadX** 视图）、MCUXpresso for VS Code（**FreeRTOS + Zephyr**）、ESP-IDF（基于 FreeRTOS SMP）。
- **适用**：跨平台、偏好轻量编辑器与开源工具链的开发者；要内核感知需自行选配扩展。

### 5) Eclipse 与 Eclipse 派生 IDE
- FreeRTOS 官方设有 Eclipse 专题文档（工程相对路径用法），并指出“许多 IDE 现基于 Eclipse”；官方 Supported Devices 页把 **Eclipse** 与各厂商的 Eclipse 派生 IDE（STM32CubeIDE、MCUXpresso IDE、e2 studio、Simplicity Studio、Code Composer Studio、Atollic TrueStudio 等）列为支持工具。
- **适用**：习惯 Eclipse 工作流、或使用厂商一体化 IDE（通常免费且与自家 Cube/SDK 深度集成）。

### 6) SEGGER（Embedded Studio / Ozone / SystemView）
- **Embedded Studio**：一体化 IDE（编辑器/编译器/调试器/仿真器），支持 Arm 与 RISC-V；**安装目录 `/samples` 自带 RTOS 感知脚本**（FreeRTOS 需编译时去掉符号 static 限定，调试器才能读取），脚本接口与 **Ozone、J-Link GDB Server 兼容**。官方曾明确支持 Amazon FreeRTOS 并附 RTOS 插件。
- **Ozone**：独立图形调试器，支持任意工具链构建的固件；RTOS 感知脚本接口通用。
- **SystemView**：跟踪可视化，**跨 RTOS**，FreeRTOS V8–V11，**V11 起内核原生支持**。
- **许可**：三者同属 **SEGGER Friendly License**——非商业/教育免费，且评估**无代码量/功能/时间限制**；商用需商业许可（部分 J-Link型号附赠 Ozone 许可）。
- **适用**：使用 J-Link/J-Trace 的团队；需要跨 RTOS 的统一调试 + 跟踪体验。

### 7) 跟踪工具：Percepio（与 SEGGER）
- **Tracealyzer for FreeRTOS** 是**专为 FreeRTOS 的跟踪分析工具**（前身即 FreeRTOS+Trace，2012 年起）；提供任务/中断时间线、FreeRTOS API 调用、CPU 负载、栈/堆与内存泄漏分析等。
- **Percepio View for FreeRTOS**：**免费**的跟踪工具（基于 Tracealyzer），快照式（目标 RAM 环形缓冲）、需启用 trace hooks 并重编，**不改内核源码**、无需专用跟踪硬件，宿主 Windows/Linux。
- **适用**：需要深入运行时可视化的 FreeRTOS 项目；预算有限可先用免费的 Percepio View 或 SEGGER SystemView。

### 8) CLion / Arm Development Studio / PlatformIO 等
- **CLion**：RTOS 集成提供 FreeRTOS / Azure RTOS / Zephyr 任务视图；**FreeRTOS 另有对象视图（任务/队列/信号量/互斥量/定时器）与堆视图**；需 GDB 7.4+（带 Python），并需在 `FreeRTOSConfig.h` 打开 `configUSE_TRACE_FACILITY`、`configMAX_TASK_NAME_LEN`、`configRECORD_STACK_HIGH_ADDRESS` 等。
- **Arm Development Studio**：Arm Debugger 提供 FreeRTOS OS 感知（任务/队列视图），需特定编译宏；属 Arm 自家商业 IDE（与 Keil MDK 并列）。
- **PlatformIO**：`framework = freertos` 在官方文档中**仅列出 CHIPS Alliance、SiFive 两个平台**；其它芯片多经 `arduino`/`espidf`/`stm32cube` 等 framework 间接使用 FreeRTOS（见四）。

## 三、通用（跨 RTOS）vs FreeRTOS 专属

**跨 RTOS 通用（工具本身不绑定 FreeRTOS，接入需内核侧适配/原厂扩展）**
- **通用 IDE/调试器**：Keil MDK（µVision/Keil Studio）、IAR EW（C-SPY，本身支持多 RTOS）、Eclipse + Eclipse 派生 IDE、VS Code（本体）+ Cortex-Debug / RTOS Views、CLion（FreeRTOS/Azure RTOS/Zephyr）、SEGGER Embedded Studio / Ozone、Arm Development Studio（FreeRTOS/Linux/ThreadX/PikeOS）、STM32CubeIDE、MCUXpresso for VS Code（FreeRTOS/Zephyr）、PlatformIO。
- **通用跟踪**：SEGGER SystemView（跨 RTOS）、Percepio Tracealyzer（多 RTOS，但有 FreeRTOS 专版）。
- **通用构建/调试基础设施**：GCC/Clang、GDB、OpenOCD、pyOCD、J-Link。

**FreeRTOS 专属（与 FreeRTOS 生态强绑定）**
- **`CMSIS-FreeRTOS` pack**：在 FreeRTOS 之上实现 CMSIS-RTOS2（Arm 维护，FreeRTOS 官方站亦指向）。
- **FreeRTOS 官方 CMSIS-Packs（LTS 库）**：FreeRTOS/AWS 官方发布。
- **Percepio Tracealyzer for FreeRTOS / Percepio View for FreeRTOS**：FreeRTOS 官方文档收录的“专属”分析工具（前身 FreeRTOS+Trace）。
- **IDF FreeRTOS（ESP-IDF）**：Espressif 基于 Vanilla FreeRTOS 的双核 SMP 分支。
- **原厂 FreeRTOS RTOS 视图**：STM32Cube RTOS Views、MCUXpresso for VS Code RTOS Details —— 面向 FreeRTOS（及少量其它 RTOS）的原厂集成。

> 说明：Keil/IAR/VS Code/Eclipse 这些**工具本体是通用的**，它们“支持 FreeRTOS”的方式是 **pack（Keil）** 或 **内核感知插件/脚本/视图（IAR、VS Code、CLion、SEGGER）**，而非工具本身只为 FreeRTOS 而生。

## 四、待核实项（不确定 / 来源冲突）

1. **Keil µVision 是否有 FreeRTOS 专用内核感知视图**：Arm 官方“RTOS-aware Debugging”文档（KAN345）面向 **RTX5**；`CMSIS-FreeRTOS` 提供的是 **CMSIS-RTOS2 封装 + Event Recorder**。µVision 是否存在“FreeRTOS 原生成分视图”未找到一手明文。❓
2. **FreeRTOS 官方 VS Code 扩展**：官方博客推荐第三方组合（Cortex-Debug），Marketplace API 检索 `freertos` 未见 FreeRTOS/AWS 官方发布者扩展；但 API 仅返回有限条（10 条），不排除检索遗漏。⚠️
3. **PlatformIO `framework = freertos` 的平台范围**：官方文档只列 CHIPS Alliance、SiFive；对 STM32/ESP32 等主流芯片，“freertos”是独立 framework 还是经 `stm32cube`/`espidf` 间接提供，语义需澄清。❓
4. **IAR EW 宿主 OS 冲突**：IAR 新版产品页称跨平台（Linux + Windows）；但抓到的某一 arm 版本安装文档写“Windows 7/10/11 64 位”。**Linux 原生支持起始版本未确认**。⚠️
5. **µVision 宿主 OS**：业界通常为 Windows 专属，但本次未逐条核到 Arm/Keil 官方系统要求明文。❓
6. **Arm Development Studio 的版本与免费档**：官方称支持 FreeRTOS OS 感知；其 “Community Edition / 评估” 现行授权细则未核实。❓
7. **Percepio 宿主覆盖**：Percepio View 官方文档明确 Windows/Linux；Tracealyzer 是否支持 macOS 未核。❓
8. **SEGGER SystemView 目标端许可**：GitHub 仓库（SEGGERMicro/SystemView）API 未返回 SPDX 许可；工具端为 Friendly License，目标端源码许可条款另需核对。❓
9. **官方 CMSIS-Pack 与 Arm CMSIS-FreeRTOS 的关系表述**：官方公告称“内核此前已是 CMSIS-Pack”，Arm pack 名 `ARM.CMSIS-FreeRTOS`；两者版本/来源的对应关系（官方 pack 索引条目）建议以 keil.arm.com pack 页与官方公告为准。✅/⚠️

## 附：核心一手来源清单

- FreeRTOS 官方站
  - Supported Devices：<https://www.freertos.org/Documentation/02-Kernel/03-Supported-devices/00-Supported-devices>
  - Official vs 3rd party：<https://www.freertos.org/Documentation/02-Kernel/03-Supported-devices/03-Official-vs-3rd-party>
  - Build your first project：<https://www.freertos.org/Documentation/01-FreeRTOS-quick-start/01-Beginners-guide/03-Build-your-first-project>
  - 许可：<https://www.freertos.org/Documentation/02-Kernel/01-About-the-FreeRTOS-kernel/04-Licensing>
  - Partners：<https://www.freertos.org/Partners>
  - 博客（CMSIS-Packs，2022）：<https://www.freertos.org/Community/Blogs/2022/announcing-the-official-release-of-freertos-cmsis-packs>
  - 博客（VS Code，2021）：<https://www.freertos.org/Community/Blogs/2021/using-visual-studio-code-for-freertos-development>
  - Percepio View for FreeRTOS：<https://www.freertos.org/Documentation/03-Libraries/02-FreeRTOS-plus/05-FreeRTOS_plus_Trace/01-Percepio_View>
  - Eclipse 工程相对路径：<https://www.freertos.org/Documentation/02-Kernel/03-Supported-devices/04-Demos/IDE/Project_Workspace_Relative_File_Paths_Eclipse>
- Arm / Keil
  - CMSIS-FreeRTOS pack：<https://www.keil.arm.com/packs/cmsis-freertos-arm/overview/>
  - MDK Getting Started（CMSIS-FreeRTOS 组件）：<https://developer.arm.com/documentation/109350/v6/Software-components-in-CMSIS-Packs/CMSIS-FreeRTOS>
  - Keil Studio Pack：<https://marketplace.visualstudio.com/items?itemName=Arm.keil-studio-pack>
  - MDK Community：<https://www.keil.arm.com/mdk-community/>
  - Arm DS 调试 FreeRTOS：<https://support.arm.com/documentation/101470/2022-1/Debugging-Embedded-Systems/About-OS-awareness/About-debugging-FreeRTOS>
- IAR
  - RTOS support（C-SPY）：<https://updates.iar.com/SuppDB/Public/UPDINFO/005585/arm/doc/infocenter/rtos.ENU.html>
  - EW 产品页：<https://www.iar.com/embedded-development-tools/iar-embedded-workbench>
- SEGGER
  - Embedded Studio：<https://www.segger.com/products/development-tools/embedded-studio/>
  - RTOS 感知脚本：<https://kb.segger.com/Enable_RTOS_Awareness_in_Embedded_Studio>
  - SystemView：<https://www.segger.com/products/development-tools/systemview/> ｜ FreeRTOS 集成 <https://kb.segger.com/FreeRTOS_with_SystemView>
  - Ozone：<https://www.segger.com/products/development-tools/ozone-j-link-debugger/>
  - Friendly License 公告：<https://www.segger.com/news/seggers-systemview-now-available-under-friendly-licensing/>
- Percepio
  - Tracealyzer for FreeRTOS：<https://percepio.com/tracealyzer/freertostrace/>
  - Percepio View：<https://percepio.com/percepio-view-now-available-for-freertos/>
- 芯片原厂 / 其它
  - STM32CubeIDE：<https://wiki.st.com/stm32mcu/wiki/STM32CubeIDE:Introduction_to_STM32CubeIDE> ｜ VS Code 扩展 <https://marketplace.visualstudio.com/items?itemName=stmicroelectronics.stm32-vscode-extension> ｜ RTOS 视图 <https://marketplace.visualstudio.com/items?itemName=stmicroelectronics.stm32cube-ide-rtos>
  - MCUXpresso for VS Code RTOS：<https://mcuxpresso.nxp.com/mcux-vscode/26.03//html/RTOS-Details.html>
  - ESP-IDF FreeRTOS：<https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/freertos-smp.html>
  - PlatformIO FreeRTOS：<https://docs.platformio.org/en/latest/frameworks/freertos.html>
  - CLion RTOS debug：<https://www.jetbrains.com/help/clion/rtos-debug.html>
  - Cortex-Debug：<https://marketplace.visualstudio.com/items?itemName=marus25.cortex-debug> ｜ RTOS Views：<https://marketplace.visualstudio.com/items?itemName=mcu-debug.rtos-views>
