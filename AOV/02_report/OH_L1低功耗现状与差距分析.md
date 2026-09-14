# OH L1 小型系统低功耗现状与差距分析

| 项目 | 内容 |
|---|---|
| 文档名称 | OpenHarmony L1 小型系统低功耗现状与差距分析（AOV 专项·阶段 2） |
| 文档版本 | V1.0 |
| 日期 | 2026-09-10 |
| 分析基线 | `/home/houcq/workspace/oh_release`（manifest 标称 OpenHarmony-6.1-Release；海思 BSP 内容停留在 api_version 8 / bundle 3.1.0 世代，属"新内核老 BSP"） |
| 目标产品 | `ipcamera_hispark_taurus`（hi3516dv300，small/liteos_a，**SMP 双核**）、`ipcamera_hispark_aries`（hi3518ev300，small/liteos_a，**单核**） |
| 上游输入 | 《IPC AOV 业界方案调研报告》§5 映射矩阵（15 项）与三大核心缺口假设 |
| 分析方法 | 4 路并行源码勘察（内核 PM / powermgr 组件 / BSP+HDF PM / 系统能力盘点），全部结论附 文件:行号 证据 |

---

## 1. 结论速览（TL;DR）

1. **内核 PM 是"骨架完整、实现掏空"**：4 档休眠枚举、sysctrl/device 回调时序、带超时 PM 锁、失败回滚、唤醒竞态保护均已就绪且已编入两个海思目标；但三档默认 handler 同为一条 WFI、tickless 补偿是空桩、无 arch 深睡支撑、无 DVFS、无 SMP 从核下线、idle task 不挂钩。
2. **"deepSuspend 空置"假设证实，且是三重空置**：内核占位（WFI）→ 平台零注册（全树无 `LOS_PmRegister(SYSCTRL)`）→ powermgr_lite small 形态挂起循环是 `sleep(10)` 模拟桩。
3. **框架链路意外地全**：HDF PM ↔ 内核 PM 桥（devmgr_pm_reg.c）、驱动 PM listener API、RunningLock→/proc/power→内核锁的真实通路、WiFi hi3881 芯片级 PM+WoWLAN（含 LiteOS 分支）——都在树内，缺的是"最后一公里"平台实现与驱动挂接。
4. **存在一条树内可落地的"浅 AOV"路径**（无需海思 NDA 资料）：WFI-idle + RTC alarm/GPIO 唤醒 + sensor `pfnStandby/pfnRestart` + `HI_MPI_SNAP` 单帧抓拍循环 + media_lite 分段录像，估 1~2 人月；功耗收益为"运行态→WFI+外设时钟停"量级，非深睡级。
5. **CV610 级深睡 AOV 存在硬阻塞**：dv300 的 PMU/电源域/DDR self-refresh 运行时代码树内为零，MPP 内核模块闭源（liteos 全预编译 .a，linux 版 pmops 空桩），uboot 仅预编译 bin——必须获取海思 dv300 低功耗 SDK/KOL 类支持（NDA）才能实施。
6. **AOV 致命缺口——时间连续性**：内核无系统时间 offset 注入点（深睡 CNTPCT 掉电即时间丢失）；NTP 对时链路断（lwip sntp 空桩未编入、无开机 RTC→系统时间同步）——录像时间轴无法保障，必须修复。
7. **平台选型建议**：深睡验证优先 hi3518ev300（单核，规避 SMP 从核无法下线问题）；dv300 双核需先做单核原型或自研从核 park 机制。

---

## 2. 分层现状盘点

### 2.1 内核层（kernel/liteos_a）——PM 框架

编译状态：`LOSCFG_KERNEL_PM` Kconfig **default y**（`kernel/extended/Kconfig:44-49`），两板 kernel_configs 种子未关闭 → **已编入 taurus/aries**；`/proc/power/*` 节点已生成。

