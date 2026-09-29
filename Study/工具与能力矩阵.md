
# RTOS 与嵌入式 Linux 工具与能力矩阵

> **定位**：本文是《调研汇总.md》的**矩阵视图**——只放"结果"（矩阵 + 事实型判定），逐格证据与 178 个工具的详情（介绍/核心能力/作用三段式）见《调研汇总.md》及其附三核查记录，两者交叉引用。
>
> **口径说明**：
> - 对象：FreeRTOS / RT-Thread / Zephyr / ThreadX / OpenVela（5 家 RTOS）+ 嵌入式 Linux（参照系）。
> - 判定图例（事实型，非主观打分）：**✅** = 官方完备支持（有官方文档/仓库级证据）；**⚠️** = 部分支持 / 社区实践 / 受限；**❌** = 缺失或无官方支持；**❓** = 未能从一手来源确认。
> - **⭐ 通用工具标注**：该工具跨多家 OS 生态通用（≥3 家 RTOS 或 RTOS+Linux 通用），其支持面见第三章矩阵 B。
> - 数据快照：2026-09（全部判定基于官方一手来源核实：官方文档页、仓库源码/LICENSE、厂商产品页；核查方法见附录 D）。

---

## 一、E2E 总览矩阵（九阶段 × 六家，⭐ = 跨生态通用工具）

| E2E 阶段 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela | 嵌入式Linux |
|---|---|---|---|---|---|---|
| ① 选型评估 | Supported Devices | BSP 列表、软件包平台 | `west boards` | 内核 + 中间件套件（认证清单） | `repo` + manifests | 主线 SoC DTS、Bootlin Elixir、OE Layer Index |
| ② 配置与代码生成 | `FreeRTOSConfig.h`、STM32CubeMX | Env 工具集、RT-Thread Studio | Kconfig、Devicetree、`west manifest` | `tx_user.h`、原厂 SDK 集成 | Kconfig、`vendor_template` | DTC、内核 Kconfig、BitBake + OE metadata |
| ③ 编译构建 | ⭐Arm GNU Toolchain | SCons | ⭐CMake + Ninja + Zephyr SDK | ⭐CMake `add_subdirectory()` | `./build.sh` | Yocto/BitBake、Buildroot、Kbuild、厂商 BSP |
| ④ 烧录下载 | ⭐J-Link/OpenOCD、STM32CubeProgrammer | RT-Thread Studio 下载 | `west flash` | ⭐探针（J-Link/OpenOCD）/ 原厂烧录工具 | `make flash` + esptool | `uuu`/`rkdeveloptool`、`fastboot`/`dfu-util`、`bmaptool` |
| ⑤ 在线调试 | ⭐GDB + OpenOCD、内核感知插件 | Studio 集成 GDB | `west debug` + ⭐GDB | 原厂 IDE 调试 + RTOS 感知 | ⭐GDB + `pynuttx` 插件 | 串口/earlycon、⭐GDB/GDBServer、KGDB、⭐OpenOCD |
| ⑥ 跟踪与调优 | 运行统计 API、⭐Tracealyzer、⭐SystemView | ulog | tracing（CTF 可选）、⭐SystemView/⭐Tracealyzer | TraceX | `trace`→Perfetto、critmon/irqinfo | ftrace、perf、eBPF/bpftrace |
| ⑦ 测试验证 | ⭐Unity + CMock + Ceedling、CBMC | utest | Twister、ztest | 官方回归测试 + ⭐通用框架 | open-vela/tests、xTS 用例精简集 | LTP、kselftest/KUnit、LAVA、⭐QEMU/Renode |
| ⑧ 自动化 CI | ⭐GitHub Actions | 通用 CI + SCons | ⭐GitHub Actions + Twister、Docker 镜像 | 通用 CI（⭐GitHub Actions） | `public-actions` | Jenkins/GitLab CI/⭐GitHub Actions、LAVA、KernelCI |
| ⑨ 维护与 OTA | coreOTA、⭐MCUboot | ota_downloader + FAL/ota_packager | ⭐MCUboot + imgtool、mcumgr | 原厂 bootloader / 安全启动 | `bootctl`、`gen_ota_zip.py` + AVB | SWUpdate、RAUC、Mender、A/B + U-Boot 回退 |

