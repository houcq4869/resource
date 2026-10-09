# AOV 系统级低功耗方案设计

| 项目 | 内容 |
|---|---|
| 文档名称 | OpenHarmony L1 小型系统 AOV 系统级低功耗方案设计（AOV 专项·阶段 4） |
| 文档版本 | V1.0（方案设计稿，供评审） |
| 日期 | 2026-09-10 |
| 目标平台 | hi3516dv300（hispark_taurus，双核，目标产品）/ hi3518ev300（hispark_aries，单核，机制验证） |
| 上游输入 | 阶段 1《IPC AOV 业界方案调研报告》（指标基线 §4、映射矩阵 §5）；阶段 2《OH L1 低功耗现状与差距分析》（P0/P1/P2 差距清单）；阶段 3《AOV 业务分析与系统裁剪方案》（三工作期模型、值守期最小集） |
| 设计范围 | 系统层（内核 PM 增强 / powermgr_lite 扩展 / BSP 平台适配 / 驱动 PM 挂接 / 时间连续性 / 快启与计量）；业务层单帧循环给出接口约定，具体业务实现属 PoC 范畴 |

---

## 1. 设计目标与指标

### 1.1 总体目标

支撑 OpenHarmony L1 小型系统低功耗竞争力提升：在 OH small 系统（LiteOS-A）+ 海思 IPC 平台上构建**系统级 AOV 低功耗框架**，实现全天候持续录像（1fps 值守 + 事件全速），并使 OH L1 具备可复用的低功耗基础能力（状态机、PM 锁治理、唤醒链路、时间连续性、计量体系）。

### 1.2 分步指标（承接阶段 1 §4 基线，按三步走分解）

| 指标 | 第一步·浅 AOV | 第二步·标准 AOV | 第三步·深睡 AOV | 业界对标 |
|---|---|---|---|---|
| 值守功耗（整板，1fps，含 WiFi PS 保活） | 建立基线实测（预期数百 mW→WFI 级收益） | **≤80mW（保底）/ ≤45mW（竞争）** | ≤45mW 稳定达成 | 海思 80mW 营销 / 国科微单板 42mW / 君正 T33 26mW |
| STR 深睡功耗（整板） | — | — | **≤40mW（保底）/ ≤10mW（竞争）** | RV1126B 核心板 7mW / 宣称 1mW 级（裸片口径） |
| 唤醒延迟（唤醒源→首帧出图） | ≤1s（RTC 路径实测） | **≤500ms** | ≤250ms（竞争） | 君正 TTFF<90ms / RV1106 250ms |
| 事件切换（AI 命中→15~30fps） | ≤2s | ≤1.5s | **≤1s** | RV1106 1s |
| 冷启动 TTFF（上电→首帧） | 分段打点建立基线 | ≤1.5s | **≤1s** | 全志 V853 700ms |
| 时间连续性 | 值守 24h 时间轴误差 ≤1s | 同左 + NTP 周期校时 | 深睡 7 天唤醒时间误差 ≤1s | — |
| 续航折算（9000mAh） | — | ≥10 天 | **≥13 天** | 觅睿 V7 13~15 天 |
| 存储占用 | ≤1GB/天 | ≤600MB/天 | 同左 | 觅睿 600MB |

**口径纪律**：全部指标按"整板含 sensor、WiFi 保活、25℃、1fps 2MP"口径验收；每项实测附测试条件。

---

## 2. 总体架构

### 2.1 五层架构

