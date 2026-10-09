# ThreadX 开发工具与 IDE 支持现状（一手来源调研）

> 调研日期：2026-09-29
> 范围：仅采信 Eclipse ThreadX 官方仓库/站点、工具厂商（Arm/Keil、IAR、SEGGER）、芯片原厂（ST、NXP、Renesas、Microchip）官网等一手来源。
> 标注约定：✅ 一手来源已确认 ｜ ⚠️ 一手来源之间存在不一致/表述过时 ｜ ❓ 未找到一手来源（不确定，勿当结论）
> 背景：Eclipse ThreadX（原 Azure RTOS）由 Microsoft 于 2023-11 捐给 Eclipse 基金会；官网 threadx.io 称其为“唯一经安全认证的开源 RTOS”。

## 〇、一句话结论

- ThreadX **官方无自研 IDE**：官方提供内核源码（MIT）+ **CMake `add_subdirectory()`** 集成方式，仓库自带 `.devcontainer`/`.vscode`，但**未发布官方 VS Code 扩展**。✅
- **IAR 提供官方 ThreadX C-SPY 内核感知插件**（随 EW 交付，7 个调试窗口），是 ThreadX 商业调试体验最完整的一手方案。✅
- **Keil MDK 侧无 Arm/Microsoft 官方 ThreadX 内核 pack**；与 ThreadX 相关的 CMSIS-Pack 多为**原厂发布**（如 `NXP::AZURE_RTOS`）。μVision 的 RTOS 感知官方面向 RTX/CMSIS-RTOS2。⚠️
- 原厂集成：**ST（X-CUBE-AZRTOS）、Renesas（e² studio/Smart Configurator）、Microchip（MPLAB X + Harmony 3）在；NXP 已停止提供**（官方页明示 MCUXpresso SDK 2.15 之后不再随发布提供）。✅
- 跟踪：**TraceX** 已随 Eclipse ThreadX 开源（MIT），但**宿主仅 Windows**（Microsoft Store / 安装器分发）；**SEGGER SystemView 官方支持 ThreadX**。✅

## 一、工具清单表格

| 工具 | 归属 | 覆盖环节 | 宿主 OS | 许可 | 来源 URL |
|---|---|---|---|---|---|
| Keil MDK / μVision（Arm） | 工具厂商官方（ThreadX 非内置） | 编辑/构建/烧录/调试 | Windows（μVision） | 商业（有社区版） | <https://www.keil.arm.com/keil-mdk/> |
| Keil Studio（VS Code 扩展 `Arm.keil-studio-pack`） | 工具厂商官方（Arm） | 编辑/构建/调试（CMSIS 方案） | Win/Linux/macOS | 免费+商业 | <https://marketplace.visualstudio.com/items?itemName=Arm.keil-studio-pack> |
| `NXP::AZURE_RTOS` CMSIS Pack v2.0.0（2024-07，基于 MCUXpresso SDK 2.16.0） | 原厂（NXP） | 集成/构建（ThreadX 全家桶） | 随 MDK/Keil Studio/cmsis-toolbox | 随 SDK | <https://www.keil.arm.com/packs/azure_rtos-nxp/> |
| IAR EW + ThreadX C-SPY 插件 | 工具厂商官方（IAR） | 编辑/构建/烧录/调试（**ThreadX 内核感知**） | Windows/Linux | 商业 | <https://updates.iar.com/SuppDB/Public/UPDINFO/005211/arm/doc/threadx_quickstart.pdf> ｜ <https://www.iar.com/products/architectures/arm/iar-embedded-workbench-for-arm/> |
| VS Code（通用编辑器 + CMake/cppdbg） | 通用 | 编辑/构建（CMake）/调试 | Win/Linux/macOS | 免费 | <https://github.com/eclipse-threadx/threadx> |
| STM32CubeIDE / STM32CubeMX + X-CUBE-AZRTOS-xx | 原厂（ST） | 配置/构建/烧录/调试 | Win/Linux/macOS | 免费（专有） | <https://github.com/STMicroelectronics/x-cube-azrtos-h7> |
| MCUXpresso IDE / SDK | 原厂（NXP） | 配置/构建/调试 | Win/Linux/macOS | 免费 | <https://www.nxp.com/design/design-center/software/embedded-software/azure-rtos-for-nxp-microcontrollers:AZURE-RTOS>（**已停供**） |
| Renesas e² studio + Smart Configurator | 原厂（Renesas） | 配置/构建/调试 | Win/Linux | 免费 | <https://github.com/renesas/azure-rtos> |
| MPLAB X IDE + MPLAB Harmony 3（azure-rtos-threadx） | 原厂（Microchip） | 配置/构建/调试 | Win/Linux/macOS | 免费 | <https://microchip-mplab-harmony.github.io/azure-rtos-threadx/> |
| SEGGER Embedded Studio（含 SEGGER 版 ThreadX 移植） | 第三方（SEGGER） | 编辑/构建/调试/仿真 | Win/Linux/macOS | 非商业免费/商业 | <https://kb.segger.com/ThreadX_with_SystemView> ｜ <https://github.com/SEGGERMicro/threadx> |
| SEGGER SystemView（官方支持 ThreadX） | 第三方（SEGGER） | 跟踪/可视化 | Win/Linux/macOS | 免费（Friendly License） | <https://www.segger.com/products/development-tools/systemview/> |
| SEGGER Ozone | 第三方（SEGGER） | 调试（RTOS 感知插件式） | Win/macOS/Linux | 商业（部分 J-Link 含免费许可） | <https://www.segger.com/products/development-tools/ozone-j-link-debugger/technology/rtos-awareness/> |
| Ozone-ThreadX（Ozone JS 插件） | 社区 | Ozone 的 ThreadX 内核感知 | 随 Ozone | 开源 | <https://github.com/fzawadiak/Ozone-ThreadX> |
| TraceX（宿主端跟踪分析） | 官方（Eclipse ThreadX） | 跟踪分析（离线/断点上传） | **Windows（仅）** | MIT 源码；Store 免费 | <https://github.com/eclipse-threadx/tracex> ｜ <https://aka.ms/azrtos-tracex-installer> |
| GUIX Studio（GUI 设计/代码生成） | 官方（Eclipse ThreadX） | GUI 设计/代码生成 | Windows（仅） | MIT | <https://github.com/eclipse-threadx/rtos-docs> |
| CMake（`add_subdirectory`） | 官方 | 构建 | 跨平台 | MIT | <https://github.com/eclipse-threadx/threadx> |