> 工具详情（178 条三段式条目）见《调研汇总.md》对应章节；重要工具以加粗标注。

---

## 二、横切维度 A：开发环境（IDE）支持矩阵

> 这是《调研汇总》此前缺失的维度：同一个 IDE，在各 RTOS 上的官方支持程度。

### 2.1 主矩阵

| 开发环境 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela | 嵌入式Linux |
|---|---|---|---|---|---|---|
| **VS Code（官方指南/工程支持）** | ❌ 无官方指南与扩展（组织 44 仓实证无 IDE 仓）；⚠️ 经 ⭐CMSIS-Pack + 通用工具链可用 | ⚠️ `scons --target=vsc` 生成 VS Code 配置；官方扩展仅 MicroPython 插件（64.7K 安装）与 Smart Helper（4K），非全流程 | ✅ **最强**：官方 "Tools and IDEs" 专章 + **IDE for Zephyr** 扩展（build/flash/debug/Kconfig 编辑/Twister 面板/内存旭日图）+ **nRF Connect for VS Code**（RTOS-aware 调试、DeviceTree 可视化编辑、建板向导） | ❌ 无官方 VS Code 指南 | ⚠️ 官方 `VSCODE_debugging.md` **仅覆盖 sim 仿真环境**（C/C++ 扩展 cppdbg）；真机走 GDB/J-Link 文档 | ✅ Remote-SSH / Dev Containers 通行 |
| **VS Code + ⭐cortex-debug（RTOS 线程视图）** | ✅ 感知可用（OpenOCD/pyOCD/J-Link 均支持 FreeRTOS） | ⚠️ 基础调试可用；**无 RTOS 感知**（OpenOCD/J-Link 主线均不支持 RT-Thread） | ✅（OpenOCD 支持 zephyr；IDE for Zephyr 内建集成） | ✅（OpenOCD 支持 threadx） | ✅（OpenOCD 支持 nuttx；另有 jlink-nuttx.so 插件） | ❌ 不适用（AP 场景主通道是 gdbserver） |
| **Keil MDK（µVision / Keil Studio）** | ✅ 官方 CMSIS-Pack 分发（202604.00-LTS 已提供 .pack） | ✅ `scons --target=mdk5` 一键生成工程 | ❌ 官方文档无 Keil 集成路径（工具链为 Zephyr SDK GCC/LLVM） | ✅ 原厂 SDK 提供（IAR/Keil/MPLAB X 等编译器组合） | ❌ 无 Keil 工程（GCC 工具链 + Make/CMake） | ❌ |
| **IAR Embedded Workbench** | ✅ port 官方支持 ICCARM；IAR 列 FreeRTOS 为生态伙伴 | ✅ `scons --target=iar` | ⚠️ IAR 官网列 Zephyr 为生态伙伴，但工具链支持未见于 Zephyr 官方 toolchains 文档 | ✅ 原厂 SDK 提供 | ❌ | ❌（IAR Build Tools 面向 MCU） |
| **Eclipse 系** | ⚠️ CDT + GNU 工具链（社区实践）；✅ 经原厂 IDE（CubeIDE/MCUXpresso 等） | ✅ **RT-Thread Studio**（Eclipse 深度定制，Windows，社区版永久免费） | ⚠️ 官方文档含 **STM32CubeIDE** 专章（原厂承载） | ✅ Renesas e² studio/Smart Configurator、Microchip MPLAB Harmony | ❌ | ⚠️ Eclipse CDT 传统可选 |
| **CLion（JetBrains）** | ⚠️ 经 OpenOCD/GDB 通用可行 | ⚠️ 同左 | ✅ 官方文档专章 | ⚠️ 同左 | ⚠️ 同左 | ⚠️ 远程模式可用 |
| **原厂 IDE（CubeIDE/MCUXpresso/CCS/e² studio/ModusToolbox）** | ✅ 各原厂工程模板内置 FreeRTOS 选项 | ⚠️ 无原厂深度集成，通用 GCC 工程可用 | ⚠️ CubeIDE 有官方章节；NXP 转推 Zephyr | ✅ ST/Renesas/Microchip 仍在提供（**NXP 已于 MCUXpresso SDK 2.15 后停止**） | ❌ | ❌（不适用） |
| **宿主 OS：Windows 原生开发** | ✅ 随原厂 IDE / ⭐Arm GNU Toolchain（Win 版） | ✅ Env 自带 Python/SCons/ARM GCC + Studio | ✅ 官方 Windows 原生（Getting Started 含 winget 流程，WSL 仅替代） | ✅ 随原厂 SDK | ⚠️ manifest 含 windows 宿主工具链变体，但官方文档/CI 主线为 Linux | ❌（发行版构建本质要求 Linux 宿主） |

