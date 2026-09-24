# 五大 RTOS E2E 工具逐个详解

> **配套文档**：《五大 RTOS 的 E2E 各节点适配工具与作用汇总》。
> **阅读法**：工具表中不少工具是**跨 RTOS 共用**的（如 GDB/OpenOCD/J-Link/CMake/Unity/GitHub Actions）。为避免重复，本文分两部分：
> - **第一部分「通用底座」**：跨五类 RTOS 共用的工具，逐个详解，并标注它出现在哪些 RTOS / 节点。
> - **第二部分「各自专有」**：按 FreeRTOS / RT-Thread / Zephyr / ThreadX / OpenVela 分别详解其**专属**工具。
> - **第三部分「交叉索引」**：工具 → 使用它的 RTOS → 对应 E2E 节点，便于反查。
> **属性标注**：🟢开源 · 🔵免费专有 · 🟠商业 · ⚪标准/规范。
> **来源**：官方文档/官方仓库（2026-09）。不确定处标「待核实」。

---

# 第一部分　通用底座工具（跨 RTOS 共用）

## 1. 工具链 / 编译器

### Arm GNU Toolchain（`arm-none-eabi-gcc`）
- **是什么**：Arm 维护的 GNU 交叉工具链（原 GNU Arm Embedded Toolchain），含 gcc、g++、binutils、gdb、newlib。🟢（GPL 系）
- **能力**：为 Cortex-M/R/A 及裸机生成目标代码；几乎所有 MCU 场景的**默认编译器**。
- **E2E 位置**：编译构建（主）。
- **谁在用**：FreeRTOS、RT-Thread、Zephyr、ThreadX、OpenVela（OpenVela 用 `arm-none-eabi`/`riscv-none-elf`/`aarch64-none-elf` 等预编译版）。

### Keil MDK（含 Arm Compiler / armclang）
- **是什么**：Arm 官方 IDE + 编译器（armclang，基于 LLVM/Clang）+ µVision；**Keil Studio Pack 是其 VS Code 扩展形态**。🟠（有 Community 免费版）
- **能力**：优化编译、RTX/RTOS 感知调试、Event Recorder、CMSIS-DAP 下载。
- **E2E 位置**：配置/构建/烧录/调试。
- **谁在用**：FreeRTOS/ThreadX（经 CMSIS-Pack/SDK 集成）、LiteOS 目标兼容对象之一。

### IAR Embedded Workbench（ICCARM + C-SPY）
- **是什么**：IAR 的商业编译器 + IDE + C-SPY 调试器。🟠
- **能力**：跨原厂优化编译、trace/覆盖率/剖析、RTOS 感知；命令行 `iarbuild` 可入 CI。
- **E2E 位置**：构建/调试/调优。
- **谁在用**：FreeRTOS、ThreadX 等；OH/LiteOS 的 `config_iccarm.gni` 亦支持 ICCARM。

### Zephyr SDK（`sdk-ng`）
- **是什么**：Zephyr 官方一体化 SDK，按架构打包 GNU/LLVM 工具链，并内置 QEMU、OpenOCD 与宿主工具。🟢（Apache-2.0，含 GPL 组件）
- **能力**：一条命令装齐多架构工具链与调试器，消除"东拼西凑工具链"。
- **E2E 位置**：构建/调试。
- **谁在用**：Zephyr（唯一）。

### TI Arm Clang（`tiarmclang`）
- **是什么**：TI 基于 LLVM 的编译器，集成于 Code Composer Studio。🔵
- **能力**：针对 TI 器件的优化编译。
- **谁在用**：TI 原厂 SDK（承载 FreeRTOS/ThreadX）。

### 交叉工具链（语境补充）
- **是什么**：运行在 x86 宿主、产出目标机代码的工具链统称；是"host–target 分离"的必然产物。
- **E2E 位置**：构建。
- **备注**：选工具链本质是选"宿主 OS 支持 + 目标架构支持"（这也是 OH 需 Ubuntu 的根因之一）。

---

## 2. 构建系统与配置

### CMake
- **是什么**：跨平台**元构建系统**（生成 Makefile/Ninja 等）。🟢（BSD-3）
- **能力**：描述构建目标与依赖；被 Zephyr、ThreadX、原厂 SDK 广泛采用。
- **谁在用**：Zephyr、ThreadX、OpenVela（`--cmake`）、各原厂 SDK。

### Ninja
- **是什么**：专注速度的**构建执行器**。🟢（Apache-2.0）
- **能力**：按 CMake/GN 生成的依赖图高速执行编译；"生成-执行"两段式的执行端。
- **谁在用**：Zephyr、OpenVela（CMake 后端默认 Ninja）、OH（GN+Ninja）。