| 能力 | 位置 | 状态 | 说明 |
|---|---|---|---|
| 4 档休眠枚举（含 SHUTDOWN） | `kernel/include/los_pm.h:41-46` | ✅ 已有 | NORMAL/LIGHT/DEEP/SHUTDOWN |
| 各档行为差异 | `kernel/extended/power/los_pm.c:109-123,653-673` | ❌ 缺失 | 三档默认 = `OsPmSuspendDefaultHandler`（PRINTK+WFI），行为完全相同；SHUTDOWN 默认 NULL → `LOS_PmModeSet` 直接拒绝（:393-396） |
| PM 锁（含超时锁） | `los_pm.c:503,512,589-622` | ✅ 已有 | `LOS_PmTimeLockRequest(name,ms)` 用软定时器自动释放，可用 |
| 锁→休眠联动 | `los_pm.c:159-179` | ⚠️ 部分 | **全局一票否决**（单一 UINT16 计数器），与头文件"分档否决"文档不符；无法表达"允许 LIGHT 禁止 DEEP" |
| suspend/resume 时序框架 | `los_pm.c:181-227` | ✅ 已有 | early→device.suspend→cpuSuspend→cpuResume→device.resume→late，含失败回滚（prepare 标志）；**关中断+锁调度同步阻塞模型**（ISR 在 late 后才执行） |
| 设备注册 | `los_pm.c:229-240` | ⚠️ 缺陷 | `pm->device` **单指针覆盖**（非链表），后注册者静默顶掉前者；sysctrl 按字段合并稍好 |
| tickless 补偿 | `los_pm.c:86-96` | ❌ 空桩 | `OsPmTickTimerStop` 恒 FALSE；`enterSleepTime` 死字段；TICK_TIMER 类型注册被显式拒绝（:291-293） |
| 动态 tick（空闲不空转） | `kernel/base/sched/los_sched.c:51-86` + `arch/arm/arm/src/arm_generic_timer.c:164-183` | ✅ 已有 | deadline 重编程常态生效（与 PM 解耦），1ms 粒度——LIGHT 场景时间基已正确 |
| **系统时间 offset 注入** | `los_sys.c:38-41` | ❌ 缺失 | `LOS_TickCountGet = HalClockGetCycles()/OS_CYCLE_PER_TICK`，无软件累加/offset 变量 → **深睡掉电即时间丢失（AOV 致命）** |
| OsIdleTask | `kernel/base/core/los_task.c:126-131` | ⚠️ WEAK 未覆写 | 纯 `while(1){WFI;}`，无 PM 钩子；全树无覆写；**SMP 从核走独立路径**（`arch/arm/arm/src/smp.c:99-101`），覆写 OsIdleTask 管不到从核 |
| 休眠自动进入 | — | ❌ 缺失 | `LOS_PmSuspend` 唯一调用点 = `/proc/power/power_count` 调试节点（且权限 0444，依赖 procfs 不校验权限的实现漏洞） |
| DVFS/调频 | 全树 | ❌ 缺失 | 零命中；CPUP 仅统计（`los_cpup.c:342` `LOS_HistorySysCpuUsage`）；`PERI_CRG30_BASE`（CPU 调频 CRG 寄存器）已在 `target_config.h:31-33` 定义但零引用 |
| arch 深睡支撑 | `arch/arm/` | ❌ 缺失 | 无 suspend/resume 汇编；`OsSRSaveRegister/OsSRRestoreRegister`（`los_hw_runstop.S:39-40`）是无调用者的死代码（可作起点）；`cache.S` 只有区间 clean/inv，**无 full cache clean+invalidate**（深睡前置条件不满足） |
| SMP 从核下线 | 全树 | ❌ 缺失 | 无 hotplug；dv300 双核下 core1 永远 WFI，阻碍 SoC 深度电源状态 |
| 唤醒竞态保护 | `los_pm.c:351-359,204-206` | ✅ 已有 | `LOS_PmWakeSet` + suspend 前二次检查；但 `LOS_PmSuspend(wakeCount)` 参数被丢弃，无唤醒源管理 |
| PM syscall | `syscall/` | ❌ 缺失 | 用户态只能走 /proc/power |

### 2.2 组件层（base/powermgr）