### 2.2 一句话结论

- **"无自研 IDE、走通用工具"是主流**：FreeRTOS（CMSIS-Pack 分发）、Zephyr（VS Code 生态最厚）、ThreadX（原厂 SDK 承载）均不自研 IDE；唯一例外是 RT-Thread Studio（Eclipse 定制）。
- **VS Code 支持梯度**：Zephyr（官方扩展双雄）＞ FreeRTOS/OpenVela（通用可行/仅 sim 文档）＞ RT-Thread（配置生成 + 垂直扩展）＞ ThreadX（无官方路径）。
- **RTOS 感知的分水岭在工具链而非 IDE**：cortex-debug/Ozone/J-Link/OpenOCD 都做"感知"，但感知清单各不相同——RT-Thread 是唯一在 OpenOCD/J-Link/SystemView/Tracealyzer 四家官方清单上**全部缺席**的主流 RTOS（详见矩阵 B）。

---

## 三、横切维度 B：通用工具 × RTOS 支持矩阵

> 同一工具对各家 RTOS 的**官方支持面**（✅ 官方支持 / ⚠️ 社区·间接·部分 / ❌ 不支持 / ❓ 未证实）。这是第一章 ⭐ 标注的依据。

| 通用工具 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela(NuttX) | Linux | 依据（附录 B 展开） |
|---|---|---|---|---|---|---|---|
| **⭐OpenOCD**（RTOS 感知） | ✅ | ❌（主线 `rtos_types` 无 rt-thread） | ✅ | ✅ | ✅（nuttx） | ✅ | 源码 rtos.c 实证 |
| **⭐SEGGER J-Link**（GDB Server RTOS 感知） | ✅ | ❌ | ✅ | ✅ | ✅（jlink-nuttx.so 插件） | ❌（MCU 探针不适用） | SEGGER 官方页 |
| **⭐SEGGER Ozone**（RTOS 感知） | ✅ | ❌ | ✅ | ✅ | ✅（另含 embOS/ChibiOS/NuttX） | ❌ | SEGGER 官方页 |
| **⭐SEGGER SystemView** | ✅（V8–V11，V11 起原生） | ❌（官方支持列表无；社区移植实践存在） | ✅（2019 起集成进 tracing） | ✅（6.4 起插桩） | ✅（经 SEGGER RTT Drivers） | ❌ | SEGGER 官方页 |
| **⭐Percepio Tracealyzer** | ✅（免费版名为 Percepio View） | ❌（官方支持列表无） | ✅ | ✅ | ❌（列表无 nuttx） | ✅（含 VxWorks/PX5/SafeRTOS 等） | Percepio 官方页 |
| **⭐cortex-debug**（VS Code 扩展，感知随 GDB Server） | ✅ | ⚠️（基础调试可，无感知） | ✅ | ✅ | ✅ | ❓（非典型场景） | 扩展 README |
| **⭐MCUboot**（安全 bootloader） | ⚠️（可选/Lab 项目） | ⚠️（社区包移植） | ✅（第一官方集成） | ❌ | ❌（自有 bootctl + AVB） | ❌（用 U-Boot Verified Boot） | mcuboot 仓库 |
| **⭐Arm GNU Toolchain / GDB / CMake** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 全生态默认底座 |

> **结构性发现**：通用工具的 RTOS 支持面呈"4+1+1"格局——FreeRTOS/Zephyr/ThreadX/NuttX 四家在探针与 trace 工具上全绿；RT-Thread 在所有第三方感知/可视化工具上缺席，其 RTOS 感知只能靠自家的 RT-Thread Studio；嵌入式 Linux 走另一条工具线（ftrace/perf/eBPF），仅与 RTOS 共享物理层（探针/功耗仪，见《调研汇总》附一）。