### Kconfig / menuconfig / guiconfig
- **是什么**：源自 Linux 的**配置/依赖求解系统**；`menuconfig`（终端）、`guiconfig`（图形）是前端。🟢（GPL-2.0）
- **能力**：把功能开关表达为带依赖的配置项，生成 `.config` → 条件编译头；解决"裁剪即配置"。
- **谁在用**：Zephyr、OpenVela（NuttX）、RT-Thread（Env）、LiteOS-M/A。

### Device Tree（DTS/DTSI/DTB）+ `dtc` + `dt-schema`
- **是什么**：**声明式硬件描述**；`dtc` 把 `.dts` 编译为内核可解析的 `.dtb`；`dt-schema` 用 YAML binding 校验。🟢（dtc GPL/BSD 双许可，dt-schema BSD-2）
- **能力**：把硬件拓扑从代码中解耦，一份内核适配多块板。
- **谁在用**：Zephyr；LiteOS-A/Linux（设备树思想）。

### SCons
- **是什么**：Python 编写的构建系统。🟢（MIT）
- **能力**：脚本化构建；RT-Thread 用其构建并**导出 GCC/MDK/IAR 工程**。
- **谁在用**：RT-Thread（唯一核心）。

### west
- **是什么**：Zephyr 的**元工具**（仓库管理 + 构建/烧录/调试封装）。🟢（Apache-2.0）
- **能力**：`west init/update`（多仓 manifest）、`west build/flash/debug/sign`、`west boards`。
- **谁在用**：Zephyr（唯一核心）。

### Make / Makefile
- **是什么**：最经典的构建工具。🟢（GPL-3.0）
- **能力**：轻量、可读、无额外依赖；LiteOS-M/A、NuttX/OpenVela 保留 Makefile 作为独立/轻量构建路径。
- **谁在用**：OpenVela（默认）、LiteOS-M/A（兜底，对应"轻量化兜底兼容"）。

### GN（Generate Ninja）
- **是什么**：Chromium 系元构建系统，生成 Ninja 文件。🟢（BSD-3）
- **能力**：OH 全系统构建的配置层（`hb → GN → Ninja`）。
- **备注**：五类 RTOS 中不直接使用，但**是 LiteOS/OH 的构建主线**，故列此说明。

---

## 3. 调试探针与调试器

### SEGGER J-Link
- **是什么**：事实标准的商业调试探针。🟠
- **能力**：JTAG/SWD/SWO；覆盖 Cortex-M/A/R、RISC-V、Xtensa 等；配套 J-Link GDB Server、J-Link Commander、RTT、J-Flash（量产烧录）。
- **E2E 位置**：在线调试/烧录（+RTT 通道）。
- **谁在用**：五类 RTOS 全通用。

### ST-LINK（V2/V3）
- **是什么**：ST 官方的板载/独立探针。🟠
- **能力**：SWD/JTAG/SWO；STM32 专用；V3 能力更强。
- **谁在用**：ST 平台的 FreeRTOS/ThreadX/RT-Thread/Zephyr。

### CMSIS-DAP / DAPLink
- **是什么**：`CMSIS-DAP` 是 Arm 定义的"USB→SWD/JTAG 桥"固件**规范**；`DAPLink` 是其开源实现。🟢(Apache-2.0)/⚪
- **能力**：低成本调试；DAPLink 还提供 U 盘拖拽烧录 + 虚拟串口。
- **谁在用**：FreeRTOS/RT-Thread/Zephyr/LiteOS 广泛。

### pyOCD
- **是什么**：Python 实现的 CMSIS-DAP 调试/烧录工具 + GDB Server。🟢（Apache-2.0）
- **能力**：脚本化烧录/调试，易入 CI；常与 west 配合。
- **谁在用**：Zephyr（runners）、FreeRTOS 等。

### OpenOCD
- **是什么**：开源片上调试器 + GDB Server + Flash 编程器。🟢（GPL-2.0）
- **能力**：适配大量探针（J-Link/ST-LINK/DAPLink/FTDI）；调试裸机/bootloader/内核早期；烧录。
- **谁在用**：五类 RTOS 全通用。

### GDB
- **是什么**：GNU 调试器。🟢（GPL-3.0）
- **能力**：源码级断点/单步/寄存器/内存；经 GDB Remote 协议对接 OpenOCD/pyOCD/J-Link GDB Server/模拟器。
- **谁在用**：五类 RTOS 全通用（几乎所有 IDE/调试链的后端）。

### SEGGER Ozone
- **是什么**：J-Link 配套的独立图形调试器。🟠（J-Link 用户免费）
- **能力**：图形化源码级调试 + RTOS 感知 + 指令跟踪视图。
- **谁在用**：FreeRTOS/RT-Thread/ThreadX/Zephyr/LiteOS。