```
┌────────────────────────────────────────────────────────────┐
│ L5 业务策略层  aov_policy（状态机主脑）+ 单帧循环业务 + AI检测   │
│    新增：AOV 策略服务（samgr service 或 media_server 内任务）    │
├────────────────────────────────────────────────────────────┤
│ L4 电源服务层  powermgr_lite（扩展）                           │
│    RunningLock(复用) + Suspend准入(复用) + 真实挂起(修桩)        │
│    + WakeSource 管理API(新增) + battery 对接(修模拟器)          │
├────────────────────────────────────────────────────────────┤
│ L3 内核层  kernel/liteos_a PM（增强）                          │
│    分档PM锁(改) + device链表(改) + 时间offset(新增)              │
│    + OsIdleTask挂钩(新增) + 触发通道正规化(改/proc+syscall)       │
├────────────────────────────────────────────────────────────┤
│ L2 驱动/平台层  HDF PM(复用框架) + BSP(新增实现)                 │
│    SYSCTRL注册: lightSuspend/deepSuspend(新增)                 │
│    驱动listener: mmc/rtc/gpio/uart/wlan(逐个挂接)               │
│    MPP模块电源: SDK_exit接管 + deinit/re-init(新增)             │
│    DVFS: PERI_CRG30两档调频(新增) + WiFi WoW桥接(新增)           │
├────────────────────────────────────────────────────────────┤
│ L1 硬件层  hi3516dv300/hi3518ev300                            │
│    RTC(irq37/32) GPIO(irq48+) hi3881(WoW) SD ARM-GTimer       │
│    CRG电源域/DDR self-refresh(第三步,依赖海思低功耗SDK·NDA)        │
└────────────────────────────────────────────────────────────┘
```

### 2.2 功耗状态机（核心设计）

四级状态，与 LiteOS-A 原生四档（`los_pm.h:41-46`）一一映射，由 L5 aov_policy 集中管理：

| AOV 状态 | 内核档位 | 进入条件 | 退出/唤醒 | 系统行为 |
|---|---|---|---|---|
| **S0 ACTIVE**（全速） | NORMAL（PM 不介入，持 BACKGROUND 锁） | AI 命中/用户预览/OTA/充电 | 滞回：连续 N 帧（建议 5，业界同款）无目标且上传完成 | 15~30fps 录像+推流+AI 全开；DVFS 高档 |
| **S1 AOV_WATCH**（值守） | LIGHT_SLEEP | ACTIVE 滞回满足 / 开机默认态 | RTC alarm（1s 周期）单帧循环内醒；GPIO/PIR/WiFi WoW → 升 S0 | 单帧循环：RTC 醒→sensor restart→SNAP 采集→编码→AI/MD→攒批落盘→sensor standby→LIGHT 睡；DVFS 低档冲刺 |
| **S2 STANDBY**（STR 深睡） | DEEP_SLEEP | S1 长时无事件（阈值可配，如 30min）或低电量 | RTC/GPIO/WiFi WoW；唤醒后回 S1 或 S0 | 第三步实现：MPP deinit→驱动 listener suspend→DDR self-refresh→电源域关断；**时间 offset 记录** |
| **S3 SOFT_OFF**（保活软关机） | SHUTDOWN | 极低电量/用户指令 | WiFi WoW 云指令/GPIO 长按；冷启动路径恢复 | SoC 下电，仅 hi3881 PS 保活（~5mA）或 4G PSM；SHUTDOWN 档需先注册 handler（当前内核禁用） |

状态切换强约束（业界共性，写入 aov_policy）：
- **"上传完成才可休眠"**：S0→S1/S2 前置条件 = 事件录像落盘 + 告警上传完成（涂鸦 TuyaOS 同款约束）；
- **低电量降档**：订阅 battery_lite 电量事件，阈值触发 S1→S2→S3 强制降档；太阳能输入升档；
- **看门狗**：S1 单帧循环超时（建议 37h 上限，RV1126B 同款）与 S2 休眠超时由 wdt 兜底，防睡死；
- **竞态保护**：休眠入口原子检查"分档锁计数 + 未决唤醒事件"（复用 `LOS_PmWakeSet` 二次检查机制，补 wakeup_count 语义）。

---

## 3. 子系统方案设计

### 3.1 L3 内核层增强（kernel/liteos_a，5 项改动）