---

## 四、各阶段优劣对比（事实型判定）

> 每格判定均给出可核查的事实依据（缩写见附录 C 证据清单）。

### ① 选型评估

| 对比项 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela | Linux |
|---|---|---|---|---|---|---|
| 支持矩阵可查性 | ✅ Supported Devices 网页 | ⚠️ README 数字滞后（官方 CI 实为 362 BSP） | ✅ `west boards` 一条命令 | ⚠️ 仅 ports/ 目录，无网页检索 | ✅ manifest 即权威清单 | ✅ 主线 DTS + Layer Index |
| 生态数据披露 | ⚠️ 无下载量类数据 | ✅ 875 包 / 1856 万下载（官方 API） | ⚠️ 无等价披露 | ❌ | ⚠️ | ⚠️ |
| 安全认证 | ⚠️ LTS + 安全流程 | ❌ | ⚠️ Safety 工作组 | ✅ **TÜV/UL/EAL4+/FIPS 最全** | ✅ xTS 产业认证 | ⚠️（SIL2 Linux 等项目） |

### ② 工程配置与代码生成

| 对比项 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela | Linux |
|---|---|---|---|---|---|---|
| 图形配置器 | ⚠️ 借原厂（CubeMX 等） | ✅ Studio + Env 双形态 | ⚠️ guiconfig + nRF Connect 的 Kconfig/DTS GUI | ⚠️ 借原厂 | ⚠️ menuconfig 终端 | ⚠️ menuconfig |
| IDE 工程导出 | ⚠️ CMSIS-Pack（限 Keil 系） | ✅ **`scons --target` 独有优势**（mdk5/iar/vsc 等） | ❌ 无（靠 CMake/west 生态） | ❌ 无 | ❌ 无 | ❌（发行版构建不适用） |
| 声明式硬件描述 | ❌（生成 C 代码） | ❌（板级头文件） | ✅ **Devicetree**（一份内核适配多板） | ❌ | ❌ | ✅ DT |

### ③ 编译构建

| 对比项 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela | Linux |
|---|---|---|---|---|---|---|
| Windows 原生构建 | ✅ 随原厂 IDE/GCC | ✅ **Env 自带工具链** | ✅ 官方原生（winget） | ✅ 随原厂 SDK | ⚠️ 有 win 变体、主线 Linux | ❌ 本质要求 Linux 宿主 |
| 构建系统工业化 | ⚠️ 无自有构建系统 | ✅ SCons | ✅ **west + CMake + Ninja + SDK 标杆** | ⚠️ CMake 子项目 | ✅ build.sh + Make/CMake + prebuilts | ✅ Yocto/Buildroot |
| 版本锁定可复现 | ⚠️ LTS tag | ⚠️ pkgs 版本 | ✅ west manifest | ⚠️ git submodule | ✅ repo manifest | ✅ kas/manifest |

### ④ 烧录下载

| 对比项 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela | Linux |
|---|---|---|---|---|---|---|
| CLI/脚本化烧录 | ✅ 探针生态（OpenOCD/pyOCD） | ⚠️ Studio 图形为主，无统一 CLI 入口 | ✅ **`west flash` runner 抽象** | ✅ 同探针生态 | ⚠️ make flash（板级）+ 厂商工具 | ✅ uuu/fastboot/bmaptool 全 CLI |
| 镜像签名 | ⚠️ MCUboot 可选 | ⚠️ ota_packager .rbl 校验 | ✅ `west sign` + imgtool | ❌ | ✅ AVB | ✅ U-Boot Verified Boot |

### ⑤ 在线调试

| 对比项 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela | Linux |
|---|---|---|---|---|---|---|
| VS Code 调试 | ⚠️ cortex-debug 通用 | ⚠️ Studio GDB / vsc 配置 | ✅ **双官方扩展**（IDE for Zephyr / nRF Connect） | ⚠️ 原厂 IDE | ⚠️ 仅 sim 官方文档 | ✅ Remote 通行 |
| RTOS 感知覆盖面（矩阵 B） | ✅ 全绿 | ❌ **仅自家 Studio** | ✅ 全绿 | ✅ 全绿 | ✅ 全绿 | ✅ |
| 系统语义级调试深度 | ⚠️ 感知视图 | ⚠️ | ⚠️ | ⚠️ | ✅ **pynuttx 命令集独一档**（memleak/deadlock/nxgcore…） | ✅ crash/drgn/eBPF 最全 |