| 能力 | 位置 | 状态 | 说明 |
|---|---|---|---|
| powermgr_lite（mini+small） | bundle.json `adapted_system_type:["mini","small"]`，rom 22KB/ram 10KB | ✅ | **taurus 已启用**（config.json:174-180，enable_screensaver=true）；**aries 未启用**（需产品 config.json 追加 + 确认 ipc 依赖） |
| RunningLock 服务化链路（small） | `services/src/running_lock_mgr.c:29-33` → `power/small/running_lock_handler.c:73-85` → `/proc/power/power_lock` → `LOS_PmLockRequest` | ✅ **真实贯通** | 3 锁型映射 3 内核锁名；AOV"录像期禁睡/空闲窗允睡"可直接用 BACKGROUND 锁表达 |
| SuspendDevice/WakeupDevice | `interfaces/innerkits/power_manage.h:25-66`；`power_manage_feature.c:80-98` | ⚠️ 部分 | API+IPC+原因枚举齐全；实现仅 Enable/DisableSuspend（suspendImmed 被忽略）；无权限校验；`WAKEUP_WHEN_ACQUIRED` 标志无消费点 |
| 自动挂起循环（small） | `services/src/power/small/auto_suspend_loop.c:29` | ❌ **桩** | `sleep(10)` 注释原文 "using sleep to simulate suspend"——**假休眠**；mini 版（`mini/auto_suspend_loop.c:24-31`）真调 `LOS_PmReadLock+LOS_PmSuspend`，**照抄即可修复，天级工作量** |
| 挂起准入状态机 | `suspend_controller.c:22,74`（默认持 WakeupHolder 锁，显式 SuspendDevice 才放行）+ `auto_suspend.c`（500ms 轮询+锁计数） | ✅ 骨架可用 | 可复用为 AOV 休眠准入控制 |
| battery_lite | `services/src/battery_device.c:19-28` | ⚠️ 模拟器 | API 全（SOC/充电/健康/电压/温度）但数据源硬编码（soc=80）；接真实电池需替换数据源（`ibattery.h:45-59` IBattery vtable 是接入点） |
| 唤醒源管理 API | — | ❌ 缺失 | 无 RTC 定时唤醒/传感器唤醒配置接口（WakeupDeviceType 仅是原因记录枚举） |
| power_manager/thermal/battery_manager/display_manager | 各 bundle.json | ❌ standard-only | L1 不可用；L1 电源能力仅 powermgr_lite+battery_lite |
| 已知坑 | hispark_taurus_linux | ⚠️ | small 形态 RunningLock 依赖 LiteOS-A 专有 /proc/power → **Linux 内核 small 产品链路失效**，AOV 方案不适用该形态 |

### 2.3 驱动层（HDF）

| 能力 | 位置 | 状态 |
|---|---|---|
| HDF↔内核 PM 桥 | `drivers/hdf_core/adapter/khdf/liteos/manager/src/devmgr_pm_reg.c`（`LOS_PmRegister(LOS_PM_TYPE_DEVICE)` → PowerStateChange(SUSPEND)，失败自动回滚） | ✅ **已有**（LOSCFG_DRIVERS_HDF 默认编入） |
| PM 状态广播链 | `devmgr_service.c:444-476` → `devhost_service.c:167-224` → `power_state_token.c:60-85`（含 DOZE_SUSPEND/RESUME） | ✅ 已有 |
| 驱动 PM API | `HdfPmRegisterPowerListener`（`hdf_device_object.c:62-81`）+ `IPowerEventListener{Suspend,Resume,DozeSuspend,DozeResume}`；注意 HdfDriverEntry 本身无 PM 回调，走 listener 注册 | ✅ 已有 |
| 外设驱动 PM 实现 | 仅 touch（`hdf_touch.c:1087` 含 hcs suspendSeq/resumeSeq）、audio(sapm)、drm_panel 实现；**gpio/uart/mmc/rtc/spi/i2c/timer/watchdog/sensor/wlan-HDI 全部未实现** | ⚠️ ≈缺失 |
| PM 单测 | `framework/test/unittest/pm/hdf_pm_driver_test.c` 等 | ✅ 已有（框架级） |

### 2.4 平台层（device/soc|board/hisilicon）——最大缺口