### Lauterbach TRACE32
- **是什么**：高端硬件调试/跟踪平台。🟠
- **能力**：多核/多架构、ETM/PTM 流式 trace、启动早期调试；Linux/RTOS 双感知。
- **谁在用**：OpenVela（TERM/FDX）、高端 RTOS 项目。

---

## 4. 跟踪与性能调优

### SEGGER RTT（Real-Time Transfer）
- **是什么**：基于内存环形缓冲的实时双向 I/O 机制。🟢/🟠（需 J-Link）
- **能力**：不占用额外引脚，速度高于 SWO，实现"printf 级"实时输出与事件流；是 SystemView 的传输底座。
- **谁在用**：FreeRTOS/RT-Thread/ThreadX/Zephyr/OpenVela（Note 后端之一）。

### SEGGER SystemView
- **是什么**：基于 RTT 的 RTOS 运行时事件可视化工具。🟠（非商用免费）
- **能力**：任务切换/中断/API/定时器时间线，CPU 负载、多核同步，开销极小。
- **谁在用**：FreeRTOS/RT-Thread/ThreadX/Zephyr/OpenVela。

### Percepio Tracealyzer
- **是什么**：RTOS 运行时跟踪与可视化。🟠（含评估版；FreeRTOS 有免费版）
- **能力**：CPU 负载/堆栈/时序/事件级分析；覆盖 FreeRTOS/Zephyr/ThreadX 等。
- **谁在用**：FreeRTOS/RT-Thread/ThreadX/Zephyr。

### CMSIS Event Recorder + Component Viewer
- **是什么**：Arm CMSIS 的事件记录 API + 以 SCVD 描述可视化的组件。🟢（Apache-2.0）
- **能力**：记录 RTOS/中间件事件，在调试器里按 SCVD 展示内核对象。
- **谁在用**：FreeRTOS（CMSIS-Pack）、RTX/ThreadX、Zephyr。

### Perfetto
- **是什么**：Google 的系统级跟踪 + Web 可视化。🟢（Apache-2.0）
- **能力**：把 trace 事件流可视化为时间线；OpenVela/NuttX 的 `trace dump` 产物即导入 Perfetto 查看。
- **谁在用**：OpenVela（唯一，作为 note trace 可视化）。

### gprof
- **是什么**：GNU 函数级剖析器（`-pg` 插桩）。🟢（GPL）
- **能力**：Flat profile / 调用图。
- **谁在用**：OpenVela（`CONFIG_SYSTEM_GPROF`）、NuttX。

### perf
- **是什么**：性能事件子系统/CLI（源自 Linux，NuttX 有对应实现）。🟢（GPL-2.0）
- **能力**：基于 PMU/tracepoint 的采样剖析。
- **谁在用**：OpenVela（`perf record/stat` + FlameGraph）。

---

## 5. 测试与仿真

### Unity
- **是什么**：轻量 C 单元测试框架。🟢（MIT）
- **能力**：断言/用例组织，适合资源受限目标的单元测试。
- **谁在用**：FreeRTOS、RT-Thread（集成）、OpenVela（集成）、通用。

### CMock
- **是什么**：基于 Unity 的 mock 生成器。🟢（MIT）
- **能力**：自动生成被测代码依赖的桩/mock。
- **谁在用**：FreeRTOS、C 单元测试项目。

### Ceedling
- **是什么**：Unity + CMock 的构建/测试编排（Ruby）。🟢（MIT）
- **能力**：一条命令完成"单测构建→运行→报告"。
- **谁在用**：FreeRTOS 及通用 C 项目。

### GoogleTest（+ GoogleMock）
- **是什么**：C++ xUnit 测试框架。🟢（BSD-3）
- **能力**：C++ 单元测试与 mocking。
- **谁在用**：通用（主机侧/中间件测试）。

### pytest / pytest-embedded
- **是什么**：Python 测试框架 / 面向嵌入式真板的 pytest 插件。🟢（MIT / Apache-2.0）
- **能力**：脚本化测试；pytest-embedded 经串口驱动真板 HIL。
- **谁在用**：Zephyr（外部测试）、Espressif、OpenVela（tests/scripts）。

### Robot Framework
- **是什么**：关键字驱动测试自动化框架。🟢（Apache-2.0）
- **能力**：端到端/验收测试；常与 Renode/真板配合。
- **谁在用**：Zephyr、通用嵌入式。

### QEMU
- **是什么**：通用机器仿真/虚拟化。🟢（GPL-2.0）
- **能力**：指令级 CPU + 设备模型，可跑 Linux/RTOS；支持系统与用户态仿真。
- **谁在用**：Zephyr（native_sim/QEMU）、OpenVela（Vela Emulator）、通用无板回归。

### Renode
- **是什么**：Antmicro 的多节点系统仿真框架。🟢（MIT）
- **能力**：多节点、确定性虚拟时间；与 Robot Framework/CI 深度集成。
- **谁在用**：Zephyr、NuttX/OpenVela（NuttX 指南）、通用 CI。