| # | 改动 | 设计 | 触点（阶段 2 证据） |
|---|---|---|---|
| K1 | **分档 PM 锁** | `LosPmCB.lock`（单一 UINT16）→ `lock[LOS_SYS_SHUTDOWN+1]` 按档计数数组；`LOS_PmLockRequestEx(name, mode)` 新 API，原 API 语义保持=否决所有档（兼容）；`OsPmSuspendCheck` 改为"取当前 pmMode 允许的最浅档"（锁否决 DEEP 时自动降级 LIGHT 而非放弃） | `los_pm.c:69,159-179,503`；修复头文件文档与实现不符 |
| K2 | **时间 offset 补偿**（AOV 致命项） | 新增全局 `g_osTimeOffsetCycle`：`OsGetCurrSchedTimeCycle()` 返回值 + offset；suspend 前记录 CNTPCT + 同步 RTC；resume 后读 RTC 换算流逝 cycles 累加 offset；LIGHT 档 CNTPCT 不停走则 offset=0 跳过。配套：`HalClockTickTimerReload/GetTickTimerCycles`（现成原语）实现 `OsPmTickTimerStop/Start` 真实逻辑 | `los_sched_pri.h:82-85`、`los_sys.c:38-41`、`los_pm.c:86-96`、`arm_generic_timer.c:164-183`；RTC 驱动已就绪 |
| K3 | **device 注册链表化** | `LosPmCB.device` 单指针 → `LOS_DL_LIST`（参照 lockList）；suspend 按注册逆序、resume 正序（"越底层越晚睡越早醒"）；单设备失败按现有 prepare 回滚机制处理并记录失败设备 | `los_pm.c:66-82,229-240` |
| K4 | **休眠自动进入 + 触发通道正规化** | 方案 A（推荐）：产品侧覆写 WEAK `OsIdleTask` → `while(1){ LOS_PmReadLock(); LOS_PmSuspend(0); }`（SMP 从核另建 park 钩子，第一步先单核验证）；方案 B：独立 PM 管理任务。修复 `/proc/power/power_count` 权限 0444→0664 + proc_file.c 补权限校验；评估新增 PM syscall（用户态正规通道） | `los_task.c:126-131`、`smp.c:99-101`、`power_proc.c:257-263`、`proc_file.c:595-658` |
| K5 | **缺陷修复** | `LOS_PmReadLock`：超时参数化 + 返回语义修正（区分超时/成功）；`LOS_PmSuspend(wakeCount)` 参数启用（对接 K1 竞态检查）；`SchedTaskFreeze` 扩展为休眠前批量冻结延时任务（减少唤醒源） | `los_pm.c:624-638`、`los_sched_pri.h:605-649` |

### 3.2 L4 电源服务层扩展（base/powermgr/powermgr_lite，4 项）

| # | 改动 | 设计 |
|---|---|---|
| S1 | **修 small 假挂起桩**（P0，天级） | `small/auto_suspend_loop.c:29` 的 `sleep(10)` → 照抄 mini 版：`LOS_PmReadLock()` 等锁释放 → 触发 `LOS_PmSuspend`（经修正后的 /proc 通道或 K4 syscall） |
| S2 | **WakeSource 管理 API**（新增） | innerkits 新增 `RegisterWakeSource(type, config)/EnableWakeSource/DisableWakeSource`；type：RTC_ALARM（周期/单次时刻）、GPIO（引脚+边沿）、WIFI_WOW（pattern）、UART；服务侧维护唤醒源注册表，SuspendDevice 前统一下发到驱动层（经 HDF listener/直接驱动 API），补齐 powermgr_lite 无唤醒源管理的缺口 |
| S3 | **battery 对接真实数据源** | 替换 `battery_device.c` 硬编码：IBattery vtable 接 ADC 电量计/充电 IC 驱动（硬件相关，PoC 阶段可先接 ADC 分压采样） |
| S4 | **SuspendDevice 语义补全** | `suspendImmed` 参数生效（立即挂起 vs 准入放行）；补权限校验（pid 白名单/权限位）；`WAKEUP_WHEN_ACQUIRED` 标志实现（加锁即触发 WakeupDevice 链路） |

### 3.3 L2 平台/驱动层（device/soc|board/hisilicon + drivers，6 项）