| 能力 | 现状 | 证据 |
|---|---|---|
| SYSCTRL 注册（deepSuspend/lightSuspend 平台实现） | ❌ **零注册** | 全树 `LOS_PmRegister` 仅 4 处调用，无一在 device/vendor 下注册 SYSCTRL；板级 board.c 中 Pm/Suspend/Idle/Power 全零命中 |
| PMU/电源域/时钟 gating 运行时代码 | ❌ 零 | DDR self-refresh 代码仅存在于 uboot DDR 训练流程（`ddr_training_impl.c:430-462`）；`sys_ctrl.h` 只有 SC_GEN/bootmode，无掉电序列；无 regulator 实体驱动 |
| OsIdleTask 平台覆写 | ❌ 无 | — |
| uboot 快启空间 | ❌ 无源码 | 仅预编译 bin + reg_info_*.bin（DDR/时钟寄存器表）→ 树内无法做 boot 裁剪 |
| MPP 低功耗钩子 | ❌ 闭源 | liteos 侧 vi/venc/isp 全预编译 .a 静态链入内核（`sdk_liteos/mpp/module_init/BUILD.gn`，MMZ 0x88000000/384MB）；linux 侧仅 vo/sys/hdmi/tde/hifb 开源且 pmops 空桩（`vou.c:441` hi_unused），唯一真实现是 TDE（`tde_ioctl.c:966-981`） |
| 调频寄存器 | ⚠️ 定义未用 | `PERI_CRG30_BASE`（cpu freq-mode CRG）已定义零引用；`get_bus_clk()` 硬编码 50MHz |
| DV300 SMP | ⚠️ 约束 | release.config `LOSCFG_KERNEL_SMP=y`，双核 + 无从核下线 |

### 2.5 唤醒源清单

| 唤醒源 | 驱动 | 能力 | 状态 |
|---|---|---|---|
| RTC alarm | `common/platform/rtc/rtc_hi35xx.c`（Alarm 读写:328/354、回调注册:380、中断使能:398、IRQ 处理:655-690）；hcs：dv300 irq=37@0x12080000、ev300 irq=32@0x120E0000 | 断电走时+alarm 中断链路完整 | ✅ **可唤醒 WFI/浅睡**；深睡唤醒域未配置；与内核 PM 零桥接（`LOS_PmWakeSet` 无调用者） |
| GPIO/按键 | `gpio_hi35xx.c`（PL061，IRQ 边沿/电平:316-342，irqStart=48）；input hcs 按键 gpioNum 1/31/32 | IRQ 完整 | ✅ 可作 PIR/按键唤醒；无 PM 回调、无 wake-pin 专用配置（仅 pin hcs `PWR_WAKEUP` 复用定义） |
| WiFi hi3881v100 | `common/platform/wifi/hi3881v100/`：`oal/plat_pm_wlan.c`（1419 行，含 `_PRE_OS_VERSION_LITEOS` 分支）、`mac/hmac/hmac_wow.c`（WoW pattern/wakeup_reason）、API `hi_wifi_api.h:464-478`（HI_LIGHT_SLEEP/HI_DEEP_SLEEP/WOW_PATTERN） | **芯片级 PM+WoWLAN 完整且已适配 LiteOS** | ✅ 已有但未接系统 PM；HDI `SetPowerSaveMode()` 全链路存在（client→hdi→hal `wifi_hal.c:377`→驱动） |
| Timer | `timer_hi35xx.c`（SetOnce/SetTimeout，irq 33/34） | 运行态周期唤醒 | ⚠️ 非深睡唤醒源 |
| UART | uart_hi35xx/uart_pl011 | 无 RX 唤醒、无 PM | ❌ 缺失 |
| Watchdog/Sensor | — | 无 PM | ❌ 缺失 |

### 2.6 AOV 业务相关系统能力