### babbleSim
- **是什么**：无线链路级仿真（BLE 控制器测试）。🟢（Apache-2.0）
- **能力**：无需硬件即可测试蓝牙协议栈行为。
- **谁在用**：Zephyr（唯一）。

---

## 6. CI

### GitHub Actions
- **是什么**：GitHub 托管的事件驱动 CI。🟠/🟢（runner 客户端开源，公共仓免费）
- **能力**：按提交触发"编译—烧录/仿真—测试—报告"。
- **谁在用**：FreeRTOS、Zephyr、OpenVela（public-actions）、通用。

### GitLab CI/CD
- **是什么**：与 GitLab 一体化流水线。🟢(CE MIT)/🟠(EE)
- **谁在用**：通用（RT-Thread/各项目常配）。

### Jenkins
- **是什么**：可扩展的构建/流水线服务器。🟢（MIT）
- **能力**：复杂流水线编排，常作板级测试（设备农场）调度。
- **谁在用**：通用（嵌入式设备农场/回归）。

---

## 7. 安全启动 / OTA（通用件）

### MCUboot + `imgtool`
- **是什么**：通用安全 bootloader + 镜像签名工具。🟢（Apache-2.0）
- **能力**：镜像签名校验、A/B 升级、回滚；Zephyr/Nordic/NXP/Infineon 采用。
- **谁在用**：Zephyr（唯一核心）、ThreadX/FreeRTOS 可选。

### TF-M（Trusted Firmware-M）
- **是什么**：Arm 的安全启动/隔离固件（安全世界）。🟢（BSD-3）
- **能力**：安全启动、安全存储、TrustZone 隔离。
- **谁在用**：Zephyr（ARM 平台）。

### mcumgr
- **是什么**：Zephyr 的设备管理/DFU 协议实现。🟢（Apache-2.0）
- **能力**：经 BLE/UART/UDP 传输的镜像管理升级（SMP）。
- **谁在用**：Zephyr（+Nordic NCS）。

### CBMC / Coverity（验证工具）
- **是什么**：CBMC 是有界模型检查器（形式化验证）；Coverity 是商业静态分析。🟢/🟠
- **能力**：证明/发现内核级缺陷。
- **谁在用**：FreeRTOS（官方 CI 用 CBMC）。

---

# 第二部分　各 RTOS 专有工具

## 一、FreeRTOS 专有

### `FreeRTOSConfig.h`
- **是什么**：FreeRTOS 的**唯一集中配置头文件**。
- **能力**：以宏定义裁剪内核（调度算法、tick 频率、堆方案 heap_1~5、任务/队列上限、调试宏等）。
- **E2E 位置**：工程配置与代码生成。

### `vTaskGetRunTimeStats` / `uxTaskGetStackHighWaterMark`
- **是什么**：内核自带的运行统计 API。
- **能力**：前者统计各任务 CPU 占用；后者查询任务栈的**历史最小剩余**（高水位）。
- **E2E 位置**：跟踪与性能调优。

### AWS IoT OTA（`ota-for-aws-iot-embedded-sdk`）
- **是什么**：FreeRTOS/AWS 生态的固件 OTA 库。🟢（MIT）
- **能力**：与 AWS IoT Core 集成的作业式 OTA、设备影子、加密库。
- **E2E 位置**：维护与 OTA。

### AWS IoT Device Defender
- **是什么**：设备安全态势监控服务。🟠
- **能力**：上报指标/告警，检测异常行为。
- **E2E 位置**：维护（安全运维）。

### CMSIS-Pack（FreeRTOS 分发形态）
- **是什么**：以 `.pdsc` 描述的软件包，供 IDE 包管理器托管（202604 LTS）。⚪/🟢
- **能力**：开发者**在 IDE 内直接管理 FreeRTOS 依赖**，免手工集成。
- **E2E 位置**：配置/构建。

### FreeRTOS-Kernel 官方回归测试
- **是什么**：官方内核单元/覆盖率测试集。
- **能力**：验证内核与 port 正确性。
- **E2E 位置**：测试验证 / CI。

## 二、RT-Thread 专有

### Env（含 menuconfig + SCons + 包管理）
- **是什么**：RT-Thread 的命令行工具集（Windows 免装 Python/SCons，自带 ARM GCC）。🟢
- **能力**：Kconfig 图形裁剪、SCons 构建、pkgs 包下载管理。
- **E2E 位置**：配置/构建。

### RT-Thread Studio
- **是什么**：基于 Eclipse 的一体化 IDE。🔵（免费，宿主 Windows）
- **能力**：图形化工程创建/配置/编译/下载/调试。
- **E2E 位置**：配置/构建/烧录/调试。