| # | 改动 | 设计 |
|---|---|---|
| B1 | **SYSCTRL 注册（核心新增）** | 新增 `device/soc/hisilicon/common/platform/pm/`：`LOS_PmRegister(LOS_PM_TYPE_SYSCTRL)` 实现四档回调——第一步 lightSuspend=外设时钟门控+WFI（可自主实现）；第三步 deepSuspend=full cache clean+inv（新增汇编，以 `los_hw_runstop.S` 死代码为起点）→DDR self-refresh→电源域关断（**依赖海思 dv300 低功耗 SDK，NDA**）；early/late 挂时间 offset 同步点（K2）与唤醒源配置（S2） |
| B2 | **驱动 PM listener 挂接** | 按裁剪后集合逐个挂 `HdfPmRegisterPowerListener`：mmc（休眠前 sync+时钟门控/断电，SD 三级省电策略）、rtc（保持，唤醒源）、gpio（wake-pin 配置）、uart（RX 唤醒，补硬件能力）、wlan HDI（对接 hi3881 芯片 PM）；框架链路现成（devmgr_pm_reg.c 已桥接内核） |
| B3 | **WiFi WoW 桥接** | hi3881 芯片级 PM+WoWLAN 已有（`plat_pm_wlan.c` 含 LITEOS 分支、`hmac_wow.c`、HDI `SetPowerSaveMode` 全链路）：aov_policy 在进入 S1/S2 前调 `HI_WOW_PATTERN_ADD` + `HI_LIGHT_SLEEP/HI_DEEP_SLEEP`，主控睡后 WiFi 保活（DTIM10），云指令经 WoW→GPIO/SDIO 中断唤醒主控；PS 模式参数化（DTIM/listen interval 权衡延迟与功耗） |
| B4 | **MPP 模块电源策略** | `hisi_sdk.c`（HDF_PLATFORM_HISI_SDK）对称接管 `SDK_exit()`（树内已有完整 mod_exit 序列，当前零调用者）：S2 进入前按序 deinit（VO/TDE 等已裁模块不涉及；VI/ISP/VENC 等值守模块 deinit→re-init 或保持最小配置），新增 `HI_SDK_EXIT/INIT` 触发通道 + 循环稳定性验证（PoC 项）；MMZ 重配 384MB→128~192MB + VB 池双档位（阶段 3 §3） |
| B5 | **DVFS 两档** | 直操 `PERI_CRG30_BASE`（`target_config.h:33`，cpu freq-mode CRG）：高档（全速）/低档（值守冲刺），切换点=S0/S1 状态迁移；决策输入=`LOS_HistorySysCpuUsage`（CPUP 已有）；与 PM 锁联动（持锁期间禁降档）；先实测两档功耗/性能曲线再定频点 |
| B6 | **唤醒源硬件配置** | RTC alarm（irq37/32，驱动链路完整）：aov_policy 每周期设置下一唤醒时刻（1s 节拍或缩时 2~4s）；GPIO（PL061 irq48+）：PIR/按键边沿唤醒；唤醒后 GIC 状态恢复检查（深睡场景） |

### 3.4 时间连续性方案（P0，贯穿 L2~L5）

```
冷启动:  uboot → kernel → [init] RTC读时→settimeofday (新增开机校时,pre-init job)
                              ↓
联网后:  time_sync任务: lwip sntp.c编入(替换fixme.c空桩) + SNTP_SET_SYSTEM_TIME回调
         → 周期校时(建议6h) + 校时结果写RTC(RtcWriteTime)
                              ↓
值守期:  每帧录像时间戳 = gettimeofday (RTC为基准,时间轴连续)
                              ↓
深睡:    suspend前: 记CNTPCT+RTC → resume后: RTC差值→g_osTimeOffsetCycle累加(K2)
         → LOS_TickCountGet/gettimeofday 连续,软定时器/录像文件命名/缩时摄影不乱
```

新增 `time_sync` 轻量服务（或并入 foundation 启动任务）：开机 RTC 校时 + SNTP 周期校时 + 校时写回 RTC。触点：`fixme.c:391`（空桩替换）、`third_party/lwip/src/apps/sntp/sntp.c`（编入）、init cfg pre-init job。