## 二、各工具优劣与适用场景

### 1) 商业工具厂商（Arm/Keil、IAR）
- **Keil MDK / Keil Studio**：keil.arm.com pack 索引中与 ThreadX 相关的是**原厂 pack**（NXP::AZURE_RTOS、Azure RTOS Alif 等），**未见 Arm/MS 发布的内核 pack**；MDK 自带 RTOS 为 RTX/CMSIS-RTOS2。优势：生态完备、芯片厂商支持广；局限：ThreadX 非 Arm 一等公民，μVision 的 OS 感知面向 RTX，且仅 Windows。
- **IAR EW**：官方托管《The ThreadX C-SPY plugin》文档，明确 ThreadX 感知插件随 IDE 交付，提供 7 个调试窗口（线程列表、断点、线程级单步等）。优势：**官方内核感知**、跨平台、支持 VS Code 扩展与 CMake；局限：商业授权，插件文档年代较早（Express Logic 时期），对最新内核兼容性待核实。

### 2) 芯片原厂 IDE（含配置器）
- **ST**：官方 README 明确将 Azure RTOS（ThreadX/USBX/FileX 等）完整集成进 STM32Cube 环境，提供 NUCLEO-H723ZG、STM32H735G-DK 等例程。生态最完整、免费。
- **NXP**：已停止随 SDK 提供，官方页原文 “no longer offering this software as part releases after MCUXpresso SDK 2.15, and is unable to guarantee technical support”。注：keil.arm.com 仍有基于 SDK 2.16.0 的 `NXP::AZURE_RTOS@2.0.0`（2024-07），与“2.15 之后停供”存在时点差异。
- **Renesas**：`renesas/azure-rtos` 由 e² studio / Smart Configurator 引用，支持 RX 多款板卡。
- **Microchip**：MPLAB Harmony 3 的 `azure-rtos-threadx` 经 Harmony Content Manager 集成。
- **TI**：未找到 TI 一方 ThreadX 支持的一手证据（倾向不支持）。

### 3) 通用调试 / 跟踪
- **SystemView**：官方将 ThreadX 列为开箱即用支持的 RTOS（并列 embOS/FreeRTOS/Zephyr 等）。优势：跨平台、非侵入；局限：属跟踪维度，不替代 IDE 调试。
- **Ozone**：官方 RTOS 感知列出 embOS 与 FreeRTOS，**未列 ThreadX**，但提供 JS 插件 SDK；ThreadX 感知由社区插件提供。
- **TraceX**：官方宿主端跟踪分析，可处理任何按规范构造的 buffer（不限于 ThreadX）；源码 MIT，但宿主仅 Windows。