### SCons + `--target` 工程导出
- **是什么**：RT-Thread 的构建系统及其**工程生成**能力。
- **能力**：`scons --target=mdk5/iar/vs2012` 一键生成主流 IDE 工程（**低门槛的关键**）。
- **E2E 位置**：构建。

### ulog
- **是什么**：RT-Thread 的分级日志组件。🟢
- **能力**：多级别、可后端的日志系统。
- **E2E 位置**：跟踪调优（日志）。

### utest
- **是什么**：RT-Thread 的统一测试框架。🟢
- **能力**：目标侧单元/集成测试。
- **E2E 位置**：测试验证。

### `ota_downloader` / `http_ota` / `ymodem_ota`
- **是什么**：RT-Thread 的分层 OTA 软件包。🟢
- **能力**：从 HTTP/Ymodem 等来源下载并升级固件。
- **E2E 位置**：维护与 OTA。

### 软件包平台（packages.rt-thread.org）
- **是什么**：RT-Thread 包生态（370+ 包）。
- **能力**：中间件/驱动/组件的可复用选型。
- **E2E 位置**：选型评估。

## 三、Zephyr 专有

### west（专有部分）
- **是什么**：Zephyr 元工具（见通用 §2，此处强调其专有子命令）。
- **能力**：`west init/update`、`west manifest`、`west build/flash/debug/sign`、`west twister`。
- **E2E 位置**：全流程。

### sysbuild
- **是什么**：Zephyr 的**多镜像统一构建**。🟢
- **能力**：一个命令构建 App + MCUboot + TF-M 等多镜像。
- **E2E 位置**：构建。

### Twister（`west twister`）
- **是什么**：Zephyr 官方测试运行器。🟢
- **能力**：扫描/构建/运行**测试矩阵**（QEMU/native_sim/真板），输出 JUnit/twister.json。
- **E2E 位置**：测试 / CI。

### ztest
- **是什么**：Zephyr 目标侧单元测试框架。🟢
- **能力**：在目标上组织并运行单测。
- **E2E 位置**：测试验证。

### Zephyr tracing（CTF）
- **是什么**：基于 CTF 格式的跟踪子系统。🟢
- **能力**：内核事件跟踪，供 Trace Compass/Perfetto 等分析。
- **E2E 位置**：跟踪调优。

### `ram_report` / `rom_report`
- **是什么**：Zephyr 构建产物静态分析。🟢
- **能力**：按段/符号统计 RAM、ROM 占用（裁剪与小型化依据）。
- **E2E 位置**：跟踪调优（资源分析）。

### Thread Analyzer
- **是什么**：Zephyr 运行期线程栈/CPU 统计。🟢
- **E2E 位置**：跟踪调优。

### native_sim
- **是什么**：Zephyr 把内核编译成**本机可执行**的仿真目标。🟢
- **能力**：无需硬件/仿真器即可跑测试。
- **E2E 位置**：测试 / CI。

### `west sign` + imgtool
- **是什么**：Zephyr 镜像签名入口 + MCUboot 签名工具。🟢
- **E2E 位置**：烧录/OTA。

## 四、ThreadX 专有

### `tx_user.h` + `tx_initialize_low_level`
- **是什么**：ThreadX 的配置头 + 端口底层初始化函数。
- **能力**：宏裁剪内核；初始化时钟/中断/内存等底层。
- **E2E 位置**：配置/代码生成。
- **备注**：ThreadX 以**源码集成**为主，无官方图形配置器。

### ThreadX 中间件套件（FileX / NetX Duo / USBX / GUIX）
- **是什么**：文件系统/网络(含安全)/USB/GUI 的成套中间件。🟢（MIT）
- **能力**：功能齐全，常与安全认证场景搭配。
- **E2E 位置**：选型/构建。

### TraceX
- **是什么**：ThreadX 事件记录与可视化工具。
- **能力**：记录内核事件缓冲并在主机端图形化分析。
- **E2E 位置**：跟踪调优。
- **状态**：分发/授权方式**待核实**。

### 原厂 SDK 集成（ST X-CUBE-AZRTOS / NXP / Renesas / Microchip）
- **是什么**：原厂把 ThreadX 打包进自家 SDK/IDE。🔵
- **能力**：图形配置 + 生成含 ThreadX 的工程。
- **E2E 位置**：配置/构建。

### CMake `add_subdirectory()`
- **是什么**：把 ThreadX 作为 CMake 子项目集成的方式。🟢
- **E2E 位置**：构建。

## 五、OpenVela 专有

### `repo` + manifests（`openvela.xml`）
- **是什么**：Google `repo` 多仓管理工具 + 官方清单。🟢
- **能力**：`repo init/sync` 拉取多仓源码与预编译工具链；是"官方支持矩阵"的来源。
- **E2E 位置**：选型/工程获取。