### 3.5 值守期单帧循环（L5 业务接口约定）

aov_policy 驱动的 S1 主循环（业务实现属 PoC，此处定系统层接口约定）：

```
loop (周期 T=1s，可配 0.5~4s 缩时):
  1. RTC alarm 唤醒（或已在 LIGHT 睡中被唤醒）
  2. 时间 offset 校验（K2）
  3. sensor restart（pfnRestart，帧消隐≥33ms 约束）
  4. HI_MPI_SNAP_TriggerPipe 单帧采集（mpi_snap.h 已有）
  5. VENC 编码（H.264/H.265，GOP=1 或 I 帧间隔策略，缩时录像标记）
  6. AI/MD 检测（libmd 帧差 或 NNIE 子流 768×448）
     ├─ 命中 → 升 S0（滞回计数器清零，事件录像+告警上传）
     └─ 未命中 → 继续
  7. 攒批落盘（1MB 缓冲满或事件/休眠前 fsync；FATFS）
  8. sensor standby（pfnStandby）
  9. 外设降电（mmc 时钟门控/SD 断电时序、WiFi PS）
  10. 设置下一 RTC alarm → 触发 LIGHT 睡（S1 经 powermgr 准入）
唤醒窗口预算: 步骤3~9 目标 ≤100ms（业界"每省5ms续航近翻倍"），分段打点强制
```

### 3.6 快启（TTFF）与启动重排

承接阶段 3 §5：快启关键路径 = uboot（预编译，树内不可裁，实测记录）→ kernel+MPP 静态模块 init → SD 挂载 → foundation+media_server → AOV 首帧落盘。设计动作：
- init cfg 服务三分组（关键路径 3 个/延迟组 4 个/裁剪组 6 个）；
- 延迟组以"首帧达成"事件为触发（aov_policy 发布 samgr 广播），而非固定 sleep；
- MPP mod_init 序列裁剪（阶段 3 §3 值守集 11 模块优先 init，事件期模块延迟 init）；
- **全链路分段打点**（见 3.7），无打点不验收。

### 3.7 计量体系（P2-1，"无计量则无优化"）

| 计量项 | 实现 | 输出 |
|---|---|---|
| TTFF 分段 | uboot 时间戳（reg_info 阶段打点受限于预编译，用 GPIO 翻转+逻辑分析仪替代）/kernel init 各 level 耗时/MPP mod_init 逐模块耗时（sdk_init.c 插桩）/业务首帧 | 分段瀑布图，每项预算告警 |
| suspend/resume 耗时 | K2 offset 机制顺带记录（进/出 CNTPCT 差），挂 hievent 上报 | 唤醒窗口时间预算达成率 |
| PM 锁审计 | 扩展 `LOS_PmLockInfoShow`：持锁者+持锁时长+超时记录，hidumper 节点导出 | 定位"谁阻止了休眠" |
| 功耗实测 | 硬件：串联功率计（整板）+ 分模块电流探针（sensor/DDR/WiFi/SD）；软件：状态驻留时长统计（aov_policy 记录各态累计时间→换算平均功耗） | 指标验收 + 功耗模型校准（P_avg ≈ P_sleep+(P_wake−P_sleep)×duty） |
| 时间连续性 | 值守 24h/深睡 7d 后校验录像文件时间戳 vs RTC/NTP 真值 | 误差 ≤1s 验收 |

---

## 4. 三步走实施路线（承接阶段 2 §6，含改动清单）

### 第一步：浅 AOV（树内闭环，1~2 人月，ev300 单核先行）