### ⑥ 跟踪与性能调优

| 对比项 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela | Linux |
|---|---|---|---|---|---|---|
| 内核自带统计 | ✅ 运行统计 API | ⚠️ | ✅ Thread Analyzer | ⚠️ | ✅ cpuload/critmon/irqinfo | ✅ 最全 |
| 标准格式/生态出口 | ✅ Tracealyzer/SystemView 原生 | ❌ **无标准出口**（社区 SystemView 移植） | ✅ CTF + SystemView/Tracealyzer | ✅ TraceX 官方（已开源） | ✅ **traceparse → Perfetto** | ✅ CTF/Perfetto |
| 函数级剖析（perf/gprof） | ❌ | ❌ | ❌ | ❌ | ✅（perf + gprof） | ✅ |
| 差异化亮点 | CBMC 形式化（⑦） | — | ram/rom_report 量化 | TraceX 免费开源 | sched_note 六后端 | eBPF 可编程观测 |

### ⑦ 测试验证

| 对比项 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela | Linux |
|---|---|---|---|---|---|---|
| 目标侧单测框架 | ⚠️ 借 ⭐Unity/CMock | ✅ utest | ✅ ztest | ⚠️ 仅内部回归 | ✅ CMocka | ✅ KUnit |
| 测试编排器 | ⚠️ 官方 CI 内部 | ❌ | ✅ **Twister（六家最强）** | ❌ | ⚠️ pytest 脚本 | ✅ LAVA/KernelCI |
| 形式化验证 | ✅ **CBMC 进官方 CI（唯一）** | ❌ | ❌ | ❌ | ❌ | ❌ |
| 无板仿真 | ⚠️ POSIX port | ⚠️ QEMU BSP | ✅ QEMU/native_sim/babbleSim | ⚠️ win32/linux 端口 | ✅ Vela Emulator | ✅ QEMU |
| 认证测试体系 | ❌ | ❌ | ❌ | ⚠️（内核自认证） | ✅ **xTS 产业准入** | ❌ |

### ⑧ 自动化 CI

| 对比项 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela | Linux |
|---|---|---|---|---|---|---|
| 官方 Docker 镜像 | ❌ | ❌ | ✅ | ❌ | ❌ | ✅（Yocto） |
| 上游 CI 强度 | ✅ CBMC + 内核回归 | ⚠️ 通用 CI 多板编译 | ✅ **Twister 全量矩阵** | ⚠️ 通用 CI | ✅ public-actions 统一门禁 | ✅ **KernelCI/LAVA 公共设施** |

### ⑨ 维护与 OTA

| 对比项 | FreeRTOS | RT-Thread | Zephyr | ThreadX | OpenVela | Linux |
|---|---|---|---|---|---|---|
| A/B + 签名 + 回滚三件套 | ⚠️ MCUboot 可选 + coreOTA 云侧 | ⚠️ FAL + ota_packager，双分区靠社区包 | ✅ **MCUboot 参考实现** | ❌ 无官方 | ✅ **bootctl + AVB + KVDB** | ✅ SWUpdate/RAUC/Mender |
| 差分升级 | ⚠️ | ⚠️ | ⚠️ | ❌ | ✅ **ddelta（六家 RTOS 唯一官方差分）** | ✅（SWUpdate/Mender Ent.） |
| 云端配套 | ✅ **AWS 全链（coreOTA + Device Defender）** | ⚠️ | ⚠️ mcumgr 本地 + 第三方云 | ❌ | ⚠️ | ✅ Mender/balena |

### 4.10 九阶段热力总表

| | ① | ② | ③ | ④ | ⑤ | ⑥ | ⑦ | ⑧ | ⑨ |
|---|---|---|---|---|---|---|---|---|---|
| **FreeRTOS** | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| **RT-Thread** | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ❌ | ⚠️ | ⚠️ | ⚠️ |
| **Zephyr** | ✅ | ✅ | ✅✅ | ✅ | ✅ | ✅ | ✅✅ | ✅✅ | ✅ |
| **ThreadX** | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ❌ |
| **OpenVela** | ✅ | ✅ | ✅ | ⚠️ | ✅✅ | ✅✅ | ✅ | ✅ | ✅✅ |
| **Linux（参照）** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅✅ | ✅ |

> **读法**：✅✅ = 该阶段的标杆；❌ = 结构性短板。三家画像——**Zephyr：工程化全优（②③⑦⑧ 标杆）**；**OpenVela：调试观测与 OTA 双标杆（⑤⑥⑨）**；**FreeRTOS：通用生态红利（④⑤⑥）+ CBMC 独有（⑦）**；**RT-Thread：上手门槛最低（②③ Windows 顺滑）但 ⑥ 无标准出口**；**ThreadX：认证资产独厚（①）但工具链全面依赖原厂（⑨ 垫底）**。

---

## 附录 A：IDE 矩阵证据展开

| 格 | 关键事实 | 一手依据 |
|---|---|---|
| Zephyr × VS Code | 官方文档有 "Tools and IDEs" 专章，含 VS Code、**IDE for Zephyr（VS Code extension）**、STM32CubeIDE、CLion 章节；IDE for Zephyr（mylonics，官方文档收录）支持宿主工具管理、west workspace、SDK 管理、build/flash、调试（`zephyr-ide-west`/`zephyr-ide-cortex` 转 Cortex-Debug 会话）、Kconfig 交互编辑、Twister 面板、RAM/ROM 旭日图，Win/Linux/macOS；配置存 `.vscode/zephyr-ide.json` 可入库 | docs.zephyrproject.org/latest/develop/tools/index.html 及 ide_for_zephyr_vscode_ext.html |
| Nordic × VS Code | nRF Connect for VS Code 扩展包把 VS Code 变成完整 IDE：编译/链接接口、**RTOS-aware 调试器**、DeviceTree 可视化编辑器、Create New Board 向导、集成串口终端，CLI+GUI 双形态，nRF91/70/53/52，Win/macOS/Linux | nordicsemi.com/Products/Development-tools/nRF-Connect-for-VS-Code |
| FreeRTOS × VS Code | FreeRTOS 官方组织 44 个仓库中无任何 IDE/VS Code 扩展仓库（IDE 路线 = CMSIS-Pack 分发 + 原厂 IDE + 通用工具链） | github.com/orgs/FreeRTOS/repositories（2026-09 实测） |
| RT-Thread × VS Code | Marketplace 发布者 "RT-Thread" 官方扩展仅三个：**RT-Thread MicroPython**（64.7K 安装）、**RT-Thread Smart Extension**（4K，Smart 版辅助）、rtt-llm-chat（LLM 工具）——均非通用全流程 IDE；通用开发经 `scons --target=vsc` 生成 VS Code 配置（.vscode/c_cpp_properties.json 等）；社区另有 Rt-Thread Assistant、RT-Thread Project Assistant 等第三方扩展 | marketplace.visualstudio.com 搜索 "rt-thread"（CDP 实测，2026-09-29）；RT-Thread tools/options.py |
| ThreadX × IDE | eclipse-threadx 组织 21 仓库无 IDE 产品；官方 Windows 工具仅 GUIX Studio（GUI 设计器）与 TraceX（trace 分析）；构建集成走 CMake `add_subdirectory()` + 原厂 SDK（ST/Renesas/Microchip 在提供，NXP 已停止）；markdown 版 rtos-docs 已于 2026-04-07 归档，文档迁移至 rtos-docs-asciidoc | github.com/eclipse-threadx/rtos-docs（archived 声明） |
| OpenVela × VS Code | 官方 docs 有 `VSCODE_debugging.md`，**仅覆盖 sim 仿真环境**（Microsoft C/C++ 扩展 cppdbg + launch.json，含 SMP 的 SIGUSR1 处理与 root 场景）；真机调试文档为 GDB（pynuttx）与 J-Link（jlink-nuttx.so）章节，无 cortex-debug 集成指南 | open-vela/docs `zh-cn/debugging_tools/GDB/VSCODE_debugging.md` |
| IAR × VS Code/Eclipse | IAR 官方提供 **IAR VS Code extensions**（把 IAR 构建与调试工具接入 VS Code）与 **IAR Eclipse plugins**；IAR 列 Zephyr 与 FreeRTOS 为生态伙伴；平台支持 20+ 架构、IDE 原生 Linux + Windows | iar.com/embedded-development-tools（产品清单） |
| cortex-debug | VS Code 扩展（marus25）：支持 J-Link/OpenOCD/ST-LINK GDB Server/pyOCD/BMP；**RTOS 线程视图依赖 GDB Server 的 RTOS 支持**（"RTOS supported depend on GDB server"）；支持 RTT/SWO、Live Watch、多核多会话 | 本地仓库 Study/cortex-debug README；marketplace marus25.cortex-debug |
| Windows 原生（各 OS） | Zephyr：Getting Started 明确 "These instructions cover the native Windows environment"（winget 流程，WSL 为替代）；RT-Thread：Env 自带 Python/SCons/ARM GCC/QEMU（env-windows 仓库实测）；OpenVela：manifest 工具链含 windows/darwin 宿主变体，但带 `groups="notdefault,platform-linux"`，官方文档/CI 主线为 Linux | docs.zephyrproject.org getting_started；github.com/RT-Thread/env-windows；open-vela/manifests openvela.xml |