### `./build.sh`
- **是什么**：OpenVela 顶层编译入口（实为 `nuttx/tools/build.sh` 软链）。
- **能力**：内部执行 `configure.sh + make + savedefconfig`；`--cmake` 切 CMake+Ninja。
- **E2E 位置**：构建。
- **备注**：**无 `build.sh flash/debug` 子命令**（待核实项）。

### `tools/configure.sh`
- **是什么**：板级配置脚本。
- **能力**：拷贝板级 `Make.defs`、生成 `.config`。
- **E2E 位置**：配置。

### `vendor_template`（chips/boards 骨架）
- **是什么**：新平台 BSP 模板仓。
- **能力**：快速起一个 `chips/<chip>` + `boards/<chip>/<board>` 移植骨架。
- **E2E 位置**：配置/移植。

### `kconfig-frontends` / `kconfig-conf` / `kconfig-tweak`
- **是什么**：Kconfig 解析与图形配置前端。🟢
- **能力**：`menuconfig` 交互配置。
- **E2E 位置**：配置。

### `genromfs` + `xxd`（`mkromfs.sh`）
- **是什么**：生成 `/etc` ROMFS 镜像并嵌入固件。
- **能力**：把启动脚本 `rcS`、密钥等打包进 `/etc`。
- **E2E 位置**：构建。

### 预编译工具链（`prebuilts_*`）
- **是什么**：官方预编译交叉工具链分支。
- **能力**：arm-none-eabi / aarch64-none-elf / riscv-none-elf / xtensa-esp32s3-elf / tricore-elf。
- **E2E 位置**：构建。

### `ccache` / `bear`
- **是什么**：编译缓存加速 / 生成 `compile_commands.json`（供 clangd/IDE）。🟢
- **E2E 位置**：构建。

### `make flash` + `esptool`（ESP32-S3）
- **是什么**：NuttX flash 目标 + Espressif 串口烧录工具。🟢
- **E2E 位置**：烧录。

### 厂商烧录器（`STM32CubeProgrammer` / `JLinkExe`+`loadfile` / `AURIXFlasher.exe`）
- **是什么**：ST / SEGGER / 英飞凌的烧录工具。🔵/🟠
- **能力**：分别用于 STM32、J-Link SWD、英飞凌 TC4x 多核镜像烧录。
- **E2E 位置**：烧录。

### `minicom`
- **是什么**：串口终端。🟢
- **能力**：烧录后连接串口确认启动。
- **E2E 位置**：烧录验证。

### `gdb-multiarch` / `arm-none-eabi-gdb`
- **是什么**：跨架构 GDB 客户端。
- **能力**：`target remote` 连 OpenOCD/J-Link GDB Server/模拟器 gdbstub。
- **E2E 位置**：在线调试。

### Vela Emulator（`emulator.sh vela -qemu -S -s`）
- **是什么**：OpenVela 的 QEMU（goldfish）模拟器。
- **能力**：内置 gdbstub，无硬件即可做"JTAG 式"调试。
- **E2E 位置**：调试/仿真。

### `JLinkGDBServer` + `jlink-nuttx.so`
- **是什么**：J-Link GDB Server + NuttX RTOS 感知插件。
- **能力**：让 GDB 支持 `info threads`、线程切换。
- **E2E 位置**：在线调试。

### GDB Plugin（`pynuttx/gdbinit.py`）
- **是什么**：NuttX/OpenVela 的 GDB **Python 插件**。
- **能力**：系统语义级命令——`info nxthreads`、`memdump/memleak/memfrag/kasan`、`rpmsgdump`、`uorb`、`netstats`、`ps`、`deadlock`、`crash busyloop`、`note/notedump`、`nxgcore`。
- **E2E 位置**：在线调试（系统级）。

### GDB Stub（`CONFIG_LIB_GDBSTUB`）
- **是什么**：目标侧 GDB 桩。
- **能力**：无硬件探针时经 UART/USB/网络做寄存器/内存/断点级调试；Crash 后自动接入。
- **E2E 位置**：在线调试。

### `trace` / `sched_note` / ATRACE / Note 后端
- **是什么**：基于 `sched_note` 的内核打点与 `trace start/dump` 命令；ATRACE 为应用埋点宏；Note 后端含 RAM/Syslog/RTT/SysView/RPMsg/ITM。
- **能力**：记录任务/中断/系统调用/锁事件，导出后可视化。
- **E2E 位置**：跟踪调优。

### `traceparse.py` → Perfetto
- **是什么**：把 note trace 解析为 Perfetto 格式的脚本。
- **E2E 位置**：跟踪调优。

### `perf` + `perfaddmmap.py` + FlameGraph
- **是什么**：NuttX/OpenVela 的 PMU 采样剖析链。
- **能力**：`perf record` 采集 → 主机 `perf report` + 火焰图。
- **E2E 位置**：跟踪调优。