| 交付 | 改动清单 | 仓库 |
|---|---|---|
| 真实休眠触发 | S1 修桩 + K4 idle 挂钩/PM 任务 + /proc 权限修复 | powermgr_lite、kernel/liteos_a、（可选 syscall） |
| LIGHT 档实现 | B1 lightSuspend（时钟门控+WFI）+ B6 RTC alarm 唤醒桥接 | device/soc/hisilicon/common/platform/pm（新增） |
| 时间连续性 | K2 offset + 3.4 开机 RTC 校时 + sntp 编入 | kernel/liteos_a、third_party/lwip、init cfg |
| 单帧循环 PoC | 3.5 主循环（SNAP+sensor standby+攒批落盘+libmd 检测） | 业务 sample（新增，参照 sample_kol 公开实现） |
| 计量基线 | 3.7 TTFF 打点 + suspend/resume 耗时 + 功耗实测方法 | sdk_init.c 插桩、hidumper 扩展 |
| 裁剪第一刀 | 无屏化 7 项 + xts 3 项（低风险先行），依赖核查表前置 | vendor config.json、init cfg |

**验收**：值守循环 7×24 稳定（1 万次唤醒无失败）、时间轴误差 ≤1s、TTFF/唤醒窗口分段数据齐备、整板值守功耗基线实测值（作为第二步目标锚点）。

### 第二步：标准 AOV（2~3 人月，dv300 目标平台）

| 交付 | 改动清单 |
|---|---|
| 内核增强 | K1 分档锁 + K3 device 链表 + K5 缺陷修复 + 冻结扩展 |
| 驱动 PM | B2 mmc/rtc/gpio/uart/wlan listener 逐个挂接（每项 1~2 人周） |
| WiFi 保活 | B3 WoW pattern + PS 参数化 + 主控睡 WiFi 保活链路 |
| DVFS | B5 两档调频 + CPUP 闭环 |
| 服务层 | S2 WakeSource API + S3 battery 对接 + S4 语义补全 |
| 裁剪第二刀 | 软总线族 5 项 + UI/ability 族 + 延迟组按需化（依赖核查后） |
| MPP 优化 | B4 VB 池双档位 + MMZ 重配 + 事件期模块延迟 init |

**验收**：值守 ≤80mW（保底）、唤醒 ≤500ms、事件切换 ≤1.5s、TTFF ≤1.5s、9000mAh 折算 ≥10 天。

### 第三步：深睡 AOV（依赖海思 NDA 资料，获取后 2~3 人月起）

| 交付 | 改动清单 | 前置 |
|---|---|---|
| DEEP_SLEEP 平台实现 | B1 deepSuspend/deepResume：full cache clean+inv 汇编（los_hw_runstop.S 起点）+ DDR self-refresh + 电源域序列 | **海思 dv300 低功耗 SDK/KOL 类支持（NDA 硬阻塞）** |
| MPP 模块电源 | B4 SDK_exit 接管 + deinit/re-init 循环策略 | SDK_exit 稳定性 PoC |
| SMP 从核 park | dv300 双核：从核下线钩子（smp.c 独立路径）或关 SMP 单核产品形态 | 第二步完成 |
| SHUTDOWN 档 | S3 SOFT_OFF：handler 注册 + WiFi WoW/4G PSM 保活 + 冷启动恢复 | — |
| AI 检测升级 | NNIE 人形（子流）替换 libmd，误报与功耗双优化 | ai_engine 延迟加载链路 |

**验收**：STR ≤40mW（保底）/≤10mW（竞争）、深睡 7 天时间误差 ≤1s、唤醒 ≤250ms、续航 ≥13 天（9000mAh）。

---

## 5. 关键设计决策与理由