## 附录 B：通用工具矩阵证据展开

| 工具 | 支持清单（官方原文） | 一手依据 |
|---|---|---|
| OpenOCD RTOS 感知 | 源码 `rtos_types[]` 全列：chibios、chromium-ec、ecos、embkernel、**freertos**、linux、mqx、**nuttx**、riot、rtkernel、**threadx**、ucos_iii、**zephyr**（+hwthread 兜底）——**无 rt-thread、无 LiteOS** | openocd 源码 src/rtos/rtos.c（master，2026-09 实读） |
| SEGGER Ozone RTOS Awareness | 官方列表含 ChibiOS、FreeRTOS、NuttX、ThreadX、Zephyr（另内置 embOS）——无 RT-Thread | segger.com Ozone "System Insight" 页（前期核实） |
| SEGGER SystemView RTOS support | 官方页 "RTOS support" 章节：**embOS**（4.12a 起默认）、**ThreadX**（6.4 起插桩）、**FreeRTOS**（V8/V9/V10/V11 可用，V11 起原生）、**uC/OS-II/III**（原生）、**Micrium OS Kernel**、**Zephyr**（2019 起集成进 tracing）、**NuttX**（经 SEGGER RTT Drivers）——**无 RT-Thread**；许可 perpetual 商业 / Friendly License 非商业免费；SystemView V4（2026-03）新增 ELF 直接加载 | segger.com/products/development-tools/systemview/（RTOS support 章节） |
| Percepio Tracealyzer | 官方支持：FreeRTOS、Zephyr、ThreadX、PX5 RTOS、SafeRTOS、LynxOS-178、VxWorks、Linux + **Bare-Metal 选项**（任意 C/C++）——无 RT-Thread、无 NuttX；FreeRTOS 免费版品牌名 **Percepio View**（仅快照追踪） | percepio.com/tracealyzer/ 及 licensing 页 |
| MCUboot 采用方 | Zephyr 第一官方集成（west sign → imgtool）；FreeRTOS 侧为 Lab-Project-FreeRTOS-MCUBoot（官方 Lab）；RT-Thread 侧为社区包；OpenVela/Linux 不用（自有 AVB / U-Boot Verified Boot） | github.com/mcu-tools/mcuboot；github.com/FreeRTOS/Lab-Project-FreeRTOS-MCUBoot |
| J-Link GDB Server RTOS 感知 | SEGGER RTOS awareness 为 J-Link 软件层能力（与 Ozone 同源）；OpenVela 侧另有官方 `jlink-nuttx.so` 插件（`make -f Makefile.host` 编译，JLinkGDBServer 加载后支持 `info threads`） | open-vela/docs J_Link.md；nuttx tools/jlink-nuttx.c |

## 附录 C：优劣判定证据清单（关键判定）