### `gprof`（OpenVela 侧）
- **是什么**：`CONFIG_SYSTEM_GPROF` 的 `gprof start/stop/dump` + 主机 `arm-none-eabi-gprof`。
- **E2E 位置**：跟踪调优。

### `cpuload` / `top` / `ps`
- **是什么**：线程级 CPU 占用统计与进程/线程查看。
- **E2E 位置**：跟踪调优。

### `critmon`（临界区监控）
- **是什么**：`CONFIG_SCHED_CRITMONITOR` 的关中断/关调度临界区监控。
- **能力**：统计最长临界区与线程运行时间，识别实时性风险。
- **E2E 位置**：跟踪调优。

### `irqinfo`（中断监控）
- **是什么**：`CONFIG_SCHED_IRQMONITOR` 的中断统计。
- **能力**：中断频次/单次最大执行时间，识别中断风暴。
- **E2E 位置**：跟踪调优。

### `showinfo`
- **是什么**：`CONFIG_LOW_RESOURCE_TEST` 的资源监控命令。
- **能力**：CPU/内存/文件系统资源监控并可落盘。
- **E2E 位置**：跟踪调优。

### 基准测试（CoreMark / Dhrystone / Whetstone / CacheSpeed / RAMSpeed）
- **是什么**：硬件性能基线测试集。
- **E2E 位置**：跟踪调优（性能基线）。

### `open-vela/tests`（testcases / testsuites）
- **是什么**：官方测试用例集。
- **能力**：异常/文件/图形/多媒体/调度/SMP/uORB/KV/安全/Flash 等。
- **E2E 位置**：测试验证。

### CMocka（`CONFIG_TESTING_CMOCKA`）
- **是什么**：C 单元测试框架（OpenVela 采用）。
- **能力**：`cmocka -l` 列用例、`cmocka -t` 运行；驱动侧 `cmocka_driver_block`。
- **E2E 位置**：测试验证。

### `fstest` / `memstress` / `opus_ramtest`
- **是什么**：文件系统/内存/PSRAM 压力测试工具。
- **E2E 位置**：测试验证。

### tests 的 `scripts/`（pytest + pexpect + minicom）
- **是什么**：自动化真板测试脚本。
- **能力**：`pytest test_*.py -D /dev/ttyUSBx -B <board> ...`，并生成报告。
- **E2E 位置**：测试 / CI。

### XTS 精简用例集（`openvela_xts_test_cases`）
- **是什么**：厂商准入/自测标准用例（通用必测 + 品类选测）。
- **E2E 位置**：测试验证。

### Allsyms + backtrace + `pyelftools`/`cxxfilt`
- **是什么**：符号表生成与堆栈符号化。
- **能力**：测试/Crash 后把地址还原为函数/行号。
- **E2E 位置**：调试/测试。

### `public-actions`
- **是什么**：官方可复用 GitHub Actions 集合。
- **能力**：`checkpatch`/`cla`/`ci`/`docs`/`stale` 等统一门禁；水印/中文检测。
- **E2E 位置**：自动化 CI。

### `tests/cibuild.sh`
- **是什么**：CI 内构建依赖准备脚本。
- **能力**：准备 gen-romfs/gperf/kconfig-frontends/各架构 gcc/ccache。
- **E2E 位置**：CI。

### `nxstyle` / `cmake-format` / `config_check`
- **是什么**：风格/格式/配置检查工具。
- **E2E 位置**：CI。

### `frameworks/system/ota` → `bootctl`
- **是什么**：A/B 分区升级管理。
- **能力**：`bootctl success/update/done`；KVDB 记录 slot A/B 的 active/bootable/successful，bootloader 自动选分区与回滚。
- **E2E 位置**：维护与 OTA。

### `gen_ota_zip.py`
- **是什么**：OTA 包生成脚本。
- **能力**：`new --sign`（全包）/ `old new --sign`（差分），支持用户脚本。
- **E2E 位置**：OTA。

### `ddelta`
- **是什么**：差分升级算法依赖。
- **E2E 位置**：OTA。

### `otaUI`
- **是什么**：OTA 升级动画/进度 UI（依赖 framebuffer）。
- **E2E 位置**：OTA。

### `avb_verify` / `zip_verify` + `avb_sign.sh`
- **是什么**：AVB/包签名校验与签名工具。
- **能力**：镜像/包签名与启动校验（防回滚）。
- **E2E 位置**：OTA/安全。

### 升级包投递（Ymodem/Zmodem、`adb push`、`curl`）
- **是什么**：把 OTA 包传到设备（串口/ADB/网络）。
- **E2E 位置**：OTA。

