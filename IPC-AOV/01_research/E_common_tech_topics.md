# 电池 IPC「AOV/全天候持续录像」共性技术专题调研

> **调研目的**：梳理电池 IPC（网络摄像机）AOV（Always-On Video，全天候持续录像）背后的通用技术机制与系统软件层实现，不绑定特定厂商，为后续在 OpenHarmony L1 小型系统（LiteOS-A 内核）上设计系统层低功耗方案提供借鉴。
>
> **调研日期**：2026-09-10（文中所有网络来源的访问日期均为 2026-09-10，参考文献编号 [n] 对应文末列表）
>
> **调研方法**：以厂商官方资料（君正、海思、瑞芯微生态、星宸、思特威、涂鸦、乐鑫、海思 HiSpark）为一手来源，配合内核/RTOS 官方文档与源码（Linux kernel、Zephyr、FreeRTOS、OpenHarmony LiteOS-A、powermgr_lite）、深度技术博客（CSDN/知乎/掘金）与学术论文（sleepyCAM、Panoptes、arXiv 等）交叉验证。厂商宣传数值（尤其功耗）多为特定测试条件下的结果，引用时已注明出处与条件，落地时应以实测为准。

---

## 目录

1. [快速启动（秒级/毫秒级快启）技术](#1-快速启动秒级毫秒级快启技术)
2. [STR（Suspend-to-RAM）与待机唤醒机制](#2-strsuspend-to-ram与待机唤醒机制)
3. [占空比录像（duty-cycle recording）策略](#3-占空比录像duty-cycle-recording策略)
4. [功耗状态机设计](#4-功耗状态机设计)
5. [存储与网络链路省电](#5-存储与网络链路省电)
6. [RTOS 层低功耗框架](#6-rtos-层低功耗框架)
7. [对 OpenHarmony L1 落地的综合启示](#7-对-openharmony-l1-落地的综合启示)
8. [参考文献](#参考文献)

---

## 0. 背景：AOV 是什么，为什么成为电池 IPC 的主流方向

- **AOV（Always-On Video）**：基于"超低功耗内存保持 + 快速启动待机"技术，使纯电池设备实现 7×24 小时不间断录像。核心是**休眠期低帧率录像（典型 1 帧/秒或 2 秒 1 帧）+ 事件触发实时录像（15~30fps）的混合模式**，解决传统 PIR 触发式方案"事件间隙无录像、漏报误报"的痛点 [2][13]。
- **第一代（PIR 触发式）痛点**：PIR 检测距离短（通常 <10 米）、响应延迟、高温误报、关键画面漏录；触发唤醒有 2~3 秒缓冲延迟；休眠功耗 >100mW [2][13]。
- **第二代（AOV）现状**：主流芯片方案运行态功耗降至 40mW 级（AOV 3.0 宣称 <40mW，待机 1mW 级），AI 视觉侦测距离达 30 米，可配合太阳能板实现"录像一直有、充电可以无"的全年免维护部署 [1][4][13]。
- **市场验证**：君正 T 系列 AOV 方案一年内实现百万级出货（捷高、觅睿等客户）[1]；瑞芯微 RV1106/RV1126B、海思 Hi3516CV610、星宸 SSC30x/SSC37x、国科微 GK720x 均已推出 AOV 级低功耗 IPC 芯片 [3][9][13][14][50][51]。

AOV 的技术底座可以拆解为本文的 6 个共性专题：**快启**（唤醒后尽快出图）、**STR**（休眠时保持现场、低功耗驻留）、**占空比录像**（唤醒-出图-编码-存储-休眠流水线）、**功耗状态机**（多级状态定义与切换）、**存储/网络省电**（外设与链路功耗治理）、**RTOS 低功耗框架**（tickless、锁、DVFS、驱动 PM）。

---

## 1. 快速启动（秒级/毫秒级快启）技术

### 1.1 机制原理

快启的目标不是"开机快"，而是**"最短时间拿到稳定可用的图像"**（TTFF, Time To First Frame）[19]。启动流水线分三段：**bootloader → kernel → rootfs/应用**，每段都有独立的优化空间 [19][22]。电池 IPC 的快启有两类场景：

1. **冷启动快启**（掉电重启、hibernate 唤醒）：走完整 boot 流水线，靠裁剪与并行化压缩各阶段耗时；
2. **STR 唤醒快启**（suspend-resume）：内存现场保留，只需恢复时钟/电源域/外设驱动，配合 sensor 快启，可做到 100ms 级 [4][5]。

现代 AOV SoC 普遍引入**异构小核/协处理器**把"出图"从主核启动路径中剥离：如君正 T31/T41 内置 RISC-V 协处理器，在 boot 阶段（甚至主核休眠时）就独立完成 sensor 初始化与 ISP 预出流，主核 Linux 起来后直接接管已出图的通路 [20][31]；君正 Atlas 方案采用"Xburst 大核 + RISC-V 小核"大小核架构，小核 7×24 负责低帧率采集与休眠/唤醒管理，大核深度休眠 [5]。

### 1.2 典型实现手段

**（a）bootloader 裁剪与绕过**

- 裁剪 U-Boot：关闭用不到的命令/协议/驱动（网络、USB、多余文件系统），只保留必要存储驱动；uboot 光初始化串口/网卡/USB 就可能花掉 1~2 秒 [22]。
- `bootdelay=0` 取消启动倒计时 [22]。
- **Falcon 模式**：SPL（第一阶段）直接加载并启动内核，跳过完整 U-Boot 第二阶段，可节省 300~500ms [22]。
- **并行加载**：boot 阶段将"从 flash 加载数据"与"sensor 复位/初始化/出流"并行处理，提高 flash 时钟频率加快加载 [19]；sensor 在 boot 阶段提前复位并配置出流 [19]。
- 专利方案：主控上电后 bootloader 阶段即启动 ISP/sensor 初始化，与内核加载并行，缩短整体出图时间 [48]。

**（b）kernel 阶段**

- **去除内核打印**：串口每条打印可能耗时数 ms，量产关闭 console 输出（`quiet`、`loglevel=0`）[19][22]。
- **内核裁剪**：删掉不必要驱动、debug 堆栈信息；内核镜像大小直接影响 boot 阶段加载耗时；非启动必要驱动编成 ko 延后加载（对应 `late_initcall`/deferred initcall 思路）[19][22]。
- **快出图驱动内建并提权**：快速出图必要的驱动（sensor/ISP/编码器）编译进内核，并提高驱动注册优先级 [19]。
- **内核镜像压缩**（如 LZ4）：解压通常比从慢速 flash 读大镜像更快 [22]。
- **XIP（eXecute In Place，芯片内执行）**：代码不搬运到 RAM、直接从 SPI NOR Flash 取指执行（通过 QSPI 内存映射），省去加载/解压时间，同时节省 RAM——是 RTOS 类系统（RT-Thread/LiteOS-M 级）从 NOR 直启的常规做法 [23]。海思 Hi3516CV610 支持从 SPI NOR（最大 32MB）/SPI NAND（最大 512MB）/eMMC 启动 [14]；国科微 GK7203V1 等把 64/128MB DDR 合封并支持自刷新，同样面向 NOR/NAND 直启场景 [53]。
- **帧策略优化出图时间**（君正 T31 实例）：内核默认等协处理器出满 6 帧才切换主通路，可降低 `frame_count` 门槛；默认丢 2 帧可改为丢 1 帧；前两帧用高帧率出图（配合 sensor 隔帧生效特性，第 1 帧设置帧率、第 3 帧生效），差帧丢弃，用帧率切换+丢帧组合压缩首帧时间 [20]。内核提供 `DEBUG_TTFF()` 打印从上电起算的分段时间，用于逐段定位 [20]。

**（c）rootfs/initramfs 阶段**

- **ramfs/initramfs 以内存换时间**：程序"先 copy 再执行"，从内存拷贝远快于从 flash 拷贝；rootfs 采用 ramfs 在内核起来后立即挂载执行 rcS [19]。
- **精简 initramfs**：用压缩 cpio + busybox 静态二进制 + 最小 init 脚本，跳过真实文件系统驱动初始化/分区表解析，显著缩短内核到用户态的时间 [22]。
- **文件系统不要太大**：非快启必要的文件/库放其他分区，延后加载 [19]；非启动必须资源（配网音频、字库）放 system 分区 [20]。

**（d）应用阶段**

- **主程序最先跑**：rcS 中环境变量设置完立即启动主程序；主程序依赖的动态库（如 libimp.so）放 rootfs；主程序先初始化视频，P2P/认证鉴权等业务**并行**处理 [20]。
- **非启动依赖库 dlopen 延迟加载**（如 libcrypto）[20]；应用层惰性初始化、避免大量全局对象构造 [22]。
- **readahead 预读 + prelink 预链接**：readahead 把将用到的 .so 提前读入 page cache；prelink 事先解析动态库符号引用、减少运行时重定位，缩短启动时间并降低内存开销（库版本变更后需重新 prelink，且增大 rootfs）[22][24]。
- **启动脚本并行化**：rcS 中无依赖任务后台并行执行 [22]。

**（e）sensor 侧快启（常被忽视的一环）**

- 传统 CIS 从休眠到完全启动（含 AE/AGC/AWB 收敛）需 250ms 以上，事件目标可能已离开画面 [18]。
- 思特威 SmartAEC™：把 AEC/AGC/AWB 内置到 sensor，实现**毫秒级唤醒**——普通光照下休眠到启动完成 <40ms，极暗/极亮环境 <60ms，比传统 CIS 节省约 60%/67% 启动时间，且省去模拟光敏电阻 [18]。
- 工程实践：sensor 睡眠态进 stream-off/standby，事件触发再唤醒；"唤醒出图时间"是选型关键指标（有的 sensor 冷启动到首帧要几百 ms）[31]。

### 1.3 关键数值（快启时间分解与整机指标）

| 指标 | 数值 | 来源/条件 |
|---|---|---|
| 君正 T31 官方第一帧图像 | 200ms（实际应用会更长） | [20] |
| 君正 T31 平台高质量出图工程目标 | 500ms 内（需跨越 sensor 初始化、AE 收敛等多重瓶颈） | [54] |
| 君正 Atlas 快速启动 | <100ms，AI 模型零延迟加载 | [2] |
| 瑞芯微 RV1126B 极速启动 | 0.1 秒（100ms） | [10][12] |
| 全志 V833 + Melis4.0（RTOS 直启） | 冷启动到出图 298~300ms | [21] |
| 思特威快启 CIS | 普通光 <40ms / 极端光 <60ms（传统 >250ms） | [18] |
| 传统 AOV 1.0/2.0 方案唤醒缓冲延迟 | 2~3 秒 | [13] |
| U-Boot Falcon 模式收益 | 省 300~500ms | [22] |
| U-Boot 未裁剪外设初始化 | 可耗 1~2s | [22] |
| 车载仪表参考要求 | 点火到显示 <2s | [22] |
| 人脸门锁算法加载 | 传统秒级 → Atlas 毫秒级开门 | [4] |
| 觅睿 T41ZM 球机事件触发响应 | <100ms，30 米人形侦测 | [2] |

**典型阶段耗时分解方法**：uboot 用 `timer_get_us`、内核用 printk 时间戳（君正 SDK 提供 `DEBUG_TTFF()` 从上电计时）、用户态用 `time`，逐段测量定位瓶颈 [20][22]。优化原则："去掉不需要的、延迟做不需要立刻做的、并行做可以同时做的" [22]。

### 1.4 对 OpenHarmony L1（LiteOS-A）的适用性分析

- **RTOS 直启路线天然占优**：全志 V833 用 Melis（RT-Thread 系 RTOS）做到 ~300ms 冷启动出图 [21]，说明不跑完整 Linux 的 RTOS 路线在快启上有结构性优势。LiteOS-A 内核体积小（MB 级镜像）、启动路径短（无 systemd/服务管理框架），配合 SPI NOR XIP 可省去"加载内核到 DDR"的大头耗时 [23][35]。
- **XIP 适配要点**：XIP 要求代码段直接映射到 NOR 地址空间、可写数据搬 RAM [23]；LiteOS-A 的 `LOSCFG` 内存布局需按"代码 XIP + 数据 RAM"划分，中断向量与热点函数（调度、ISP 中断处理）建议仍拷入 RAM 执行以规避 NOR 随机读延迟。
- **initramfs 概念在 L1 的对应物**：L1 通常用 ramdisk/romfs 或直接 XIP rootfs；应借鉴"快出图必要文件进小 ramfs、其余延后加载"的分层思想 [19][22]。
- **应用预链接**：L1 若使用动态加载（LiteOS-A 支持动态库/`dlopen` 风格的按需加载），可借鉴 prelink 减少重定位 [24]；更激进的做法是关键路径静态链接。
- **启动任务编排**：借鉴 [20] 的"视频通路优先、网络业务并行"，在 L1 上应把出图任务设为最高优先级，Wi-Fi 连接/云平台鉴权放低优先级任务并行执行；驱动侧将 sensor/ISP/venc 驱动注册优先级提前。
- **快启与 STR 互补**：L1 方案若具备 DDR 自刷新能力，优先走 STR 唤醒（免 boot）；冷启动快启仅作为 hibernate/掉电后的兜底路径设计。

---

## 2. STR（Suspend-to-RAM）与待机唤醒机制

### 2.1 机制原理

**STR 的本质**：把系统状态（CPU 寄存器、设备上下文、内存内容）保存在 RAM 中，DDR 进入自刷新（self-refresh）模式维持数据，其余电源域尽量关断，由常驻低功耗单元（PMU/协处理器/Always-On 域）监听唤醒源；唤醒后恢复现场继续执行，无需重新 boot [25][27][29]。

**Linux 睡眠状态家族**（内核官方定义）[25]：

| 状态 | sysfs 写法 | 机制 | ACPI 对应 |
|---|---|---|---|
| Suspend-to-Idle（S2I/freeze） | `freeze` | 纯软件轻量挂起：冻结用户态、停 timekeeping、设备进低功耗态，CPU 进最深 idle；任何可产生中断的设备都可作唤醒源 | — |
| Standby（浅睡） | `standby` | S2I 基础上关闭非启动 CPU、挂起底层系统功能；核心逻辑保持供电 | S1 |
| **Suspend-to-RAM（STR/deep）** | `mem`（`mem_sleep=deep`） | 除内存（self-refresh 保持内容）外全部进低功耗态；设备/CPU 状态保存在内存中；多数外设总线断电，设备驱动必须能处理重新上电；唤醒设备集合缩小，常需平台固件配合 | S3 |
| Hibernation（STD） | `disk` | 内存快照写入持久存储后近乎全断电；唤醒需 restore kernel 引导恢复 | S4 |

Zephyr 的 `pm_state` 枚举给出了 RTOS 视角的同构映射：`PM_STATE_ACTIVE`(S0)、`RUNTIME_IDLE`(S0ix)、`SUSPEND_TO_IDLE`(S1)、`STANDBY`(S2)、`SUSPEND_TO_RAM`(S3，"内存进入 self-refresh 保持内容，设备与 CPU 状态存于内存，可能需要 ROM 引导代码恢复")、`SUSPEND_TO_DISK`(S4)、`SOFT_OFF`(S5，不保留现场、等价重启) [32]。LiteOS-A/LiteOS-M 则定义 4 档：`LOS_SYS_NORMAL_SLEEP / LIGHT_SLEEP / DEEP_SLEEP / SHUTDOWN` [34][35]。

**硬件层面的三个关键维度**（以高通 SM8450 STR 为例）[29]：

1. **电压域调节**：PMIC 将除 Always-On 域（AOP，Always-On Processor）外的 LDO 输出降至最低/关断；
2. **时钟树修剪**：系统总线时钟从 MHz 级降到 32kHz 基准时钟；
3. **IP 核冻结**：GPU/DSP 等模块进入电气隔离，漏电流控制在 μA 级。

**DDR self-refresh 与 retention 细节**[30]：

- 进入自刷新前所有 BANK 必须预充电至 IDLE、满足 tRP/tDAL 等时序，关闭 ODT 端接；SRE 命令后 CKE 保持低电平，DRAM 内部计数器自行发刷新命令，**不需要外部时钟**；VDD/VDDQ/VSS/VRefCA 等供电必须保持有效（自刷新≠断电）；自刷新期间可停外部时钟省电（最小停留 tCKESR）。
- 退出自刷新：外部时钟先稳定→SRX→tXS 后可发免 DLL 命令、tXSDLL 后可发需 DLL 锁定命令；因电压/温度漂移需重做 ZQ 阻抗校准。
- **PHY Retention**：主控 core 电压（VDD）断电时，DDR PHY 通过 `Data_Retention_N` 信号把 SSTL IO 锁存到已知状态（维持 CKE 低、RESET# 高等），保证 DRAM 侧信号不乱；重新上电后先初始化 core 逻辑再解除 retention。这是"主控断电但内存保数据"的关键配合机制。
- 电池 IPC SoC 的做法：休眠时"CPU 部分电源关闭，只保留 CPU 的 DDR 电源以暂存休眠前数据，外设电源关闭，sensor 进低功耗 standby，仅 DDR 和协处理器 PMU 工作"，做得好的芯片休眠功耗 40mW 级（含周期性出图的 AOV 态）[6]；内置 DDR 合封芯片（GK7203V1 等）直接支持自刷新 [53]。

**CPU retention 模式**：电源域支持"retention（保持寄存器内容、断电省漏电）"与"off（完全断电、需重初始化）"两档；STR 下 CPU 域通常 retention 或 off+上下文存 RAM。AOP/PMU 常驻域负责唤醒仲裁（外部信号/中断经 AOP 切回正常电源模式）[29]。

### 2.2 suspend-resume 软件流程

**Linux 标准流程**[25][27][28]：

```
echo mem > /sys/power/state
 → pm_suspend() → enter_state()
    → sys_sync()                       # 同步文件系统
    → suspend_prepare()                # 冻结用户态进程与内核线程
    → suspend_devices_and_enter()
       → dpm_prepare()                 # 阶段1: 设备 prepare（runtime PM 可用、中断正常）
       → dpm_suspend()                 # 阶段2: 设备主挂起（保存状态、停 I/O）
       → dpm_suspend_late()            # 阶段3: runtime PM 已 disable
       → dpm_suspend_noirq()           # 阶段4: 非 wakeup 中断不再分发
       → disable_nonboot_cpus()        # 冻结副 CPU
       → syscore_suspend()             # 阶段5: 时钟源/中断控制器等最底层硬件
       → suspend_ops->enter()          # 阶段6: 平台进入硬件休眠（ARM 常见走 PSCI/ATF）
    ← 唤醒后按镜像逆序: syscore_resume → resume_noirq → resume_early → resume → complete → 解冻进程
```

关键设计规则：**越底层的驱动越晚 suspend、越早 resume**（普通外设用 `SET_SYSTEM_SLEEP_PM_OPS`，时钟/regulator/pinctrl 等资源提供者用 `LATE_SYSTEM_SLEEP_PM_OPS`，中断控制器/电源域等基础设施用 `NOIRQ_SYSTEM_SLEEP_PM_OPS`）[28]。

**wakelock / wakeup_count 机制**：上层 service 通过 wakelock 表达"系统还需要工作"；无 wakelock 持有时 power manager 向 `/sys/power/state` 写 `mem` 发起休眠；`wakeup_count` 用于处理"释放锁到真正休眠之间来了唤醒事件"的竞态（有唤醒事件则放弃/中止本次休眠）[27]。

**RTOS 流程（Zephyr）**：idle 线程在无可调度任务时锁中断调用 `pm_system_suspend()` → 策略管理器选择电源状态（residency 策略：`空闲时长 ≥ min_residency + exit_latency` 才允许进入该状态）→ 可选挂起设备（system-managed device PM）→ `pm_state_set()` 执行 SoC 级低功耗进入 → 唤醒事件后恢复设备、执行 post-ops/时钟补偿 → 解锁中断处理挂起的中断 [32]。应用负责设置唤醒事件（RTC/counter/GPIO 等），且**并非所有外设在所有电源状态下都能作为唤醒源** [32]。

**AOV 特有的"单帧 suspend-resume 循环"**（君正 Atlas 软件流程）[5]：

- AOV 模式下**每次 suspend-resume 只处理一张图片**：该帧经编码或缩放后交给算法，宏观表现为 1fps；
- 单帧模式（first frame）：ISP 处理完首帧后通知 sensor 进 standby（StreamOff），并关闭自身所有模块降功耗；
- 基础视频通路（Main Stream: Sensor→ISP→IPU→VPU）与算法通路（Second Stream: Sensor→ISP→IVS）分离，算法通路决定下一周期走"长出流"（实时流）还是 AOV 单帧模式；
- 休眠入口就是标准 Linux STR（写 `mem`），但每个占空比周期都完整走一遍 suspend→(RTC/WKUP 唤醒)→resume。

### 2.3 唤醒源设计

| 唤醒源 | 机制 | 典型指标/备注 | 来源 |
|---|---|---|---|
| **RTC 定时** | RTC alarm 计数到达唤醒；AOV 占空比周期的心跳 | "纳秒级响应、功耗仅微瓦级"；RKADK AOV 定时休眠最大支持 37 小时 | [5][9] |
| **GPIO/PIR** | PIR 输出电平变化→IO 中断/WKUP 引脚 | 第一代方案主唤醒源，<10 米、易受温度干扰；AOV 中作为辅助触发 | [2][6][38] |
| **WKUP 专用引脚** | SoC 常驻域外部唤醒输入，立即唤醒系统（用户预览、PIR 触发等强制唤醒） | 唤醒导致 PWRON 事件通知应用 | [5] |
| **网络 WoL/WoWLAN** | 网卡/WiFi 芯片在低功耗态监听 magic packet/特定帧唤醒主机 | Linux 经 `/sys/.../power/wakeup` + ethtool 使能；以太网 WoL 默认常开 | [26] |
| **WiFi 远程唤醒（云）** | WiFi 芯片/MCU 维持 DTIM 监听+心跳长连接，收到云端指令经 UART/SDIO 唤醒主控 | 涂鸦"低功耗 IPC 业务能力"：休眠时可被预览/DP 配置远程唤醒；专利：WiFi 模块持续心跳维持服务器连接后远程唤醒 | [41][49] |
| **声音触发（AOA）** | 低功耗音频通路常驻检测异常声源（狗吠、玻璃破碎、枪声、哭声） | RV1126B AOV3.0 融入低功耗音频事件唤醒，待机 1mW 级 7×24 监测；CV610 哭声检测 2.0；音频分析比视频分析省电 | [12][13][14] |
| **AI/NPU 事件** | 小核+NPU 常驻跑轻量模型（人形/车形），命中后唤醒大核 | 30 米级人车检测、准确率 99%+；MicroNN 轻量模型常驻 | [2][5] |
| **传感器 hub/MCU** | 独立 MCU 管理 PIR/按键/电量，经 UART 发唤醒指令 | 4G/WiFi AOV 双芯片/三芯片架构中的标准角色 | [7][8] |

Linux 内核将"硬件唤醒事件"归纳为：RTC alarm、WoL 网络包、键盘/鼠标、介质插拔（MMC/SD、USB）等；设备通过 `device_set_wakeup_capable()` 声明能力、用户态经 `power/wakeup` sysfs 开关策略；**系统唤醒（system wakeup）与运行时远程唤醒（remote wakeup）概念不同但可能共用物理机制** [26]。

### 2.4 关键数值（唤醒延迟与休眠功耗）

| 指标 | 数值 | 来源 |
|---|---|---|
| Atlas/T41 事件触发响应（STR 唤醒到出图/抓拍） | <100ms | [2][4] |
| RV1126B 极速启动（唤醒） | 0.1s | [10][12] |
| 传统触发式方案唤醒缓冲延迟 | 2~3s | [13] |
| 工程需求实例：触发后抓到 1080p 清晰人脸 | 100ms 内 | [31] |
| SM8450 STR 各模块电流 | AOP 子系统 12μA、DDR 控制器 8μA、显示接口 0.5μA、外设 IO 环 2μA（对比工作态 15/45/22/18mA） | [29] |
| Zephyr 电源状态示例退出延迟 | suspend-to-idle 100μs / standby 240μs / STR 360~500μs（min-residency 5~50ms，devicetree 示例值） | [32] |
| T41 待机功耗构成 | 主核 WFI + DDR self-refresh + sensor 1fps VGA：~0.15W；加 RISC-V 协处理器运动检测：~0.22W | [31] |
| RV1126B AOV 值守（核心板） | 0.007W（7mW，摄像头休眠、核心板 AOV 值守） | [11] |
| RV1126B 待机（AOV3.0 宣传） | ~1mW | [12][13] |
| 君正 T41ZM/ZG 休眠功耗 | 1mW 级（业内最低档宣传值） | [1] |
| DDR 自刷新退出时序约束 | tXS 内发免 DLL 命令、tXSDLL 后才可发 DLL 锁定命令、需 ZQ 重校准 | [30] |

### 2.5 对 OpenHarmony L1（LiteOS-A）的适用性分析

- **LiteOS-A 已具备 STR 骨架**：内核 PM 组件（`kernel/extended/power/los_pm.c`，受 `LOSCFG_KERNEL_PM` 控制）提供 4 档休眠模式、`LosPmSysctrl` 的 `deepSuspend/deepResume` 回调（对应 STR 平台入口）、`LosPmDevice` 设备挂起/恢复注册、tick timer 停走与补偿（跨节拍休眠）、PM 锁（`LOS_PmLockRequest/LOS_PmTimeLockRequest/LOS_PmLockRelease`）与 `LOS_PmSuspend` 入口 [35]。默认 `OsIdleTask` 是 WEAK 符号、仅 `WFI`，**平台可通过覆写 idle 任务接入完整 PM 流程** [35]——这是 L1 上做 STR 的第一落点。
- **需要芯片 BSP 补齐的部分**：DDR self-refresh 进入/退出序列、PHY retention、电源域 gating、PMU 唤醒仲裁均为 SoC 强相关，LiteOS-A 内核只留回调位（`deepSuspend` 等），需参考 Linux 平台 `suspend_ops->enter()` 的实现由板级代码填充 [28][35]。
- **唤醒源管理**：L1 无 sysfs/wakeup_count 体系，可借鉴 Linux "wakeup source + 计数防竞态"思想 [27]，在 LOS PM 锁机制上封装：休眠前统计使能的唤醒源、`LOS_PmWakeSet()` 标记唤醒、resume 后检查唤醒计数决定是否立即复睡 [35]；WS53（LiteOS 系 OpenHarmony 芯片）的 LPC 框架提供了现成参考：`uapi_pm_register_dev_ops()` 注册设备 suspend/resume 回调 + "sleep veto"（模块持否决则系统不睡）+ GPIO 唤醒引脚配置（边沿中断、施密特触发、10ms 防抖）[38]。
- **AOV 单帧循环可直接移植为 L1 应用状态机**：`RTC 定时唤醒 → resume → 采集一帧 → 编码 → 存储/判断 → suspend` 的循环在 L1 上即"深睡模式 + 高精度 RTC 软定时器"组合；注意 LiteOS-A tick 补偿精度决定占空比定时精度（建议用 RTC/宽定时器做唤醒基准，而非 tick 估算）[34][35]。
- **resume 路径优化**：Linux 分 6 阶段 resume 的教训是"设备恢复顺序错乱导致总线错误" [28]；L1 设备少，应按"时钟/中断控制器 → 存储 → ISP/sensor → 网络"顺序恢复，且驱动 resume 需幂等（外设可能在休眠中掉电）。

---

## 3. 占空比录像（duty-cycle recording）策略

### 3.1 机制原理

**占空比录像的核心逻辑**："主芯片在绝大多数时间处于休眠状态，仅在需要时被短暂唤醒执行必要任务，完成后立即重新进入休眠" [6]。一个典型工作周期 [6][5]：

1. **定时唤醒**：PMU/RTC 每隔固定周期（如 1 秒）唤醒主芯片；
2. **快速取帧与编码**：sensor 出图 → ISP 处理 → 编码生成一帧（或几帧）；
3. **可选任务**：跑轻量 AI（人形/车辆检测）、判断是否切入高帧率录像、经 Wi-Fi/4G 上传一帧到云端；
4. **立即休眠**：任务完成后重新 suspend，等待下次定时唤醒或外部触发。

**平均功耗模型**（决定续航的第一性公式）[6]：

```
P_avg ≈ P_sleep + (P_wake − P_sleep) × duty
例：休眠 40mW、唤醒 1W、每秒唤醒工作 10ms
    → P_avg ≈ 40 + (1000−40)×0.01 ≈ 50mW
优化到每秒工作 5ms → ≈45mW，续航提升近一倍
```

即：**唤醒后工作时间越短，整机平均功耗越低**——快启（第 1 章）、单帧流水线的紧凑度、编码效率都直接折算为续航。学术界对该模式的表述：视觉传感器超过 99% 的时间在等待事件，等待期能耗是总能耗的主导项 [44]。

**帧率/分辨率/色彩维度的降级谱系**：

- 帧率：事件期 15/25/30fps ↔ 值守期 1fps（主流）、2~3 帧/秒（RV1106 方案）、2 秒 1 帧（君正上限）、5 帧/秒（神眸 AOR，兼顾音频）[1][2][3][13][15]；
- 分辨率/格式：值守期 sensor 切 VGA 等小分辨率模式做运动检测（全尺寸切换回 1080p 需重配 sensor/ISP，是唤醒延迟大头）[31]；ISP 可在主核休眠时只输出 YUV422 缩略图供检测 [31]；
- 动态帧率调节：1fps~25fps 自适应 + 智能电源门控 [2]。

**智能编码（变化才记录）**：值守期"闲时浓缩录影、重要事件全帧率记录" [15]；非事件期用高频抓拍替代全帧录制可节省 90% 存储空间 [2]；智能编码按场景自适应调整，比常规 CBR 省 50%+ 码率 [3]；SVAC3.0 比 H.265 再省约 20% 码率、智能编码 2.0 下 4MP@30fps 每天仅约 5GB [16]。

### 3.2 典型实现手段

**（a）流水线设计（唤醒-出图-编码-存储-休眠）**

- **单帧模式**：AOV 每次 suspend-resume 只处理 1 张图，ISP 处理完首帧即通知 sensor StreamOff 并关闭自身模块 [5]；海思 SDK 中对应"KOL 模式"（官方 demo：平时 1 秒 1 帧 AOV 录像，AI 检测检出人脸后抓 jpg 并切正常录像，ko 模块 + sample 程序 + 检测模型三件套）[17]；
- **切换进入 AOV 的收尾动作**（RKADK/RV1126B 实测流程）：把系统剩余帧取完防止残留帧影响休眠唤醒 → 关闭子码流/音频等非必要媒体流 → **卸载外设驱动（SD 卡、以太网、USB、SDIO）** 降低休眠与唤醒功耗 → 进入 AOV 单帧模式；退出 AOV 时逆序恢复 [9]；
- **检测-决策-唤醒链路下沉小核**：T41 内置 RISC-V 协处理器 + 硬件运动检测单元，主核休眠时独立跑完"检测→决策→唤醒"；工程优化实例：运动检测从 ISP MD 模块挪到 RISC-V 上跑 VGA 帧差分，差分阈值随环境光强动态调整（白天高、夜晚低，参考 ISP 自动曝光统计值），误报率降 80%，代价是待机功耗 0.15W→0.22W [31]；
- **进出模式滞回**：1fps 检测到人形→切正常帧率；正常帧率下连续 5 帧未检测到人形→退回 AOV（防抖动切换）[10]。

**（b）漏录与功耗的权衡**

| 方案 | 漏录风险 | 功耗 | 备注 |
|---|---|---|---|
| PIR 触发式（一代） | 高：<10m 探测、高温误报、响应 2~3s、事件间隙无录像 | 休眠 >100mW，续航长 | 市场反馈不佳 [2][13] |
| AOV 1fps（二代主流） | "每一秒都有数据"，零漏报；但 1fps 对高速目标仍可能丢关键帧 | 40~180mW 级 | [2][3][9] |
| AOV 多秒 1 帧 | 漏报率高于 1fps 方案 | 更低 | RV1106 方案对比"多秒一帧"竞品 [3] |
| AOR（1 秒 5 帧+完整音频） | 进一步降低丢画面/丢音频 | 高于 1fps | 高速旋转云台场景 1fps 仍丢画面 [13] |
| 音频辅助（AOA） | 声音事件不漏（视频之外的维度） | 音频分析比视频省电，待机 1mW 级 | RV1126B AOV3.0 [12][13] |

**（c）学术界方法**

- **sleepyCAM**（IEEE ICC Workshops 2017）：对不支持低功耗模式的相机节点（树莓派），用"低功耗控制节点 + PIR + 继电器"做电源门控——等待期整机 5.4mW（对比软件运动侦测方案 1423.6mW、硬件 PIR 但主机常开方案 2162.9mW），功耗改善 >99%，6000mAh 电池等待期续航约 2600 小时（108 天）；录制期整机 2140.5mW（控制节点因继电器吸合升至 212mW）[44]。这是"占空比=0 的极端形态"（纯触发式）与 AOV（占空比>0 持续录像）的两个端点。
- **Panoptes**（ACM 2005）：早期低功耗视频传感网络平台，通过 802.11 网络传输高质量视频并做功耗管理，是视频传感网节能的开山工作之一 [45]。
- **自适应占空比**：能量收集 IoT 网络中用 KNN 基于时空相关性动态管理 duty cycling，在能效与检测准确率之间折中（arXiv 2405.06372）[46]；自适应占空比专利通过活动监测电路动态调整传感器占空比 [47]；能量收集约束下的自适应占空比调度亦有系统研究 [55]。启示：**占空比不必是固定 1fps，可按场景活动性/电量/光照（太阳能输入）动态调节**。

### 3.3 关键数值

| 指标 | 数值 | 来源 |
|---|---|---|
| AOV 值守帧率 | 1fps（主流）/ 1~3fps（RV1106）/ 0.5fps（君正上限 2 秒 1 帧）/ 5fps（AOR） | [1][2][3][13] |
| 事件模式帧率 | 15fps（CV610 方案）/ 25fps（君正）/ 30fps（常规）/ 演示中切 60fps | [2][10][15] |
| 占空比功耗实例 | 休眠 40mW + 每秒醒 10ms@1W ≈ 50mW | [6] |
| RV1106G2 AOV IPC @1fps 整机 | ~40mW；5200mAh 电池无日照约 14 天 | [3] |
| Hi3516CV610 AOV @1fps | 80mW（方案级宣传值，官网功耗标注 TBD） | [14][15] |
| RV1126B 整板实测 | 正常推流(全帧率+AI) 1280mW / 空闲 580mW / AOV 低帧率 180mW（降 86%） | [9] |
| RV1126B 评估板（SC850SL） | AOV 待机 ~122mW，比正常模式节能 90%+ | [10] |
| 君正 T41ZM/ZG/T32V AOV 典型功耗 | 40+mW | [1] |
| 觅睿 T41ZM 球机 | 2 节电池 + 5W 太阳能板：15 天内有太阳即全年免充电 | [2][4] |
| sleepyCAM 等待期功耗 | 5.4mW（控制节点），RPi 断电 0mW | [44] |
| 存储节省 | 智能编码比 CBR 省 50%+；非事件期抓拍替代全帧录制省 90% 存储；SVAC3.0 比 H.265 省 20% | [2][3][16] |

### 3.4 对 OpenHarmony L1（LiteOS-A）的适用性分析

- **占空比状态机适合放在 L1 应用框架层**：内核只提供 suspend/resume 与锁机制（第 6 章），"何时醒、醒多久、做什么"是策略问题——建议独立的 power policy 任务持有状态机（AOV 单帧循环 / 事件录像 / 上传 / 充电全速），用 RTC 硬件定时器而非系统 tick 设定唤醒点（tick 补偿有误差且宽定时器不一定存在）[34][35]。
- **"唤醒即批处理、完成即休眠"**：把取帧、编码、SD 写入、AI 判断、（可选）上传组织为唤醒窗口内的串行流水，窗口时长目标 <10~20ms/帧周期（对应 40mW 级平均功耗）[6]；L1 内存小，编码输出应直接 DMA 到存储缓冲，避免多次拷贝。
- **降级谱系可裁剪适配**：L1 设备若无 NPU，可用"帧差 + 动态阈值"替代 AI 检测（误报率优化思路同 [31]）；灰度/低分辨率值守帧对 ISP 依赖小，适合小内存系统。
- **动态占空比**：参考 [46][47]，按电量（电池服务上报）与场景活动性调节唤醒周期（如夜间静止场景降到 0.2fps、白天提到 2fps），在 L1 上即修改 RTC alarm 周期，实现成本低。
- **漏录兜底**：切换高帧率的触发条件除 AI/PIR 外，保留"云端/App 强制唤醒"（远程预览即切正常模式）[41][42]。

---

## 4. 功耗状态机设计

### 4.1 机制原理

电池 IPC 的多级功耗状态机是上述所有技术的集成框架：**每级状态对应一组"保持什么、关掉什么、谁能唤醒、唤醒多快"的契约**。业界两种代表性建模：

**（a）瑞芯微 RV1126B AOV 三模式**（芯片级支持多级功耗状态切换，系统按任务负载与电量自动/手动切换）[9][10]：

| 模式 | 典型功耗 | 核心行为 | 适用场景/切换条件 |
|---|---|---|---|
| 正常帧率模式 | ~1280mW（整板） | 全帧率推流、AI 检测、联网、音视频完整工作 | PIR 触发/人形检测事件/远程预览进入 |
| AOV 低帧率模式 | ~180mW（整板）/ ~122mW（评估板） | SoC 低帧率主码流录像，WiFi/4G 保活在线 | 空闲时段且电量充足；连续 N 帧无目标退回 |
| 低功耗保活模式 | 更低（SoC 下电，核心板 7mW 值守/待机宣传 1mW） | SoC 下电休眠，仅 WiFi/4G 保活监听唤醒 | 空闲且电量偏低时进入 |

**（b）君正 Atlas 大小核状态机**[5][6]：

- **休眠态**：CPU 部分电源关闭、仅保 DDR 供电（self-refresh 暂存现场）、外设电源关、sensor 进 standby；仅 DDR + 协处理器 PMU 工作（优秀者 40mW 级，含周期出图；纯 STR 休眠宣传 1mW 级 [1]）；
- **唤醒态**：协处理器 PMU 经定时计数或外部 IO 触发 → 主控制器/外设重新上电 → 驱动恢复 → 应用程序借助内存暂存技术从休眠前状态继续运行（常电功耗数百 mW~2W [6]）；
- 小核常驻：接收 PIR、低帧率采集、NPU 轻量模型、管理休眠/唤醒逻辑；大核/VPU/高清 ISP 深度休眠（时钟关断或降压）[5]。

**状态切换条件矩阵**（综合各方案）[5][6][9][10][41]：

| 触发 | 方向 |
|---|---|
| PIR/GPIO 触发 | 休眠 → 唤醒（抓拍/录像） |
| AI 检测到人形/车辆（值守帧内） | AOV → 正常帧率 |
| 连续 N 帧（如 5 帧）无目标 | 正常帧率 → AOV |
| RTC 定时（alarm） | 休眠 → 单帧采集 → 休眠（AOV 心跳） |
| App/云端远程预览、DP 下发 | 任意低功耗态 → 正常模式 |
| 电量低于阈值 | AOV → 保活模式/深度休眠（关闭视频值守）；上报低电量告警 |
| 太阳能充电输入充足 | 允许提高占空比/帧率（能量中性调度 [46]） |
| 事件录像+上传完成 | 正常 → AOV/休眠（"录像事件推送完成后才可以休眠" [42]） |

### 4.2 各状态功耗数量级汇总（跨厂商对照）

| 状态 | 功耗数量级 | 实测/宣传数据点 |
|---|---|---|
| 全速 Active（编码+AI+网络推流） | **1~3W+** | T41 ISP 全速 1080p30 整机 1.2~1.5W（不含 sensor/DDR）[31]；RV1126B 整板全帧率+AI 1280mW [9]；传统 IPC 持续全帧率录像整机通常 3W 以上 [9] |
| 空闲（出流停止但未休眠） | **数百 mW** | RV1126B 整板空闲 580mW [9] |
| AOV 值守（低帧率录像+网络保活） | **40~180mW** | 君正 40+mW [1]；RV1106 ~40mW [3]；CV610 80mW [15]；RV1126B 整板 122~180mW [9][10]；SSC303/306 工作功耗典型 300mW（含动态降频/模块休眠）[50] |
| STR/深度休眠（DDR self-refresh + PMU 驻留） | **1~40mW** | 君正 T41ZM/ZG 休眠 1mW 级 [1]；RV1126B 待机 ~1mW（AOV3.0 宣传）[12][13]；RV1126B AOV 值守核心板 7mW [11]；"做得比较好的芯片 40mW 休眠功耗"（含 DDR 保持与周期出图的工程口径）[6]；传统方案休眠 >100mW [13] |
| 网络保活（SoC 下电，仅无线链路） | **mA~μA 级（链路侧）** | WiFi STA 省电模式 ~5mA（对比 Active ~50mA）[40]；4G Cat.1 PSM <5μA（移远 EC600U）[6] |
| 关机/仅 RTC+POR | **μA 级** | sensor 待机 <10μW（思特威快启 CIS）[18]；RTC 独立供电域（CV610 集成独立供电 RTC）[14]；SSC303/306 待机 μA 级 [50] |

> 注意口径差异：芯片级宣传值（1mW）通常指 SoC 休眠态裸片/核心板功耗；方案级数值（40~80mW）多含 DDR 保持、sensor standby、周期出图摊分与板级静态电流；整板实测（122~180mW）再叠加 WiFi 保活与板损。对比时必须核对测试条件 [1][9][10][11][15]。

### 4.3 对 OpenHarmony L1（LiteOS-A）的适用性分析

- **状态数量建议 4~5 级**，与 LiteOS-A 原生 4 档（NORMAL/LIGHT/DEEP/SHUTDOWN）[35] 天然对齐：
  - `Active`（全速）→ NORMAL_SLEEP 档不介入；
  - `AOV 值守`（单帧循环）→ DEEP_SLEEP + RTC 定时唤醒的应用层循环；
  - `Standby/STR`（纯休眠，网络保活交给 WiFi 芯片）→ DEEP_SLEEP；
  - `Hibernate/Soft-off`（仅 RTC/POR，冷启动恢复）→ SHUTDOWN 档 + 快启路径（第 1 章）。
- **切换条件集中管理**：OpenHarmony L1 电源管理子系统（powermgr_lite 的 small 形态）已提供 RunningLock（`RUNNINGLOCK_BACKGROUND` 保持 CPU 运行、`RUNNINGLOCK_SCREEN`、`RUNNINGLOCK_FLAG_WAKEUP_WHEN_ACQUIRED` 加锁即唤醒）与 `SuspendDevice(reason)/WakeupDevice(reason)` 服务化接口（含 APPLICATION/TIMEOUT/POWER_BUTTON 等挂起原因、PLUGGED_IN/CAMERA_LAUNCH/WAKE_KEY/WAKE_MOTION 等唤醒原因的枚举）[36][37]——状态机可直接构建在该服务上：业务模块用 RunningLock 表达"不许睡"，策略模块调用 SuspendDevice 入眠。
- **电量/充电状态接入**：L1 电源管理子系统含轻设备电池服务（battery_lite）[37]，低电量降档（AOV→保活）与太阳能输入升档可订阅电池状态实现。
- **防误睡/防睡死**：借鉴 Linux wakeup_count 竞态处理 [27] 与 WS53 sleep veto [38]，休眠入口前必须原子检查"锁计数 + 未决唤醒事件"；同时给每个状态设看门狗（如 AOV 循环超过 37h 上限保护 [9]）。

---

## 5. 存储与网络链路省电

### 5.1 SD 卡/SD NAND 低功耗写入策略

**（a）存储介质功耗分级**（以 SD NAND 为例）[43]：

| 层级 | 机制 | 电流 | 唤醒代价 |
|---|---|---|---|
| Idle（空闲） | 读写完成自动进入，控制器仍工作 | ~1-3mA | 最低，立即响应下一命令 |
| Clock Gating（时钟门控） | 不切电源，主控停发 CLK | 数百 μA | 最快，恢复时钟若干周期即可通信 |
| Sleep/断电 | 切断 VDD（MOS 管电源开关） | ~130μA | 需完整上电初始化流程 |

**（b）断电/上电时序合规**（唤醒可靠性关键）[43]：

- 断电：VDD 需降至 0.5V 以下并保持 ≥1ms（保证内部状态机完全复位）；VDD 滤波电容不宜过大（参考 2.2μF），否则电压泄放过慢违反时序；
- 上电：0V→2.7V 爬升时间须在 0.1~35ms 内且无台阶/回沟（防欠压保护误触发）；上电后先发 ≥74 个时钟脉冲再发 CMD0 复位；初始化阶段时钟 <400kHz，成功后才可提速（SD2.0 最高 50MHz / SD3.0 208MHz）；
- 电源开关用低内阻 MOS 管而非三极管（数千次开关后三极管性能衰退会引发供电不足→不可纠正 ECC 错误）；
- 实测案例：ESP32-S3 + SD NAND，非采样时段切断 VDD、采样前 2ms 恢复供电并初始化——休眠态 3mA→130μA，整机平均 15mA→6mA，续航 +66% [43]。

**（c）写入策略与文件系统**

- **休眠前卸载/去初始化 SD 驱动**：RKADK AOV 流程在进入休眠前显式卸载 SD 卡驱动（连同以太网/USB/SDIO），唤醒后再恢复——避免 SD 控制器/PHY 在休眠期漏电，也防止休眠中卡状态不一致 [9]；
- **批量/缓存写入**：涂鸦 AOV 存储设计——AOV 录像先进专用 `AOV buf`（与常规 ringbuf 区分），**"缓存达到最大限制时，或事件触发唤醒主控后"才开始写本地/上传云端**；每段 AOV 录像标注最后一帧，写入线程自动收尾并回调通知 [42]。即写入按"攒批-一次性落盘"组织，减少卡的唤醒次数与碎片写；
- **文件组织**：分段文件（时间轴友好）、跨天切换新目录、前段结束时间=后段开始时间保证回放时间轴无缝、I 帧优先写入、AOV 段不带音频（回放自动静音）[42]；
- **掉电安全**：文件存储方式的固有风险是"最后一个录像文件因异常断电丢失/不可用"（MP4 moov 未落盘），流式存储则有"需缓存若干秒数据、内存开销大、私有格式"等问题——电池设备休眠/断电频繁，需选择抗掉电的容器格式或定期落盘索引 [52]；休眠前 `sys_sync()` 同步文件系统也是 Linux STR 标准步骤 [27][28]；
- **写入期间禁止系统休眠**：Zephyr 提供 `pm_device_busy_set()/pm_device_busy_clear()` 保护"正在写 flash/SD 的设备"不被系统 PM 挂起（挂起中会导致未定义行为/数据不一致）[32]——L1 等价物是写操作期间持有 PM 锁。

### 5.2 Wi-Fi 省电模式（DTIM/PS-Poll/Light-sleep）

**（a）协议机制**（IEEE 802.11 省电模式）[39][40]：

- STA 长时间监听信道能耗大 → 协议引入省电模式：**AP 缓存进入省电态 STA 的单播包，周期发含 TIM 的 Beacon；TIM 指示有无缓存单播包，DTIM（每 n 个 Beacon 一次，n 由 AP 决定）额外指示广播/组播缓存**。TIM 非必听、DTIM 必听 → STA 只在 DTIM 帧前醒来打开 RF，其余时间关射频休眠 [39]；
- Beacon 典型间隔 100ms：DTIM=1 每 100ms 醒一次（延迟 ~100ms、功耗高）；DTIM=3 → ~300ms 延迟、功耗约 1/3；DTIM=10 → ~1s 延迟、功耗约 1/10 [40]；
- 唤醒窗口时长由四因素决定：时钟偏差（time offset）、Beacon 漏听处理时间、为突发数据预留的 active 时间、IDLE 进入条件 [39]；
- **功耗三要素模型**：`interval`（醒来间隔，越大越省但响应越慢）、`period`（每次工作时长，越短越省但可靠性下降）、`base current`（射频不工作时的底电流，由休眠深度决定）[39]；
- 模式阶梯（ESP-IDF）：**Modem-sleep**（仅关 PHY/射频，CPU 保持运行，按 DTIM/listen interval 自动醒来，适合 CPU 需持续工作的场景如本地语音唤醒）→ **DFS + Modem-sleep**（空闲期降 CPU/APB 频率，Wi-Fi 任务持 `ESP_PM_CPU_FREQ_MAX` 电源锁保证收发时全速）→ **Auto Light-sleep**（空闲超时自动进 light-sleep：关 RF、8MHz/40MHz 晶振、PLL，门控数字内核时钟、暂停 CPU；仍遵循 DTIM 自动苏醒保持连接）[39]；
- listen interval 可协商（如 `power_save_set_listen_int(10)`）：越大越省电，但延迟与丢包风险增大 [BK7252N 文档，经 [39] 同类机制归纳]。

**（b）整机链路保活架构**

- **双芯片协同**：视频主控 SoC 深度休眠期间，由 WiFi 芯片（或配套低功耗 MCU）进 DTIM 模式维持连接与心跳，监听路由器 Beacon；MCU 同时负责电量监测、PIR 管理、经 UART 向主控发休眠/唤醒指令 [7]；
- **云侧远程唤醒**：设备需具备"低功耗 IPC 业务能力"，保证休眠时可通过预览/DP 配置远程唤醒 [41]；实现上 WiFi 模块持续与服务器保持心跳长连接，收到指令后唤醒主控（专利方案）[49]；
- **状态上报**：休眠前上报"休眠态"（DP149=false），唤醒后补报"唤醒态"（true），App 侧据此展示设备在线状态 [41]；
- 常用低功耗 WiFi 器件：海思 Hi3861L（极低功耗、快速连接）、爱科微 AIC8800（WiFi6 低功耗）；部分主控 SoC 集成 WiFi MAC+PHY（如君正 T41）进一步降低休眠功耗与成本 [6]。

**（c）4G 链路省电**：4G 模组平时置于 PSM（省电模式）或深休眠，主控经 AT 指令唤醒模组、传输完成立即回睡（如移远 EC600U/EG912Y PSM 模式 <5μA；合宙 Air780 支持 PSM+休眠）[6][8]。

### 5.3 事件上传策略

- **触发即传**：PIR 触发 → 唤醒 → 抓拍图片 → 经 SDK 上报 → 消息推送（涂鸦 DP115 移动侦测透传 + DP212 报警消息）[41]；
- **上传完成才可休眠**：低功耗设备"录像事件推送完成后才可以休眠"，否则云存片段高概率上传失败 [42]——上传窗口是休眠的前置条件，需纳入 PM 锁管理；
- **批量上传**：AOV 录像攒批到缓存上限或事件唤醒时统一上传；上传期间无事件则新数据继续进 AOV 缓存待下轮；有事件则切正常模式走常规 ringbuf 上传；AOV 段与事件段并发上传时需做优先级控制并考虑带宽限制 [42]；
- **值守期轻量上报**：AOV 周期唤醒时可选"上传一帧到云端"作为活动快照 [6]；
- **时间轴一致性**：云存上传耗时会造成录像空洞，需让下一段录像起始时间覆盖上传间隙，App 时间轴渲染才无缝 [42]。

### 5.4 关键数值

| 指标 | 数值 | 来源 |
|---|---|---|
| WiFi STA Active vs Power Save | ~50mA（<1ms 延迟） vs ~5mA（100ms~1s 延迟） | [40] |
| DTIM=1/3/10 | 延迟 ~100ms/300ms/~1s，功耗比例 1 : 1/3 : 1/10 | [40] |
| SD NAND Idle/门控/断电 | 1-3mA / 数百 μA / ~130μA | [43] |
| SD 断电恢复时序 | VDD<0.5V 保持 ≥1ms；上电爬升 0.1~35ms；≥74 clk 后 CMD0；初始化 <400kHz | [43] |
| SD 断电优化案例 | 整机 15mA→6mA，续航 +66%（提前 2ms 上电初始化） | [43] |
| 4G Cat.1 PSM | <5μA（EC600U） | [6] |
| AOV 定时休眠上限 | 37 小时（RKADK 参数，单位 ms） | [9] |

### 5.5 对 OpenHarmony L1（LiteOS-A）的适用性分析

- **SD 驱动 PM 回调**：L1 的 SD/SDIO 驱动应实现 LiteOS-A `LosPmDevice.suspend/resume`（休眠前 flush+去初始化+可选断电，唤醒后按 74clk/CMD0/低速初始化时序恢复）[35][43]；写入路径用 `LOS_PmLockRequest`/`LOS_PmTimeLockRequest`（带超时自动释放，防死锁）保护 [35]。
- **攒批写入天然匹配占空比循环**：AOV 帧先在 RAM 环形缓冲聚合，按"缓存满或事件"落盘 [42]；L1 内存有限，批大小 = min(可用 RAM, 卡单次写入能效最优块大小)，并在每次唤醒窗口内完成"写卡→sync→解锁→休眠"闭环。
- **WiFi 保活职责外移**：若采用 WiFi SoC 集成方案，L1 主控深睡时依赖 WiFi 固件的 DTIM 保活+UART 唤醒（等同 [7] 架构）；若 WiFi 由 L1 主控直驱，则必须实现 Modem-sleep/Light-sleep 阶梯 [39]，此时主控无法真正 STR，功耗下限受 base current 约束——**方案选型时应优先考虑"主控可完全下电、WiFi 芯片自主保活"的架构**。
- **上传完成前禁止休眠**：在 L1 状态机中将"事件上传完成"设为释放 BACKGROUND RunningLock [36] 的条件，天然利用锁机制实现 [42] 的约束。
- **时间同步**：休眠期 tick 停走，唤醒后需用 RTC 校时并修正录像时间戳（时间轴连续性约束 [42]），L1 文件系统时间戳与分段命名都依赖该校准。

---

## 6. RTOS 层低功耗框架

> 本章对 FreeRTOS、Zephyr、Huawei/OpenHarmony LiteOS（-M/-A）、Linux 的公开文档与源码做通用归纳，抽象出 L1 低功耗框架应具备的四件套：**tickless idle、wakelock/锁机制、DVFS、驱动 PM**。

### 6.1 tickless idle（无节拍空闲）

**原理**：周期性 tick 中断迫使 CPU 频繁退出深睡，"进出低功耗态的能量与时间开销可能超过省电收益"；tickless 即在**所有任务都阻塞/挂起的空闲期停掉 tick 定时器**，让 MCU 保持深睡直到中断或下一个任务超时点，醒来后**用低功耗定时器读数补偿 tick 计数** [33][34]。

- **FreeRTOS**：`configUSE_TICKLESS_IDLE=1/2` 启用；当且仅当（1）idle 任务是唯一可运行任务、（2）距下一个任务出阻塞态还有 ≥`configEXPECTED_IDLE_TIME_BEFORE_SLEEP` 个完整 tick 时，内核调用 `portSUPPRESS_TICKS_AND_SLEEP(xExpectedIdleTime)`（参数=可安全深睡的 tick 数）；`eTaskConfirmSleepModeStatus()` 返回 `eNoTasksWaitingTimeout` 时可无限期深睡；调用前挂起调度器、停 tick 源与进睡眠之间需小临界区防竞态 [33]。
- **Zephyr**：idle 线程锁中断后调用 `pm_system_suspend(空闲时长)`，PM 子系统按策略选态；**residency 策略**核心判据：`time_to_next_scheduled_event ≥ state.min_residency_us + state.exit_latency_us` 才进入该状态（退出延迟与最小驻留时间都建模进决策）；支持应用自定义策略 `pm_policy_next_state()` 与自定义 tick 源钩子 `pm_policy_next_custom_ticks()`（把私有硬件定时器纳入唤醒时间决策）[32]。
- **LiteOS（-M/-A 同构）**：组件位于 `kernel/extended/power`（los_pm.c/h），`LOSCFG_KERNEL_PM` 使能；`LOSCFG_KERNEL_PM_IDLE` 决定空闲任务是否走完整 PM 流程（否则每节拍只能浅睡一次、不能跨节拍休眠）；跨节拍休眠依赖 `LosPmTickTimer`（freq/timerStart/timerStop/timerCycleGet/tickLock/tickUnlock 回调，通常绑定 RTC 或 LPTIM 低功耗定时器）：休眠时停 SysTick、启动低功耗定时器，唤醒后读计数补偿系统节拍 [34][35]。`LOSCFG_BASE_CORE_TICK_WTIMER`（64/128 位宽定时器）可免溢出处理 [34]。LiteOS-A 默认 idle 任务为 WEAK 的 `while(1){WFI;}`，平台覆写后接入 `LOS_PmSuspend` [35]。
- **Linux 对应物**：cpuidle 阶梯 + s2idle（在 idle 路径冻结调度、设备进低功耗、CPU 进最深 C-state）[25]。

### 6.2 wakelock / PM 锁机制

| 框架 | 机制 | 语义 |
|---|---|---|
| Linux/Android | wakelock + `wakeup_count` | 服务持锁阻止休眠；无锁时写 `/sys/power/state`；wakeup_count 处理"释放锁到入睡之间出现唤醒事件"的竞态 [27] |
| LiteOS-A/M | `LOS_PmLockRequest(name)` / `LOS_PmTimeLockRequest(name, ms)` / `LOS_PmLockRelease(name)` / `LOS_PmLockCountGet` | 按**当前休眠模式**加锁（持锁则下次进 idle 不进入该模式）；带毫秒超时自动释放（内部软定时器实现），防忘记释放 [34][35] |
| OpenHarmony L1 powermgr_lite | `AcquireRunningLockEntry/ReleaseRunningLockEntry/IsAnyRunningLockHolding` + `RUNNINGLOCK_FLAG_WAKEUP_WHEN_ACQUIRED` | RunningLock 分 SCREEN/BACKGROUND/PROXIMITY 三类；服务化（SAMGR/IPC）跨进程统一管理；带 timeoutMs；加锁可顺带唤醒设备 [36] |
| Zephyr | `pm_policy_state_lock_get()/put()` + 设备约束（`CONFIG_PM_POLICY_DEVICE_CONSTRAINTS`、DT `zephyr,disabling-power-states`、`pm_policy_device_power_lock_get/put`） | 按**电源状态粒度**加锁：组件可阻止系统进入特定状态；设备可声明"哪些状态会断电"，异步操作期间自动锁住这些状态 [32] |
| ESP-IDF | `ESP_PM_CPU_FREQ_MAX`/`ESP_PM_APB_FREQ_MAX`/`ESP_PM_NO_LIGHT_SLEEP` 电源锁 | 锁类型对应调频与浅睡禁止，Wi-Fi 任务自动持锁保证收发性能 [39] |
| WS53（LiteOS 系） | sleep veto | 任一模块持否决则平台不进低功耗 [38] |

**通用设计要点**：锁要带名字/持有者（可观测、可追责，LiteOS 提供 `LOS_PmLockInfoShow` 输出持锁信息 [35]）；锁应支持超时自动释放或死锁检测；锁的粒度最好是"状态级"而非全局"睡/不睡"（Zephyr 模型最细，允许"可以浅睡但不许深睡"的中间表达）[32][35]。

### 6.3 DVFS（动态电压频率调节）

- **Zephyr**：CPU Frequency Scaling 子系统——SoC 以 devicetree `zephyr,pstate` 节点声明 P-state 集合，驱动实现 `cpu_freq_pstate_set()`；策略层（P-state policy，如 on_demand）基于指标（CPU 负载、温度）决策；可选 Thermal Cap 按温度跳变点限制最高 P-state [32]。
- **ESP-IDF**：DFS 与电源锁联动——两把频率锁（CPU/APB）的最高需求决定当前频率，全部释放后降到最低频进 IDLE；Wi-Fi 场景调频只发生在 base current 阶段（任务持锁期保持全速）[39]。
- **Linux**：cpufreq governor 体系（对应 cpuidle 之外的运行态调频）；设备侧另有 runtime PM 自动挂起空闲设备 [26]。
- **AOV 场景的 DVFS**：唤醒瞬间 PMU 动态调高电压/频率恢复大核性能、事件结束后降压降频回休眠（Atlas 唤醒流程）[5]；SigmaStar SSC303/306 支持"动态降频、模块休眠"作为工作态省电手段 [50]；君正 T41 通过"智能电源门控 + 动态帧率"在 40mW 下维持成像 [2]。
- **归纳**：DVFS 与占空比策略互补——**短时唤醒窗口内应全速冲刺（race-to-idle），空闲期降频，长空闲进睡眠**；调频决策必须与 PM 锁互锁（有锁不降频）[39]。

### 6.4 驱动 PM 框架（设备级电源管理）

- **Linux**：`dev_pm_ops` 多阶段回调（prepare/suspend/suspend_late/suspend_noirq + resume 镜像），系统级休眠与运行时 PM（runtime PM：设备空闲自动挂起，引用计数管理）双轨；late/noirq 阶段 runtime PM 被禁用的边界条件是驱动踩坑重灾区 [26][28]；电源域（genpd）作为 provider 管理设备供电轨 [28]。
- **Zephyr** 两种设备 PM 模式 [32]：
  1. **Device Runtime PM**（官方推荐）：驱动/子系统/应用三层经引用计数协调（`pm_device_runtime_get/put`），设备状态机 ACTIVE/SUSPENDING/SUSPENDED/OFF × 动作 SUSPEND/RESUME/TURN_ON/TURN_OFF；系统 PM 无需重复挂起已 runtime 管理的设备，切换电源状态更快；
  2. **System-Managed Device PM**：设备随系统入眠统一挂起（按初始化顺序 suspend、逆序 resume），适合无阻塞操作需求的简单系统；设备返回 -EBUSY 则 CPU 不入眠；
  - 辅助机制：`pm_device_busy_set/clear`（事务保护，如写 flash 期间禁止挂起）、devicetree `wakeup-source` 属性 + `pm_device_wakeup_enable()`（唤醒能力声明）、power domain 作为一等设备对象管理子设备供电 [32]。
- **LiteOS-A/M**：三类注册节点 [34][35]：
  - `LOS_PM_TYPE_DEVICE`（`LosPmDevice.suspend/resume(mode)`，按模式挂起/恢复外设，可注册多个）；
  - `LOS_PM_TYPE_SYSCTRL`（`LosPmSysctrl`：early/late 钩子 + 四档模式各自的 suspend/resume 实现，normalSuspend 必填、其余按需）；
  - `LOS_PM_TYPE_TICK_TIMER`（低功耗定时器，A 核标注 reserved，实际节拍补偿由内核 tick 模块协同）；
  - 入口 `LOS_PmSuspend(wakeCount)` → `OsPmSuspendSleep`：检查锁与模式（OsPmSuspendCheck）→ early/设备 suspend（OsPmSuspendPrepare）→ 停 tick timer → 调 sysctrl 对应档位 suspend → 唤醒后逆序恢复 + tick 补偿 [35]。
- **WS53 LPC（海思 OpenHarmony 轻量芯片）**：`uapi_pm_register_dev_ops(PM_DEV_GPIO, &ops)` 按设备类型注册 suspend/resume；平台全局低功耗策略统一调度；GPIO 唤醒配置含施密特触发/边沿/防抖，ISR 只更新状态、业务放任务态 [38]。
- **OpenHarmony L1 服务层**：powermgr_lite（small 形态）把电源管理做成 SAMGR feature 服务（POWER_MANAGE_SERVICE/FEATURE），提供 RunningLock + Suspend/Wakeup 的 IPC 接口，底层对接内核 PM [36][37]。

### 6.5 框架对比总表

| 能力 | FreeRTOS | Zephyr | LiteOS-A/M | Linux | OH powermgr_lite(L1) |
|---|---|---|---|---|---|
| tickless | `portSUPPRESS_TICKS_AND_SLEEP` [33] | idle→`pm_system_suspend`+residency 策略 [32] | `LOSCFG_KERNEL_PM_IDLE` 跨节拍+tick timer 补偿 [34][35] | cpuidle/s2idle [25] | （依托内核）[36] |
| 锁 | 无内建（应用自理） | 状态级 lock + 设备约束 [32] | 模式级 PM 锁+超时自动释放 [35] | wakelock/wakeup_count [27] | RunningLock 服务化+唤醒标志 [36] |
| DVFS | 无内建 | P-state+policy+thermal cap [32] | 无内建（板级自实现） | cpufreq [26] | 省电模式接口 [37] |
| 驱动 PM | 无内建 | Runtime PM（引用计数）+System-managed 双模 [32] | `LosPmDevice/LosPmSysctrl` 注册制 [35] | dev_pm_ops 多阶段+runtime PM+genpd [26][28] | WS53 式 dev_ops 注册 [38] |
| 电源状态模型 | — | 7 态（ACPI S0~S5 映射）[32] | 4 档 [35] | 4 态（s2idle/standby/STR/hibernate）[25] | Suspend/Wakeup reason 枚举 [36] |
| 唤醒源管理 | 应用自理 | DT `wakeup-source`+`pm_device_wakeup_enable` [32] | 驱动自行配置+`LOS_PmWakeSet` [35] | wakeup source 框架/sysfs [26] | WakeupDevice(reason) [36] |

### 6.6 对 OpenHarmony L1（LiteOS-A）的适用性分析

- **存量资产**：LiteOS-A 内核 PM 组件（4 档模式、锁、tick 补偿、设备/sysctrl 注册）+ powermgr_lite small 形态（RunningLock/Suspend/Wakeup 服务）已覆盖"tickless + wakelock"两件套 [35][36][37]；海思 CV610 官方 SDK 明确支持 OpenHarmony 4.1 [14]，说明 L1/L2 形态在 AOV 级 IPC SoC 上已有落地通道。
- **主要缺口与补法**：
  1. **STR 平台层**：`LosPmSysctrl.deepSuspend/deepResume` 只是空位，DDR self-refresh/PHY retention/电源域序列需 SoC BSP 实现（参照 Linux `suspend_ops->enter` 与 [29][30] 的硬件序列）；
  2. **设备级 runtime PM**：LiteOS-A 无 Zephyr 式引用计数 runtime PM，建议在 `LosPmDevice` 之上封装引用计数与 busy 保护（语义对齐 `pm_device_runtime_get/put` 与 `pm_device_busy_set/clear` [32]），SD 卡/WiFi/ISP 驱动优先接入；
  3. **DVFS**：内核无内建调频框架，可先实现两档（全速/低频）+ PM 锁联动（有 BACKGROUND 锁不降频），够用且简单；
  4. **唤醒源注册与竞态**：补一个轻量 wakeup source 表（使能/计数/原因），休眠入口原子检查，对齐 Linux wakeup_count 语义 [26][27]；
  5. **策略层**：在 powermgr_lite 服务上实现第 4 章的 AOV 状态机（占空比调度、电量降档、上传完成才休眠）。
- **设计准则移植**：Zephyr residency 判据（`空闲时长 ≥ min_residency + exit_latency` 才值得进深睡）应成为 L1 选档的基本公式 [32]；FreeRTOS 的"预期空闲时间阈值"（`configEXPECTED_IDLE_TIME_BEFORE_SLEEP`）同理 [33]——避免为几十 ms 的空闲付出 ms 级唤醒延迟与进出能耗。

---

## 7. 对 OpenHarmony L1 落地的综合启示

1. **总体架构**：目标形态 = "LiteOS-A 主控（可 STR）+ 常驻小核/协处理器或 WiFi MCU（保活+唤醒仲裁）+ 快启 sensor"。君正 Atlas（大小核）[5]、RV1126B（芯片级多级功耗状态）[9]、双芯片 WiFi 保活 [7] 都指向同一结论：**把"值守"与"处理"在硬件上分离，主控要么全速要么全睡，避免中间态**。
2. **状态机四档对齐内核四档**：Active / AOV 值守 / STR Standby / Hibernate ↔ LiteOS-A `NORMAL/LIGHT/DEEP/SHUTDOWN` + powermgr_lite RunningLock/SuspendDevice [35][36]；切换条件矩阵见 4.1（事件、电量、RTC、云端指令）。
3. **功耗预算锚点**（用于立项指标）：全速 1~1.5W、AOV 值守 40~180mW（含 WiFi 保活）、纯休眠 1~40mW、保活链路 μA~mA 级 [1][6][9][11][12][15][40]；平均功耗 ≈ P_sleep + P_wake×duty，唤醒窗口每省 5ms 续航提升近一倍 [6]。
4. **快启路径双保险**：STR 唤醒 <100ms（主路径，依赖 BSP 的 DDR retention 与驱动 resume 优化）[2][10]；冷启动 300~500ms 出图（兜底路径：XIP + 裁剪 + ramfs + 出图驱动提权 + sensor 快启）[19][20][21][22][23]。
5. **占空比循环做成应用层策略任务**：RTC 硬件定时唤醒 → 单帧采集/编码/检测 → 攒批写卡 → （可选）上传 → 立即休眠；进出 AOV 有滞回（连续 N 帧无目标才退回）[5][9][10]；占空比可按电量/活动性/太阳能输入动态调节 [46][47]。
6. **锁机制是防睡死/防误睡的核心**：所有"不许睡"的场景（写卡、上传、OTA、预览）统一走 PM 锁/RunningLock，优先用带超时的 `LOS_PmTimeLockRequest` 防泄漏 [35][36]；休眠入口原子检查锁计数+未决唤醒事件（wakeup_count 语义）[27]。
7. **存储省电三件套**：写操作持锁 + busy 保护 [32]；攒批落盘与休眠前 sync/卸载驱动 [9][42]；SD 供电/时钟门控分级（频繁写→门控，长空闲→断电，断电严格遵守 0.5V/1ms、74clk、<400kHz 初始化时序，MOS 管开关）[43]。
8. **网络保活外移**：主控深睡时由 WiFi 芯片 DTIM 保活 + 心跳长连接 + UART 唤醒主控 [7][39][40][49]；上传完成作为释放锁/允许休眠的前置条件 [42]；4G 场景用 PSM+AT 唤醒 [6][8]。
9. **驱动 PM 框架建议**：在 `LosPmDevice` 上补引用计数 runtime PM 与 busy 标记（对齐 Zephyr 语义），按"越底层越晚睡越早醒"排序 suspend/resume [28][32][35]；唤醒源设备声明 wakeup capability 并支持使能开关 [26][32]。
10. **可观测性**：分段计时（boot 各阶段 TTFF 打点 [20][22]、suspend/resume 各回调耗时 [27][28]）、持锁者列表导出 [35]、唤醒原因记录 [36]、异常掉电计数（存储侧 CMD56 健康寄存器 [43]）——没有测量就没有优化。

---

## 参考文献

> 访问日期均为 **2026-09-10**。标注「官方」的为厂商/项目一手来源；宣传性数值请注意其测试条件。

### 厂商与方案（AOV/芯片/传感器）

- [1] 君正官网（官方）：《君正AOV方案选型指南》（T41ZM/ZG、T32V、T33V 三代方案，休眠 1mW 级、典型功耗 40+mW） — http://www.ingenic.com.cn/news-detail/nid-383.html
- [2] 我爱方案网：《从T41到T33V，解密君正三大代系AOV芯片的突围之路》（Atlas 快启 <100ms、1fps~25fps、MIS80W1 两级唤醒、觅睿案例、存储省 90%） — https://news.52solution.com/news/80059761/
- [3] 我爱方案网：《瑞芯微RV1106/君正T32V AOV方案：7x24小时无遗漏录像》（RV1106G2 1fps≈40mW、5200mAh 14 天、智能编码省 50% 码率） — https://news.52solution.com/news/80062014/
- [4] 搜狐/雷科技：《"录像一直有，充电可以无"——君正已落地新一代低功耗Atlas解决方案》（Atlas 五大技术组成、觅睿 2 电池+5W 太阳能全年、AI+PIR 30 米、门锁毫秒级） — https://www.sohu.com/a/766734485_651994
- [5] 易百纳：《什么是Atlas？读懂IP Camera的"续航秘密"》（大小核架构、休眠/唤醒流程、单帧 suspend-resume、RTC 纳秒级响应微瓦功耗、Linux suspend/resume 流程） — https://www.ebaina.com/articles/140000017746
- [6] CSDN lee_rick：《低功耗AOV电池摄像机介绍》（休眠态 DDR 保电/40mW、唤醒流程、平均功耗公式、WiFi/4G 器件选型、PSM <5μA） — https://blog.csdn.net/lee_rick/article/details/148150102
- [7] CSDN lee_rick：《WiFi Aov的硬件框图》（主控+WiFi/MCU 双芯片、DTIM 保活、UART 唤醒指令） — https://blog.csdn.net/lee_rick/article/details/161391949
- [8] CSDN lee_rick：《4G AOV的硬件系统框图》（主控+4G 模组 PSM+协处理 MCU 三芯片架构） — https://blog.csdn.net/lee_rick/article/details/160865430
- [9] 知乎/眺望电子：《【RV1126B 实战连载 09】AOV低功耗持续录像实测解析》（三模式功耗 1280/580/180mW、AOV 进出流程与外设卸载、定时休眠最大 37h、rkadk_aov_record_test） — https://zhuanlan.zhihu.com/p/2069055163944457663
- [10] 创龙科技：《瑞芯微"低功耗录像技术"，AI节能90%+》（AOV3.0 三模式、1fps ISP 单帧取流+分形检测、5 帧滞回、待机 ~122mW、0.1 秒极速启动、异常声音唤醒） — https://www.tronlong.com/newsinfo49.html
- [11] 飞凌嵌入式（官方产品页）：OK1126BJ-C 开发板（AOA+AOV、休眠持续收音/画面预侦测、WiFi/4G 远程唤醒、AOV 值守核心板 0.007W） — https://www.forlinx.com/product/240.html
- [12] 半导纵横 icviews：《瑞芯微发布AI视觉芯片RV1126B》（AOV3.0 低功耗音频事件唤醒、待机 ~1mW、4 核 A53+3TOPS NPU） — https://www.icviews.cn/news/17868/7
- [13] 搜狐：《AOV 3.0技术加持！低功耗IPC芯片市场风云再起》（传统方案休眠 >100mW/唤醒 2-3s/PIR<10m、AOV3.0 运行态 <40mW/AI 30 米、1 秒 1 帧主流、神眸 AOR 1 秒 5 帧、AOA 概念、GK7206V1） — https://www.sohu.com/a/919901661_121124364
- [14] 海思官网（官方）：Hi3516CV610 芯片页（Cortex-A7 MP2 950MHz、1T NPU、内置 1Gb DDR3/3L、SPI NOR/NAND/eMMC 启动、独立供电 RTC、Linux5.10/OpenHarmony 4.1 SDK、哭声检测 2.0） — https://www.hisilicon.com/cn/products/smart-vision/public-security/IPC/Hi3516CV610
- [15] CSDN 海思开发板总店：《海思Hi3516CV610/Hi3516CV608 AOV源码 低功耗网络摄像机AOV方案》（AOV 运行功耗 80mW@1fps、事件切 15fps、AI 检测 30 米/99%、闲时浓缩录影） — https://blog.csdn.net/yichu5074/article/details/151315879
- [16] 知乎：《海思Hi3516CV610‑00S作用有哪些？》（00S/20S/10B/20B 型号差异、SVAC3.0 比 H.265 省 20% 码率、智能编码 2.0 4MP@30fps≈5GB/天、支持 OpenHarmony） — https://zhuanlan.zhihu.com/p/2035758492875760271
- [17] Gitee shumjj/3516cv610_aov：海思 CV610 KOL（AOV）模式 demo 使用说明（sample_kol：平时 1 秒 1 帧 AOV 录像、aidetect 检出人脸后抓 jpg 并正常录像；SDK《kol模式使用指南》） — https://gitee.com/shumjj/3516cv610_aov
- [18] 思特威 SmartSens 官网（官方）：《物联网专题 | 快速启动技术，低功耗IoT设备进阶必备》（SmartAEC：传统 CIS 启动 >250ms→快启 40/60ms、工作功耗 <60mW、待机 <10μW、第二代支持 AOV 1fps） — https://www.smartsenstech.com/page?id=242
- [50] 搜狐/芯智雲城：《Sigmastar SSC303&306 低功耗视觉芯片产品介绍与应用》（工作功耗典型 300mW、动态降频/模块休眠、PIR 唤醒、待机 μA 级、哨兵/AOV 模式） — https://www.sohu.com/a/981813218_121184240
- [51] 搜狐/芯智雲城：《Sigmastar SSC308DE低功耗IP摄像头解决方案》（双核 A32@1GHz 每核 ≤75mW + Cortex-M4@200MHz 低功耗 IDLE 常驻、内置 1Gb DDR3L） — https://www.sohu.com/a/844904689_121184240
- [53] 百度百科：GK7203V1（国科微，ARM Cortex-A7+RISC-V 双核、0.2T NPU、内置 64/128MB DDR 支持自刷新） — https://baike.baidu.com/item/GK7203V1芯片/66254386

### 快速启动

- [19] CSDN will_yanjx：《IPC启动时间优化》（boot/kernel/rootfs 三阶段：并行加载、提 flash 频率、sensor 提前复位、去内核打印、裁剪、ko 后置、出图驱动提权、ramfs 以内存换时间） — https://blog.csdn.net/will_yanjx/article/details/136819208
- [20] CSDN li_wen01：《君正Zeratul开发(5)——快速启动优化》（T31 官方首帧 200ms、rcS 主程序优先、业务并行、rootfs 精简、dlopen、帧率切换与丢帧策略、DEBUG_TTFF 计时） — https://blog.csdn.net/li_wen01/article/details/115327992
- [21] CSDN：《V833 IPC开发避坑指南：从环境配置到298ms快速出图（Melis4.0）》（全志 V833 RTOS 方案冷启动 ~300ms 出图；正文部分付费） — https://blog.csdn.net/weixin_42620913/article/details/160326512
- [22] RayByte：《系统启动慢如龟速？嵌入式Linux从uboot到用户态的启动时间逐段优化》（uboot 裁剪/bootdelay=0/Falcon 省 300-500ms、内核裁剪/deferred initcall/initramfs/quiet、rcS 并行/readahead/prelink/dlopen 惰性加载、分段测量方法、车载点火<2s） — https://raybyte.cn/post/2026/7/28/0db6b4f3
- [23] ArtInChip 文档中心（官方）：《XIP 方案》（Luban-Lite/RT-Thread：XIP 执行程序节省内存、XIP 数据访问实现快速启动、QSPI 内存映射） — https://aicdoc.artinchip.com/topics/sdk/xip/xip_user_guide-lite.html
- [24] CSDN：《动态库优化——Prelink（预连接）技术》（事先链接代替运行时链接，减少启动时间与内存消耗，适用嵌入式） — https://blog.csdn.net/jxgz_leo/article/details/52870225
- [48] X技术网专利：《一种低功耗网络摄像机的快速启动系统及方法与流程》 — https://www.xjishu.com/zhuanli/62/202310915908.html
- [54] CSDN 文库专栏：《君正T31 IPC摄像头快启优化实战》（T31 平台 500ms 内高质量出图的挑战：sensor 初始化、AE 收敛、首帧过曝） — https://wenku.csdn.net/column/5up3sxzigpx

### STR / 唤醒 / DDR

- [25] Linux Kernel 文档（官方）：《System Sleep States》（s2idle/standby/STR/hibernation 定义、sysfs 接口、mem_sleep） — https://www.kernel.org/doc/html/latest/admin-guide/pm/sleep-states.html
- [26] Linux Kernel 文档（官方）：《Power Management for Devices》（wakeup sources、/sys/.../power/wakeup、device_set_wakeup_capable、RTC alarm/WoL/介质插拔唤醒事件、runtime PM 与系统睡眠的关系、suspend 多阶段） — https://www.kernel.org/doc/html/latest/driver-api/pm/devices.html
- [27] 掘金：《电源管理入门-8 休眠唤醒》（STR/STD 概念、wakelock/wakeup_count/PM core 框架、suspend 全流程源码走读） — https://juejin.cn/post/7290375566255505447
- [28] Xiaolei Wang 博客：《Linux 系统 Suspend/Resume 的 PM 阶段详解》（prepare/suspend/suspend_late/suspend_noirq/syscore/enter 六阶段、runtime PM disable 时机、PM 宏选择、imx8m blk-ctrl 案例） — https://wangxiaolei12.github.io/blog/system-internals/2026-04-22-linux-suspend-resume-pm-stages/index.html
- [29] CSDN 长亭Time：《从AOP到DDR自刷新：图解高通STR/S2R的硬件省电原理》（电压域/时钟树/IP 冻结三维度、SM8450 STR 电流表、AOP 常驻唤醒仲裁；正文部分付费） — https://blog.csdn.net/weixin_33587161/article/details/161905927
- [30] CSDN hierro_zs：《SDRAM中自刷新操作与PHY中Retention功能的关系》（JESD79-3F 自刷新进入/退出时序、CKE/ODT/ZQ 校准、PHY Data_Retention_N 机制） — https://blog.csdn.net/hierro_zs/article/details/68485355
- [31] CSDN zzfmlxs：《君正T41超低功耗ISP的待机唤醒影像架构——0.3W功耗下的运动检测与快照捕获》（T41 RISC-V 协处理器独立检测-决策-唤醒、全速 1.2-1.5W、待机 0.15W/0.22W、sensor VGA 1fps 待机、动态阈值误报 -80%、100ms 抓拍需求；正文部分付费） — https://blog.csdn.net/zzfmlxs/article/details/164052494
- [49] X技术网专利：《一种低功耗远程唤醒网络摄像机及视频监控系统》（WiFi 模块心跳维持服务器连接实现休眠远程唤醒） — https://www.xjishu.com/zhuanli/62/201710728769.html

### RTOS 低功耗框架（官方文档/源码）

- [32] Zephyr Project 文档（官方）：Power Management 系列——Overview / System Power Management（idle→pm_system_suspend、residency 策略、状态锁、custom ticks hook）/ Device Power Management（runtime PM 引用计数、system-managed、busy 标记、wakeup-source）/ pm_state 枚举（ACPI S0~S5 映射）/ CPU Frequency Scaling（P-state、policy、thermal cap） — https://docs.zephyrproject.org/latest/services/pm/index.html 、https://docs.zephyrproject.org/latest/services/pm/system.html 、https://docs.zephyrproject.org/latest/services/pm/device.html 、https://docs.zephyrproject.org/latest/doxygen/html/group__subsys__pm__states.html 、https://docs.zephyrproject.org/latest/services/cpu_freq/index.html
- [33] FreeRTOS 官方文档：《Low Power Tickless Idle Mode》（portSUPPRESS_TICKS_AND_SLEEP、configUSE_TICKLESS_IDLE、configEXPECTED_IDLE_TIME_BEFORE_SLEEP、eTaskConfirmSleepModeStatus、tick 补偿、临界区防竞态） — https://www.freertos.org/low-power-tickless-rtos.html
- [34] CSDN pilihuo：《OpenHarmony Liteos-m 内核低功耗调试》（components/power 移植、LOSCFG_KERNEL_PM/PM_IDLE/TICK_WTIMER 宏、跨节拍休眠原理、4 模式 3 结构体、LOS_PmRegister 实例） — https://blog.csdn.net/pilihuo182175954/article/details/148332858
- [35] OpenHarmony kernel_liteos_a 源码（官方）：`kernel/include/los_pm.h`、`kernel/extended/power/los_pm.c`（4 档休眠模式、LosPmDevice/LosPmTickTimer/LosPmSysctrl、PM 锁 API、OsPmSuspendSleep 流程、tick timer 停走补偿）、`kernel/base/core/los_task.c`（WEAK OsIdleTask: WFI） — https://gitee.com/openharmony/kernel_liteos_a
- [36] OpenHarmony powermgr_powermgr_lite 源码（官方）：`frameworks/src/small/power_manage.c`（RunningLock/SuspendDevice/WakeupDevice 的 SAMGR-IPC 代理）、`interfaces/innerkits/power_manage.h`（SuspendDeviceType/WakeupDeviceType 枚举）、`interfaces/kits/running_lock.h`（RUNNINGLOCK_SCREEN/BACKGROUND/PROXIMITY、WAKEUP_WHEN_ACQUIRED） — https://gitee.com/openharmony/powermgr_powermgr_lite
- [37] OpenHarmony docs（官方）：《电源管理子系统》（base/powermgr 目录：battery_lite/powermgr_lite 轻设备服务、RunningLock、省电模式） — https://github.com/openharmony/docs/blob/master/zh-cn/readme/电源管理子系统.md
- [38] 海思 WS53 开发者中心（官方）：《LPC 低功耗》（uapi_pm_register_dev_ops 设备 suspend/resume 注册、sleep veto、GPIO 唤醒配置与防抖、平台全局低功耗策略） — https://docs.hisilicon.com/projects/fbb_ws53/master/samples/peripherals/lpc/lpc/

### 网络 / 存储省电

- [39] ESP-IDF 官方文档（乐鑫）：《Wi-Fi 场景下低功耗模式介绍》（TIM/DTIM 原理、interval/period/base current 三要素、Modem-sleep、DFS+电源锁、Auto Light-sleep） — https://docs.espressif.com/projects/esp-idf/zh_CN/v5.4.2/esp32c61/api-guides/low-power-mode/low-power-mode-wifi.html
- [40] 海思 WS63 开发者中心（官方）：《省电模式》（Beacon 100ms、DTIM=1/3/10 延迟与功耗比例、Active ~50mA vs Power Save ~5mA、OTA 期间关省电） — https://docs.hisilicon.com/projects/fbb_ws63/master/samples/connectivity/wifi/power-save/power-save.html
- [41] 涂鸦开发者（官方）：《低功耗摄像机方案-TuyaOS》（休眠唤醒/电量显示/告警推送、DP149 唤醒状态上报、PIR 触发抓拍上报、低功耗 IPC 业务能力=远程唤醒） — https://developer.tuya.com/cn/docs/iot-device-dev/tuyaos-package-ipc-device?id=Kcuwpao8ihq38
- [42] 涂鸦开发者（官方）：《AOV 录像本地存储-TuyaOS》（AOV buf 与常规 ringbuf 区分、缓存满或事件唤醒后批量写入/上传、上传完成才可休眠、时间轴连续性、I 帧优先、AOV 无音频） — https://developer.tuya.com/cn/docs/iot-device-dev/tuyaos-package-ipc-device?id=Kcp17u98e8j19
- [43] 知乎/MK米客方德：《SD NAND低功耗模式与唤醒策略》（Idle 1-3mA/时钟门控数百 μA/断电休眠 130μA、上下电时序 0.5V·1ms/0.1-35ms/74clk/CMD0/<400kHz、MOS 管开关、2.2μF 滤波电容、实测 15mA→6mA 续航 +66%） — https://zhuanlan.zhihu.com/p/2065036366740820586
- [52] CSDN hope_wisdom：《媒体存储封装：IPC录像文件管理》（文件存储 vs 流式存储的掉电丢失/内存开销/时间轴权衡；正文部分付费） — https://blog.csdn.net/hope_wisdom/article/details/130859213

### 学术论文 / 专利

- [44] T. Mekonnen, E. Harjula, T. Koskela, M. Ylianttila, "sleepyCAM: Power management mechanism for wireless video-surveillance cameras", 2017 IEEE ICC Workshops, pp.91-96.（PIR+继电器电源门控：等待期 5.4mW vs 1423.6/2162.9mW，>99% 改善，6000mAh→108 天；视觉传感器 >99% 时间等待事件；Wake-on-Wireless 相关工作综述）开放获取 PDF：https://oulurepo.oulu.fi/bitstream/10024/25789/1/nbnfi-fe2019041812810.pdf （条目页：https://www.semanticscholar.org/paper/a0f1876deed79ce600fa7d10acba98a51fda46e5）
- [45] W. Feng, E. Kaiser 等, "Panoptes: scalable low-power video sensor networking technologies", ACM Transactions on Multimedia Computing, Communications, and Applications (TOMCCAP), 2005（802.11 低功耗视频传感平台） — https://dl.acm.org/doi/10.1145/1062253.1062256
- [46] D. E. Ruíz-Guirola 等, "Intelligent Duty Cycling Management and Wake-up for Energy Harvesting IoT Networks with Correlated Activity", arXiv:2405.06372（KNN 自适应占空比，能效-检测精度折中，能量中性运行） — https://arxiv.org/abs/2405.06372
- [47] US11137804B2, "Low power activity monitoring with adaptive duty cycle"（活动监测电路动态调整传感器占空比专利） — https://patents.google.com/patent/US11137804B2/en
- [55] W. H. R. Chan, P. Zhang, I. Nevat, S. G. Nagarajan, A. Valera, H.-X. Tan, N. Gautam, "Adaptive Duty Cycling in Sensor Networks with Energy Harvesting using Continuous-Time Markov Chain and Fluid Models"（能量收集约束下用 CTMC/流体模型做自适应占空比，实现长期能量中性运行，PDF） — https://gamtamu.github.io/gampsu.github.io/papers/duty_jour.pdf

---

*本文档为专题 E（共性技术专题）调研产出；数据以来源为准，工程落地前建议对关键指标（唤醒延迟、各状态功耗、SD 时序容限）在目标硬件上复测。*