### 4) 通用编辑器 / 构建
- **VS Code**：未发现官方 ThreadX 扩展；官方用法是通用方式（CMake + `add_subdirectory`、自带 `.devcontainer`/`.vscode`），或借 Keil Studio/原厂 VS Code 扩展。
- **CMake**：官方一等公民，`add_subdirectory()` 把 ThreadX 作为子模块接入，示例 `cmake -Bbuild -GNinja -DCMAKE_TOOLCHAIN_FILE=cmake/cortex_m4.cmake .`。

## 三、通用（跨 RTOS）vs ThreadX 专属

**跨 RTOS 通用**：Keil MDK / Keil Studio、IAR EW、VS Code、CMake、SEGGER Ozone（插件式感知）、SEGGER SystemView；各原厂 IDE（IDE 通用，仅“对 ThreadX 的集成/例程”是厂商特定）。

**ThreadX 专属 / 原生**：TraceX（ThreadX 实时事件跟踪）、GUIX Studio（GUIX 图形库设计器）、IAR 的 ThreadX C-SPY 插件、`tx_user.h` 配置体系与官方 CMake 构建、原厂 SDK 中的 Azure RTOS/ThreadX 集成包（X-CUBE-AZRTOS、Harmony azure-rtos-threadx、Renesas azure-rtos）。

## 四、待核实项（不确定 / 来源冲突）

1. **NXP 当前状态口径差异**：官方页称“SDK 2.15 之后不再提供”，但 keil.arm.com 存在基于 SDK 2.16.0 的 `NXP::AZURE_RTOS@2.0.0`（2024-07）。二者或为“不再维护 vs 已发布 pack 仍在架”之别，建议向 NXP 支持渠道确认。
2. **Keil μVision 对 ThreadX 的内核感知**：未找到 Arm 官方文档明确说明 μVision 支持 ThreadX 线程/队列视图（其 OS 感知面向 RTX/CMSIS-RTOS2）。
3. **IAR ThreadX C-SPY 插件与最新内核（6.x/7.x）兼容性**：所引官方文档为较早版本，是否随最新 IAR EW 继续交付、支持最新内核待核。
4. **TI 官方 ThreadX 支持**：未找到一手证据，倾向不支持。
5. **ST 的 X-CUBE-AZRTOS 系列维护状态与最新版本**：原标题页 404，系列页存在，各系列状态待逐一核实。
6. **VS Code 中 ThreadX 调试体验**：“ST VS Code RTOS Views 不支持 ThreadX”来自社区帖（二手），待核实。
7. **TraceX/GUIX Studio 是否有非 Windows 版本**：现有官方说明仅指向 Windows；如需跨平台跟踪可评估 SystemView。
8. **许可细节**：ThreadX/TraceX = MIT（已核）；各原厂 SDK 与 SEGGER/Keil/IAR 的许可细则以厂商许可页为准。

## 附：核心一手来源

- 内核：<https://github.com/eclipse-threadx/threadx>（MIT）｜ 官网：<https://threadx.io/>
- TraceX：<https://github.com/eclipse-threadx/tracex>（MIT）｜ <https://aka.ms/azrtos-tracex-installer>
- Keil pack（NXP::AZURE_RTOS）：<https://www.keil.arm.com/packs/azure_rtos-nxp/>
- IAR ThreadX C-SPY 插件：<https://updates.iar.com/SuppDB/Public/UPDINFO/005211/arm/doc/threadx_quickstart.pdf>
- NXP 停供声明：<https://www.nxp.com/design/design-center/software/embedded-software/azure-rtos-for-nxp-microcontrollers:AZURE-RTOS>
- ST：<https://github.com/STMicroelectronics/x-cube-azrtos-h7>
- Renesas：<https://github.com/renesas/azure-rtos>
- Microchip：<https://microchip-mplab-harmony.github.io/azure-rtos-threadx/>
- SEGGER：SystemView <https://www.segger.com/products/development-tools/systemview/> ｜ ThreadX+SystemView KB <https://kb.segger.com/ThreadX_with_SystemView> ｜ Ozone 感知 <https://www.segger.com/products/development-tools/ozone-j-link-debugger/technology/rtos-awareness/>