| 领域 | 现状 | AOV 用途/结论 |
|---|---|---|
| 录像链路 | media_lite recorder：**MP4/TS 封装、H264/H265+AAC、SetMaxDuration/MaxFileSize/SetNextOutputFile/FileSplitType 分段录像 API**；camera_lite→海思 HAL（libhdi_camera/libcodec/libplugin_muxer_recorder 预编译）→MPP→FATFS+MMC SD 栈（fsync 可用；`FS_FAT_CACHE_SYNC_THREAD` 默认 n） | ✅ 分段录像可直接用；掉电一致性需应用层 fsync 或开缓存同步线程 |
| 单帧抓拍 | **`HI_MPI_SNAP_TriggerPipe/EnablePipe`**（`sdk_liteos/include/mpi_snap.h:28-32`）；sensor `pfnStandby/pfnRestart`（imx335_cmos.c:1652，liteos 侧同源预编译） | ✅ AOV 单帧循环的关键积木在树内 |
| AI 检测 | ai_engine（small，taurus 已启用 ai_server）+ libnnie_adapter + MPP libnnie/libive/**libmd（移动侦测）**；SVP sample 仅 sdk_linux 下（需移植）；MindSpore Lite/NNRT 无 small 版 | ✅ NNIE wk 模型路线可用 |
| 网络 | lwip 2.1（内核态集成，DHCP/DNS）、hieth-sf 以太网、wpa_supplicant 2.9、curl/mbedtls、dsoftbus/ipc | ✅ 基础齐备 |
| **RTSP/ONVIF** | **无任何组件**（仅 ffmpeg/curl 内部协议源码） | ❌ IPC 标准协议栈需自研/移植（阶段 3 裁剪与按需加载的核心对象） |
| **NTP/时间同步** | time_service standard-only；内核 lwip 不含 apps（LWIPNOAPPSFILES），`fixme.c:391 lwip_sntp_start()` **空桩**；无开机 RTC→系统时间自动同步 | ❌ **AOV 关键缺口**：需移植 lwip sntp.c + SNTP_SET_SYSTEM_TIME 回调 + 开机 RTC 校时 |
| OTA | sys_installer_lite（HOTA 差分+RSA/SHA256）+ libhal_update.so + patchfs/zpfs 防掉电 | ✅ 远程维护可用；下载通道需自行组装（curl+mbedtls） |
| DFX | hilog_lite/hidumper_lite/hievent；blackbox_lite 为 mini-only | ⚠️ small 侧黑盒能力有限；**无 PM 专项计量（TTFF 打点/suspend 耗时/持锁者导出）** |
| KV/配置 | utils_lite kv_store（aries 已显式启用） | ✅ AOV 录像计划/阈值持久化可用 |

---

## 3. 三大核心缺口验证（对照调研报告 §5 假设）

| 假设缺口 | 验证结论 | 修正后表述 |
|---|---|---|
| ① 平台层 deepSuspend/deepResume 空置 | **证实，且为三重空置**：内核默认 handler=WFI（los_pm.c:653-676）→ 平台零 SYSCTRL 注册 → powermgr small 挂起循环 sleep(10) 假休眠 | 好消息：框架链路（内核 PM↔HDF PowerStateChange↔驱动 listener）全部现成；mini 版实现可作 small 修复参照。**真正的深睡实现被 NDA 阻塞**（dv300 PMU/DDR self-refresh 资料树内为零） |
| ② 缺设备级 runtime PM | **部分证伪**：HDF 框架级 PM（listener 注册、状态广播、DOZE、wake token、单测）**已有且已桥接内核**；缺的是**外设驱动侧实现**（gpio/uart/mmc/rtc/sensor/wlan-HDI 全未挂 listener）与 Zephyr 式引用计数+busy 保护语义 | 工作量从"建框架"降级为"逐驱动挂接"（每项 1~2 人周）；device 单指针覆盖缺陷需先修（改链表或产品侧聚合分发器） |
| ③ 缺分段功耗/时间计量 | **证实**：hidumper/hievent 为通用 DFX，无 TTFF 分段打点、无 suspend/resume 耗时、无持锁者导出（`LOS_PmLockInfoShow` 有但仅 printk） | 需自建 PM 埋点体系（阶段 4 方案必含项）；CPUP 统计可作 DVFS 决策输入 |

**新增发现的关键缺口**（调研阶段未预判）：

- **④ 时间连续性双缺口（AOV 致命）**：深睡 CNTPCT 掉电无 offset 补偿（内核必改：`OsGetCurrSchedTimeCycle` 加全局 offset + 唤醒后 RTC 读回累加）；NTP 链路断 + 无开机 RTC 校时。AOV 录像时间轴、文件命名、缩时摄影连续性全部依赖此项。
- **⑤ SMP 从核无法下线**：dv300 双核，core1 停在独立 WFI 路径（smp.c:99-101），深睡收益大打折扣 → 建议 ev300 单核先行验证。
- **⑥ PM 锁全局一票否决**：与文档语义不符，AOV 需要分档锁（"禁 DEEP 允 LIGHT"）；且 `LOS_PmReadLock` 超时硬编码 500ms 恒返 LOS_OK，PM 管理任务需自行循环重试。
- **⑦ 休眠触发入口异常**：`LOS_PmSuspend` 唯一入口 /proc/power/power_count 权限 0444（依赖 procfs 不校验权限的漏洞），无 syscall——产品化必须新增正式触发通道。

---

## 4. AOV 状态机 → 现有能力映射可行性

| AOV 状态（业界 4 级） | 期望落点 | 可行性 | 阻碍与动作 |
|---|---|---|---|
| 全速 Active（15~30fps 录像+推流+AI） | PM 锁持有，不休眠 | ✅ 立即可用 | `AcquireRunningLock(BACKGROUND)`→内核锁链路已通；注意全局否决副作用 |
| AOV 值守（1fps 单帧循环） | LIGHT_SLEEP 档 + RTC alarm 定时唤醒 + MPI SNAP 单帧 | 🟡 **浅 AOV 可行**（树内） | 槽位有、实现缺：LIGHT 默认=WFI 与 NORMAL 无差；需自研 lightSuspend（时钟门控级）+ RTC alarm→PM 唤醒桥接 + 单帧循环业务任务；**不依赖 NDA** |
| STR 深睡（DDR self-refresh+PMU 驻留） | DEEP_SLEEP 档 | ❌ **当前不可用** | 三重硬缺口：时间补偿缺失、无 full cache clean+inv、SMP 从核不下线；平台实现被 NDA 阻塞（dv300 PMU/DDR 资料为零；MPP 闭源只能整模块 deinit/re-init，代价与风险高） |
| 保活/软关机（WiFi PS / 4G PSM，SoC 下电） | SHUTDOWN 档 + hi3881 WoWLAN | 🟡 部分可行 | SHUTDOWN 档被内核主动禁用（handler NULL）需先注册；**hi3881 芯片级 PM+WoW 已就绪**（LiteOS 分支存在），接入系统 PM 为中等工作量；uboot 预编译 → 冷启动快启无树内空间 |
| 降频运行维度（DVFS） | — | ❌ 内核无此维度 | 4 档模型只描述"睡多深"不描述"跑多快"；需绕过内核直操 `PERI_CRG30_BASE` + CPUP 闭环（寄存器地址已给出） |

---

## 5. 差距清单（按优先级，含工作量判断）

### P0 —— 阻塞项（不解决则 AOV 不成立）

| # | 差距 | 落点 | 动作 | 工作量 |
|---|---|---|---|---|
| P0-1 | small 挂起循环是 sleep(10) 桩 | powermgr_lite `small/auto_suspend_loop.c:29` | 照抄 mini 版接 `LOS_PmReadLock+LOS_PmSuspend`（或新增 syscall/修正 proc 权限） | **天级** |
| P0-2 | 休眠无自动进入机制 | 内核 OsIdleTask（WEAK） | 产品侧覆写 OsIdleTask 或建 PM 管理任务（等锁释放→触发 suspend）；注意 SMP 从核例外 | 周级 |
| P0-3 | 深睡时间丢失 | 内核 `los_sched_pri.h:82-85`/`los_sys.c:38-41` | 引入全局时间 offset：休眠前记 CNTPCT、唤醒后 RTC 读回累加（RTC alarm 驱动已就绪） | 周级（**改内核，需评审**） |
| P0-4 | NTP/RTC 校时断链 | third_party/lwip sntp + init | 编入 sntp.c、实现 SNTP_SET_SYSTEM_TIME、开机 RTC→settimeofday、周期校时任务 | 周级 |
| P0-5 | 平台 SYSCTRL 零注册（light/deep 实现） | device/soc 或 board hisilicon | 浅 AOV：自研 lightSuspend（WFI+可控时钟门控）；深睡：**依赖海思 dv300 低功耗 SDK（NDA）——外部硬阻塞** | 浅:月级 / 深:阻塞 |

### P1 —— 显著影响效果

| # | 差距 | 动作 | 工作量 |
|---|---|---|---|
| P1-1 | PM 锁全局一票否决、无分档 | 扩展为按档位锁计数数组（内核改动） | 周级 |
| P1-2 | device 注册单指针覆盖 | 改 LOS_DL_LIST 链表（参照 lockList）或产品侧聚合分发器 | 周级 |
| P1-3 | 外设驱动无 PM listener | mmc/rtc/gpio/uart/wlan-HDI 逐个挂 `HdfPmRegisterPowerListener`（框架已就绪） | 每项 1~2 人周 |
| P1-4 | hi3881 WoWLAN 未接系统 PM | 芯片 PM 已有（含 LiteOS 分支），桥接到 suspend 流程 + SetPowerSaveMode 策略化 | 中等 |
| P1-5 | SMP 从核不下线（dv300） | ~~优先 ev300 单核验证；dv300 关 SMP 做单核原型~~ **【修订：T6 第三批实证 dv300 关 SMP 链接失败（MPP 预编译库依赖 SMP spinlock 符号）】**→ dv300 保持 SMP + 自研从核 park（唯一路线）；单核机制验证用 ev300（MPP 为 .so 形态，依赖性待验证） | 从核 park:月级 |
| P1-6 | 无 DVFS | 直操 PERI_CRG30_BASE 两档调频 + CPUP 闭环（"唤醒全速冲刺、空闲降频"） | 周级 |
| P1-7 | arch 深睡底层（full cache 操作/上下文保存） | 以 `los_hw_runstop.S` 死代码为起点补 full cache clean+inv 与关电序列（配合 P0-5 NDA 资料） | 月级 |

### P2 —— 工程质量

| # | 差距 | 动作 |
|---|---|---|
| P2-1 | 无 PM 计量 | TTFF 分段打点（boot/kernel/init/驱动/出图）、suspend/resume 耗时、持锁者导出（扩展 LOS_PmLockInfoShow）——**无计量则无优化** |
| P2-2 | 唤醒源管理缺失 | 建唤醒源注册/使能接口（RTC/GPIO/WiFi/UART 集合管理），补 wakeup_count 竞态语义 |
| P2-3 | battery_lite 是模拟器 | IBattery vtable 对接真实电量/充电检测（电池 IPC 必需；常电场景可缓） |
| P2-4 | 无 PM 单测/回归 | 补 testsuites pm 用例；`LOS_PmReadLock` 缺陷修复（超时硬编码/恒 LOS_OK） |
| P2-5 | aries 未启用 powermgr | config.json 追加 powermgr 子系统块 + 确认 ipc 依赖 |
| P2-6 | 权限与安全 | SuspendDevice/WakeupDevice 无权限校验；/proc/power 权限位修正 |

---

## 6. 实施路径建议（输入阶段 3/4）

**三步走，先浅后深、先单核后双核：**

1. **第一步：浅 AOV（树内闭环，1~2 人月）**
   P0-1~P0-4 + 浅版 P0-5：修复 small 挂起桩 → 覆写 idle/PM 任务自动进入 → RTC alarm 唤醒桥接 → LIGHT 档实现（WFI+时钟门控）→ MPI SNAP 单帧循环 + sensor standby/restart + media_lite 分段录像 + 攒批 fsync 落盘 → PM 分段计量打点。**产出可实测的 AOV 原型与功耗基线**（预期量级：运行态数百 mW → 值守 WFI 级，具体以实测为准）。
2. **第二步：标准 AOV 增强（2~3 人月，与海思资料获取并行）**
   P1 全部：分档锁、设备链表、驱动 listener 逐个挂接、hi3881 WoW 接入（WiFi 保活+主控浅睡）、DVFS 两档、唤醒源管理、battery 对接。对标业界"AOV 值守 40~80mW"档位。
3. **第三步：深睡 AOV（依赖 NDA，获取后 2~3 人月起）**
   海思 dv300 低功耗 SDK（PMU/DDR self-refresh/电源域序列）→ DEEP_SLEEP 平台实现（arch 底层 + 时间 offset 联调）→ MPP 模块级 deinit/re-init 策略（闭源约束下的唯一路径，需评估 MMZ/ISP 重建代价）→ 对标业界"STR 1~40mW"档位。若 NDA 不可得，**方案上限锁定在浅 AOV+WiFi 保活组合**，指标基线相应下调（阶段 1 报告 §4 的"保底目标"口径）。

**平台策略**：ev300（单核）作为深睡机制验证平台；dv300（双核）作为目标产品平台，SMP 从核 park 列入第三步。

---

## 7. 证据附录（关键文件索引）

| 主题 | 文件:行号 |
|---|---|
| 4 档枚举/Sysctrl 结构 | `kernel/liteos_a/kernel/include/los_pm.h:41-102` |
| 默认 WFI handler/初始化 | `kernel/liteos_a/kernel/extended/power/los_pm.c:653-690` |
| suspend 主流程/回滚 | `los_pm.c:125-227` |
| PM 锁实现 | `los_pm.c:404-632` |
| OsIdleTask WEAK | `kernel/liteos_a/kernel/base/core/los_task.c:126-131`；SMP 从核 `arch/arm/arm/src/smp.c:99-101` |
| 动态 tick | `kernel/base/sched/los_sched.c:51-86`、`arch/arm/arm/src/arm_generic_timer.c:164-183` |
| TickCount 无 offset | `kernel/base/core/los_sys.c:38-41` |
| /proc/power 节点 | `kernel/liteos_a/fs/proc/os_adapt/power_proc.c:61-278` |
| small 假挂起桩 | `base/powermgr/powermgr_lite/services/src/power/small/auto_suspend_loop.c:29`（mini 真实现 `mini/auto_suspend_loop.c:24-31`） |
| RunningLock→内核锁 | `services/src/power/small/running_lock_handler.c:73-85`、`services/src/running_lock_mgr.c:29-33` |
| battery 模拟器 | `base/powermgr/battery_lite/services/src/battery_device.c:19-28` |
| HDF↔内核 PM 桥 | `drivers/hdf_core/adapter/khdf/liteos/manager/src/devmgr_pm_reg.c` |
| HDF listener API | `drivers/hdf_core/framework/core/host/src/hdf_device_object.c:62-81` |
| RTC alarm 链路 | `device/soc/hisilicon/common/platform/rtc/rtc_hi35xx.c:328-710` |
| hi3881 PM+WoW | `device/soc/hisilicon/common/platform/wifi/hi3881v100/driver/oal/plat_pm_wlan.c`、`mac/hmac/hmac_wow.c`、`include/hi_wifi_api.h:464-478` |
| WiFi PS HDI | `drivers/interface/wlan/v1_2/IWlanInterface.idl:100`、`drivers/peripheral/wlan/hal/src/wifi_hal.c:377` |
| MPI SNAP | `device/soc/hisilicon/hi3516dv300/sdk_liteos/include/mpi_snap.h:28-32` |
| sensor standby 钩子 | `sdk_linux/usr/sensor/sony_imx335/imx335_cmos.c:1652-1653` |
| MPP 静态链入/MMZ | `sdk_liteos/mpp/module_init/BUILD.gn`、`src/sdk_init.c` |
| uboot DDR self-refresh（仅训练用） | `device/board/hisilicon/hispark_taurus/uboot/secureboot_release/ddr_init/drv/ddr_training_impl.c:430-462` |
| sntp 空桩 | `kernel/liteos_a/net/lwip-2.1/enhancement/src/fixme.c:391` |
| recorder 分段录像 API | `foundation/multimedia/media_lite/interfaces/kits/recorder_lite/recorder.h` |
| taurus 产品配置 | `vendor/hisilicon/hispark_taurus/config.json:174-180`（powermgr）及全文 |
| Linux 版 MPP pmops 空桩 | `sdk_linux/drv/mpp/cbb/vo/vo_dev/mkp/src/vou.c:441-444` |