### 日志/异常维护（`crashlog` / `coredump` / `nxgcore` / `resetcause` / `dmesg` / ramlog）
- **是什么**：Crash 日志、内核 core dump、复位原因、日志缓冲。
- **E2E 位置**：维护。

### 异构/多核（Rptun / RPMsg / VirtIO / OpenAMP）
- **是什么**：AMP 多核通信与生命周期管理。
- **能力**：`/dev/rptun/<cpuname>`、`rptun start|stop|boot|poweroff|reset|panic`；多核镜像 `cmake_out/<board>_coreN`。
- **E2E 位置**：调试/维护（多核）。

### `micumgr`/`microADB`（ADB 支持）
- **是什么**：OpenVela 的 ADB 支持（`apps_system_adb`）。
- **能力**：`adb push` 等调试/投递（非所有板卡默认启用）。
- **E2E 位置**：调试/维护。

---

# 第三部分　交叉索引（工具 → RTOS → 节点）

| 工具 | 使用它的 RTOS | E2E 节点 |
|---|---|---|
| Arm GNU Toolchain / gcc | 五类全用 | 构建 |
| Keil MDK / armclang | FreeRTOS、ThreadX（+LiteOS 目标） | 构建、调试 |
| IAR EW / C-SPY | FreeRTOS、ThreadX | 构建、调试、调优 |
| Zephyr SDK | Zephyr | 构建、调试 |
| TI Arm Clang | 原厂 SDK(FreeRTOS/ThreadX) | 构建 |
| CMake / Ninja | Zephyr、ThreadX、OpenVela | 构建 |
| Kconfig / menuconfig | Zephyr、RT-Thread、OpenVela、LiteOS | 配置 |
| Device Tree / dtc | Zephyr（+LiteOS-A） | 配置 |
| SCons | RT-Thread | 构建、工程导出 |
| west | Zephyr | 全流程 |
| Make / Makefile | OpenVela、LiteOS | 构建 |
| J-Link / ST-LINK / CMSIS-DAP | 五类全用 | 烧录、调试 |
| pyOCD | Zephyr、通用 | 烧录、调试 |
| OpenOCD | 五类全用 | 烧录、调试 |
| GDB | 五类全用 | 调试 |
| Ozone | 五类全用 | 调试 |
| TRACE32 | OpenVela、高端项目 | 调试、跟踪 |
| RTT | 五类全用 | 跟踪 |
| SystemView | 五类全用 | 跟踪 |
| Tracealyzer | FreeRTOS、RT-Thread、ThreadX、Zephyr | 跟踪 |
| Event Recorder | FreeRTOS、ThreadX、Zephyr | 跟踪 |
| Perfetto | OpenVela | 跟踪 |
| gprof / perf | OpenVela | 跟踪 |
| Unity / CMock / Ceedling | FreeRTOS、RT-Thread、OpenVela、通用 | 测试 |
| GoogleTest | 通用 | 测试 |
| pytest / pytest-embedded | Zephyr、OpenVela、Espressif | 测试、CI |
| Robot Framework | Zephyr、通用 | 测试 |
| QEMU | Zephyr、OpenVela、通用 | 测试、调试 |
| Renode | Zephyr、OpenVela(NuttX)、通用 | 测试、CI |
| babbleSim | Zephyr | 测试 |
| GitHub Actions | FreeRTOS、Zephyr、OpenVela、通用 | CI |
| GitLab CI / Jenkins | 通用 | CI |
| MCUboot | Zephyr（+FreeRTOS 可选） | OTA |
| TF-M | Zephyr | OTA/安全 |
| mcumgr | Zephyr | OTA |
| CBMC / Coverity | FreeRTOS、通用 | 测试/CI |
| AWS IoT OTA / Device Defender | FreeRTOS | OTA/维护 |
| Env / Studio | RT-Thread | 配置/构建/调试 |
| ulog / utest / ota_downloader | RT-Thread | 调优/测试/OTA |
| Twister / ztest / sysbuild / CTF / ram·rom_report | Zephyr | 测试/构建/调优 |
| tx_user.h / TraceX / FileX·NetX·USBX·GUIX | ThreadX | 配置/调优/选型 |
| repo / build.sh / vendor_template / pynuttx / bootctl / gen_ota_zip | OpenVela | 全流程/OTA |

---

## 附录：待核实

1. **ThreadX TraceX** 当前分发/授权方式。
2. **OpenVela**：`build.sh flash/debug` 不存在；无专属 `vlog`；`vela-linux`（与 Linux 的 RPC）未见官方仓。
3. 各原厂 IDE 精确宿主 OS 组合、部分工具许可证随版本变化，采用前请核对官方最新文档与 EULA。
4. 表中"谁在用"为工程实践归纳，非官方兼容性声明。

> **免责声明**：本文为工具知识参考，能力与许可随版本变化。