| 决策 | 选项 | 选择与理由 |
|---|---|---|
| 状态机载体 | a) 新建独立 AOV 服务 b) 扩展 powermgr_lite c) media_server 内任务 | **a+c 混合**：状态机主脑放 aov_policy（samgr 服务，新增），单帧循环业务放 media 侧（数据面与控制面分离）；powermgr_lite 保持通用电源服务定位不绑业务 |
| 第一步验证平台 | dv300（目标）vs ev300（单核） | **ev300 先行**：规避 SMP 从核问题（阶段 2 P1-5），机制验证后平移 dv300；两板 MPP 库不同构（hi3516ev200_* .so），业务层接口按平台无关设计 |
| 深睡路径 | a) 等 NDA 资料做 CV610 级深睡 b) 树内浅 AOV+WiFi 保活组合 | **双线并行**：a 为上限路线（指标对标业界），b 为保底路线（NDA 不可得时方案上限锁定，指标按阶段 1 §4 保底列验收）；外部依赖即刻启动确认 |
| PM 锁兼容 | 改原 API 语义 vs 新增 Ex API | **新增 `LOS_PmLockRequestEx(name, mode)`**：原 API=否决所有档（存量兼容），Ex 版分档；powermgr_lite running_lock_mgr 三锁名映射到 Ex 版 |
| 时间补偿位置 | 内核 offset vs 仅应用层校时 | **内核 offset（K2）必做**：LOS_TickCountGet 是软定时器/超时/日志时间戳的公共基，应用层无法兜底；RTC 校时（3.4）解决绝对时间，两者正交 |
| MPP 电源策略 | 模块 deinit/re-init vs 通道级启停 | **通道级优先（第一步），模块级补充（第三步）**：HI_MPI VI/VENC stop-start 代价小、闭源风险低；模块级 deinit 仅深睡前执行（SDK_exit 需先 PoC 验证） |
| 唤醒节拍 | 固定 1s vs 自适应缩时 | **可配 0.5~4s + 自适应**：对标君正（0.5~4fps 缩时）；无事件超时后拉长间隔（省电），事件后恢复 1s（防漏录），策略参数入 KV |

---

## 6. 风险清单

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| R1 | 海思 dv300 低功耗 SDK（PMU/DDR self-refresh）NDA 不可得 | **高**（第三步硬阻塞） | 即刻启动商务/技术渠道确认；保底路线 b（浅 AOV+WiFi 保活）先行，指标口径同步下调预期；评估 ev300/其他平台资料可得性 |
| R2 | MPP 闭源，deinit/re-init 稳定性未知（SDK_exit 零调用历史） | 高 | 第一步 PoC 专项验证（1000 次循环）；不通则退回通道级启停+浅睡上限 |
| R3 | 内核改动（K1~K5）涉及公共仓，上游合入周期与兼容风险 | 中 | 改动最小化+Ex API 兼容策略；产品分支先行，同步准备上游贡献材料（OH 社区低功耗 SIG） |
| R4 | 声明值口径混乱导致裁剪收益不及预期 | 中 | 阶段 3 已声明"实测为准"；第一步建立 size/内存水位基线后再动第二刀 |
| R5 | 双平台（dv300/ev300）MPP 不同构，代码分叉 | 中 | 业务层平台无关接口（单帧循环抽象 HAL），平台差异收敛到 device/soc 适配层 |
| R6 | 关中断同步 suspend 模型（ISR 在 late 后执行）限制唤醒延迟下限 | 中 | 第一步实测唤醒路径耗时分解；超 250ms 目标则评估异步 suspend 改造（大改，慎重） |
| R7 | uboot 预编译，冷启动 TTFF 无法树内优化 | 低 | TTFF 预算中 uboot 段按实测值锁定；长期与海思确认 uboot 源码/快启版可得性 |
| R8 | battery/电量计硬件依赖（现有板无电池） | 低 | PoC 用外部供电+功率计折算；S3 对接留接口，产品化时按硬件补 |

---

## 7. 交付物与下一步

1. 本文档 = 阶段 4 方案设计稿 → **评审动作**：与内核/驱动/业务/测试代表评审 §3 改动清单与 §4 路线，确认第一步范围；
2. **并行前置**（不阻塞评审）：
   - 裁剪依赖核查表（阶段 3 §7.1，RP2 方法逐组件反查 BUILD.gn）；
   - 海思 dv300 低功耗 SDK 可得性确认（R1，决定第三步是否启动）；
3. **下一步（阶段 5）**：按 §4 第一步清单出《PoC 验证计划》：ev300 环境搭建 → 计量基线（TTFF/功耗打点先行）→ S1 修桩+K4 → LIGHT 档+RTC 唤醒 → 单帧循环 → 1 万次唤醒稳定性 → 浅 AOV 功耗基线报告。