| 判定 | 事实依据 | 来源 |
|---|---|---|
| RT-Thread 软件包 875 / 下载 1856 万 | 官方 API packages/stats（2026-09） | api.rt-thread.org |
| RT-Thread BSP：CI 清单 362 路径 | `.github/ALL_BSP_COMPILE.json` 实测；README "nearly 200"（英）/“将近90种”（中）两处滞后且矛盾 | github.com/RT-Thread/rt-thread |
| ThreadX 认证：SGS-TÜV Saar + UL | IEC 61508 SIL 4（SGS-TÜV Saar）；UL 60730-1/60335-1/UL 1998；EAL4+ CC（Brightsight/SERTIT，TOE 含 ThreadX+NetX Duo+NetX Secure+MQTT）；FIPS 140-2（atsec/NIST） | github.com/eclipse-threadx/rtos-docs |
| NXP 停止提供 Azure RTOS | 官方页 "no longer offering this software as part of releases after MCUXpresso SDK 2.15" | nxp.com Azure RTOS 页 |
| OpenVela 调试/观测深度 | pynuttx（nuttx 仓 tools/pynuttx，12+ 命令源码逐一确认）；sched_note 六后端；traceparse.py → Perfetto；perf/gprof；bootctl KVDB + ddelta 差分 + AVB | open-vela 各仓库源码（详见《调研汇总》附三） |
| FreeRTOS CBMC | 官方 CI `proof_ci` 作业（CI-CD-Github-Actions/run_cbmc），proofs 在 FreeRTOS/FreeRTOS `Test/CBMC/proofs`，每 PR 校验 | github.com/FreeRTOS/FreeRTOS workflows |
| Twister | 扫描→过滤→构建并运行（QEMU/native_sim/真板 `--device-testing`）→ twister.json + JUnit XML；"并行"官方指构建并行（-j） | docs.zephyrproject.org twister 章节 |
| Zephyr Windows 原生 | "These instructions cover the native Windows environment. You may also use WSL…instead" | docs.zephyrproject.org getting_started |
| RT-Thread ⑥ 无标准 trace 出口 | SystemView 与 Tracealyzer 官方支持列表均无 RT-Thread；OpenOCD/J-Link 感知清单亦无 | 本文档附录 B 各行 |
| MCUboot 三件套 | 签名（RSA/ECDSA、防回滚计数）+ A/B 双槽 swap/overwrite + 失败自动 revert | mcuboot docs/design.md |

## 附录 D：核查方法与待核实项

**方法**：所有判定基于 2026-09 的官方一手来源——官方文档页（docs.zephyrproject.org、segger.com、percepio.com、iar.com、nordicsemi.com 等）、仓库源码与 LICENSE（OpenOCD rtos.c、RT-Thread tools/options.py、open-vela manifests 等）、Marketplace 官方发布者页面（经真实浏览器 CDP 访问）。反爬站点以官方 GitHub 仓库原始文件替代。判定为"缺席性"（如 ❌ 无支持）时，含义是"官方清单/源码中未发现"，置信度高但非可证伪的绝对事实。

**与既有文档的关系**：第一章总览矩阵与《调研汇总.md》开头的矩阵同源（⭐ 为新增标注）；《调研汇总.md》的 178 条工具详情是其附录级展开；LiteOS 视角的逐阶段对比另见《LiteOS竞争力分析.md》。

**本轮新增发现并已修正**：《调研汇总.md》RT-Thread ⑥ 原表述"SystemView / Tracealyzer 对接——两款第三方 RTOS 可视化工具均官方支持 RT-Thread"与两家官方支持列表不符（均无 RT-Thread），已修正为"社区移植/对接"口径。

**仍待核实**：
1. IAR C-SPY 对 Zephyr/ThreadX/NuttX 的 RTOS 感知确切清单（IAR 伙伴页未给出逐 RTOS 列表）；
2. Zephyr 对 IAR 工具链的支持状态（iar.com 列 Zephyr 为伙伴，但 Zephyr toolchains 文档未见 IAR）；
3. 商业 RTOS（VxWorks/QNX/INTEGRITY）的 IDE 形态（本次未纳入范围）；
4. RT-Thread Smart Extension 的功能边界（仅 Smart 版辅助，未深挖）；
5. 数据快照类（安装量、包数量）随时间变化，采用前请复核。

> **免责声明**：本文为技术选型参考；工具能力、许可与支持状态随厂商版本变化，正式采用前请核对官方最新文档与 EULA。
