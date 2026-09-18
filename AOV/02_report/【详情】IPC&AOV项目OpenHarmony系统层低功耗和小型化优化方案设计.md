# IPC&AOV项目OpenHarmony系统层低功耗和小型化优化方案设计

## IPC AOV 业界方案调研报告

### 1. AOV 定义与业务价值

#### 1.1 定义

AOV（Always-On Video，全天候持续录像/全时录像）：**基于超低功耗内存（DDR self-refresh）的快速启动待机技术，实现电池 IPC 7×24 小时不间断录像**。2023 年 CPSE 由北京君正首发（T41），海思在 SDK 层将其命名为 **KOL 模式**（官方方案品牌"越影 S610"），瑞芯微有官方 AOV 产品系列（RV1106G2 / RV1126B "AOV 3.0"）。

#### 1.2 业务价值：解决 PIR 触发式的三大痛点

| 痛点 | PIR 事件触发式 | AOV 全时录像 |
|---|---|---|
| 漏录 | 事件间隙无画面，事后无完整证据链 | 7×24 不间断，0 漏报（觅睿产品口径） |
| 检测距离 | PIR <10m，受热源/天气影响 | 图像 AI 检测 25~70m（日 30m/夜 20m 典型） |
| 误报 | PIR 误触发功耗与体验双损 | AI 人车过滤，误报大幅下降（帧差+光感动态阈值可再降 80%） |

#### 1.3 竞争格局结论

- **AOV 是中国芯片生态主导的差异化路线**：君正、海思、瑞芯微、国科微、安凯微、富瀚微、全志、星宸均已布局；国内终端品牌（萤石、Tapo/TP-LINK、小米、乐橙、觅睿、海康）2024 年起全面 AOV 化。
- **国际四强（Ring/Arlo/Wyze/eufy）电池机均无 AOV**：其 24/7 连续录像强制"常电 + 订阅 + 云存储"（Ring Home Premium $19.99/月、Arlo Secure 云 30 天），与 AOV"电池供电 + 本地缩时存储 + 免订阅"形成鲜明路线差异。Ambarella 布局最早（S2Lm 2015 唤醒 <500ms 出流）但不使用 AOV 术语，待机功耗数值从未公开。
- 技术代际基准线：**传统 PIR 方案休眠 >100mW / 唤醒 2~3s → AOV 1fps 值守 ~40mW 级 → AOV 3.0（音频唤醒 AOA）待机 ~1mW 级**。

---

### 2. 厂商方案横向对比

#### 2.1 主控芯片方案对比总表

> ⚠️ 口径警示：各厂商功耗口径不一致（裸片 / 核心板 / 单板含 sensor / 整机含 WiFi），横向比较仅作量级参考。

| 厂商 | 代表芯片 | AOV 值守功耗（公开值） | 深度待机功耗 | 快启公开指标 | 录像占空比策略 | 数据可信度 |
|---|---|---|---|---|---|---|
| **海思** | Hi3516CV610 / CV608（KOL 模式） | **80mW@1fps**（营销口径，不可核实）；开发板整板实测深睡 **350mW** / 浅睡 **610mW**（@5V） | 芯片级全速 CV610 1043mW / CV608 668mW（官方 PDF，无 AOV 态官方值） | sensor 帧消隐 ≥33ms 硬约束；Fast AE 有光 3 帧收敛；曝光参数 4 种光照模式缓存 | KOL 三态机：DEEP 休眠（全 IP 停+sensor standby+DDR STR）→ 唤醒采 1 帧（SINGLE）→ 编码 → AI 检测 → 回睡（默认 1000ms 周期 = 1fps）；事件触发切 ~30fps×15s + JPEG 抓拍 | 头文件/sample 源码权威（Apache-2.0 公开）；80mW 仅营销 |
| **君正** | T41ZM/ZG（一代）、T32VL/VN/VX（二代）、T33VL/VN（三代） | T41 整板全时录像典型 **6mW**（4M@0.1fps 缩时）；T33 AOV-AT 单摄 2M@1fps **26mW**、双摄 44mW；选型指南口径 40+mW | 休眠 **1mW 级**（宣称业内最低） | **TTFF<90ms**，RISC-V 协处理器开机即接管后台任务，恒定百毫秒级 | 无事件 0.5~4fps 缩时；AI 侦测（30~70m）命中切 25fps；黑光全彩 0.01lux | 官网选型指南一手；产品级有觅睿实测口径 |
| **瑞芯微** | RV1106G2、RV1126B（AOV 3.0） | 整机 **~40mW@1fps**（RV1106G2 官方方案口径）；RV1126B 整板 AOV 值守 122~180mW、核心板 7mW | AOA（音频唤醒）待机 **~1mW**（RV1126B） | 250ms 抓图、1s 人脸识别（RV1106 官网） | 1fps 值守 + AI 多目标检测切全速；AOV 3.0 增加异常声源/哭声音频唤醒 | 官网 + TP-LINK 产品实测背书（AOV 降功耗约 90%） |
| **国科微** | GK7206V1 / GK7203V1 | **单板（含 sensor）2MP@1fps 42mW、4MP 50mW**；GK7203V1 近 40mW | STR 待机（机顶盒方案移植），数值未公布 | "大幅降低首帧耗时"（无数值） | STR + DDR 自刷新 + NPU 防误检 | 单板级数字为业界最硬口径 |
| **全志** | V853 / V821 | V821 明确"低速 AOV 工作"档位（数值未公布） | Wi-Fi DTIM10 保活 **180μA@4.2V**（"冬眠级待机"） | 疾风系统：100ms 起 sensor / **200ms 首帧** / 700ms 冷启动全流程 | 双 RISC-V 异构 + XR806 WiFi 芯片 μA 级保活；V853+XR806 门铃 2500mAh 半年续航 | 官方发布会口径 |
| **星宸** | SSC303/306、SSC308DE/QE | 官方从不公布 AOV 态 mW 值；工作功耗典型 300mW | PIR 待机 μA 级 | SSC306 系冷启动首帧 **68ms**；功耗较 308/377 降 60% | A32+M4 always-on 小核值守；SDK 级"哨兵模式" | 官网无功耗数字，靠 SDK/代理商传播 |
| **安凯微** | AK3918AV130 / KM01 | 整机 **30mW@1fps**（官方口径） | 不可得 | 不可得 | — | AV130 年出货千万颗级 |
| **富瀚微** | FH8626V300（AOV 2.0）、MC6321L | **4.5mW@1fps**（方案宣传，口径存疑：整板/芯片、含否 sensor 不明） | 不可得 | 不可得 | AI 高频定点抓拍检测 | 低可信，仅记录 |
| **Ambarella** | CV25/CV28M/CV5/CV72S | 不用 AOV 术语；待机 mW 值从未公开；CV5 8K30 <2W（全速） | 不公开 | S2Lm（2015）唤醒后 <500ms 出 1080p30；S6LM 误报后 <1s 关断 | AI Timelapse 缩时录像；wire-free 优化 | 官方新闻稿/产品页 |
| **联咏+思特威** | NT 系列 + SC301HIOT（SmartAOV™ 整机参考方案） | **整套方案 <40mW@1fps** | sensor 待机 **<10μW** | 快启 sensor 出图 40~60ms（传统 >250ms） | 无事件 1fps 全时录像；事件快启切 30fps（~100mW） | 大联大诠鼎参考设计口径 |

#### 2.2 海思 KOL 模式关键细节（本项目直接对标对象）

来源：Apache-2.0 公开头文件 `ss_mpi_syskol.h` 与 sample_kol 参考实现源码（24 文件，公开可得）。

- **API**：`ss_mpi_syskol_set/get_param`、`ss_mpi_syskol_sleep`、`ss_mpi_syskol_wakeup`、`ss_mpi_syskol_suspend`（下电方案，新版本是否开放待确认）
- **休眠 4 级**（`ot_syskol_param`）：NONE / LIGHT（保 RTSP 在线）/ **DEEP**（全 IP 停 + sensor standby + DDR STR，检测到目标才按需起 RTSP）/ USER（`audio_cken` 位可休眠保留音频 = AOA 基础）
- **采集模式**：NORMAL / **SINGLE**（睡后采 1 帧）——AOV 单帧循环的核心
- **AOV 周期时序**：restart sensor → 采 1 帧 → 编码 → AI 检测（768×448 子流）→ sensor standby → sleep（默认 1000ms → 1fps）
- **唤醒源**：always-on BSP timer（sysfs）、GPIO/input event、RTC、UART、MCU-4G
- **存储策略**：1MB 内存攒批满才落盘（减少 SD IO 唤醒次数）；多目走 MIPI-Switch 轮询 + 卷绕压缩（wrap）
- **老平台差异**：CV100 / Hi3518EV200/EV300 / Hi3516DV300/CV500 **无原生 KOL**，只能靠"外部超低功耗 MCU+PMU 保活 + SoC 下电/STR + 快启"做事件触发型待机，睡眠期存在录像断档
- **生态关键事实**：海思 CV610 官方 SDK 支持 OpenHarmony 4.1，OH + 海思 AOV 硬件通道已有官方背书

#### 2.3 终端产品指标对比（产品级，供反推续航基线）

国内 AOV 产品机制高度趋同：**无事件 1 帧 / 1~3s 间隔缩时抓拍 → AI 检测到人/车切 12.5~15fps 全速录像**。

| 产品 | 电池 | AOV 策略 | 续航宣称 |
|---|---|---|---|
| 觅睿 V7（君正 T41） | 9000mAh | AOV 白天 11mA / 夜间 15mA（实时 209mA）；全天 AOV 录像仅 **600MB** vs 实时 15GB | **全时录像 13~15 天** |
| Tapo C460 | 10000mAh | 1~60s 间隔快照（24/7 Capture） | 官方续航表：**1s 间隔 8 天、60s 间隔 55 天**、标准口径 200 天 |
| TP-LINK TL-IPC16B-F4GE | 5100mAh | 间隔抓图+事件录像 | AOV 9~10 天 / PIR 40~45 天 |
| 乐橙 B7E | 10000mAh+5W 太阳能 | 2s/帧缩时+事件全速 | 日耗电约 10%（100 事件/天） |
| 小米太阳能 4 Pro | 9900mAh+7.6W 太阳能 | 无人 2s/帧缩时（省存储 >90%） | 满电 1 周+ |
| 海康 AOV 4G 球机（参照） | 32Wh+8W 太阳能 | 1fps 定时抓拍+事件 12.5fps | 7 个连续阴雨天（实测约 15%/天） |
| 萤石 HB8 Lite 4G | 5200mAh | AOV 2.0 间隔抓拍 | 未公布 |
| 捷高 DL32A-4G（君正） | — | 休眠 1fps | 50mW（整机口径） |

---

### 3. 共性技术架构归纳

业界 AOV 方案收敛为**五层技术栈 + 一个功耗状态机**：

#### 3.1 功耗状态机（业界收敛为 4 级）

```
┌─────────────┐  事件/AI命中   ┌─────────────┐
│ 全速 Active  │ ◄──────────── │  AOV 值守    │
│  1~3W       │ ────────────► │ 40~180mW    │
│ 15~30fps录像 │  滞回:连续5帧  │ 1fps单帧循环  │
└─────────────┘  无目标退回    └──────┬──────┘
                                    │ 长时无事件/低电量
                                    ▼
┌─────────────┐  RTC/PIR/网络/音频  ┌─────────────┐
│ 保活/软关机   │ ◄──────────────── │  STR 休眠    │
│ μA~5mA      │ ────────────────► │  1~40mW     │
│ WiFi PS/4G  │    唤醒延迟<100ms   │ DDR自刷新+PMU│
│ PSM,SoC下电  │    (新一代)        │  常驻仲裁     │
└─────────────┘                   └─────────────┘
```

各状态功耗数量级（跨厂商对照）：

| 状态           | 功耗数量级        | 代表数据点                                                 |
| ------------ | ------------ | ----------------------------------------------------- |
| 全速 Active    | **1~3W+**    | T41 1080p30 整机 1.2~1.5W；RV1126B 整板全帧率+AI 1280mW       |
| 空闲（未休眠）      | 数百 mW        | RV1126B 整板空闲 580mW                                    |
| AOV 值守       | **40~180mW** | 君正 40+mW；CV610 80mW；RV1106 ~40mW；国科微单板 42mW           |
| STR 深度休眠     | **1~40mW**   | 君正 1mW 级（宣称）；RV1126B 核心板 7mW；工程口径"较好的芯片 40mW"         |
| 网络保活（SoC 下电） | mA~μA 级      | WiFi STA PS ~5mA；4G Cat.1 PSM <5μA；全志 DTIM10 保活 180μA |
| 关机/仅 RTC     | μA 级         | sensor 待机 <10μW；SSC303/306 μA 级                       |

切换条件矩阵：事件（AI/PIR/音频）、RTC 定时、云指令、电量阈值（低电量降档 AOV→保活）、太阳能输入（升档）、**"上传完成才可休眠"**（强约束）。

#### 3.2 第一层：硬件功耗域设计

- **DDR self-refresh**：CKE 拉低内部自刷新（退出需 tXS/ZQ 校准时序），AOV 的地基（"超低功耗内存"即指此）
- **CPU retention / PHY retention**：保持逻辑与信号状态，唤醒免重初始化
- **电源域分域关断 + 时钟树修剪**（MHz→32kHz）
- **低功耗岛常驻**：PMU/AOP 仲裁唤醒源；值守与处理硬件分离——君正 RISC-V 协处理器、星宸 M4 小核、全志双 RISC-V + XR806 WiFi MCU、瑞芯微 AOA 音频通路
- **sensor 低功耗**：standby <10μW、帧消隐 ≥33ms（海思硬约束）、快启出图 40~60ms（vs 传统 >250ms）、in-sensor 检测（Sony IMX500 片上 AI 3.1ms）

#### 3.3 第二层：快速启动（TTFF 导向）

目标是**首帧时间（TTFF）而非开机时间**，三段流水线并行：

| 阶段 | 手段 | 典型收益 |
|---|---|---|
| bootloader | 裁剪/Falcon 模式（跳过 U-Boot 直接拉起 kernel）/加载与 sensor 初始化并行 | 省 300~500ms |
| kernel | 去打印（每条数 ms）、裁剪、**XIP 从 SPI NOR 直执**、出图驱动提权 | — |
| rootfs/应用 | ramfs 以内存换时间、rcS 主程序优先+业务并行、prelink/dlopen、非必需文件延后加载 | — |

业界快启标杆：君正 Atlas **<100ms**、RV1126B 0.1s、星宸 SSC306 首帧 68ms、全志 V853 200ms 首帧/700ms 冷启动、君正 T31 首帧 200ms。

#### 3.4 第三层：STR 待机与唤醒

- **软件流程**（Linux 范式，RTOS 同构）：freeze 进程 → 6 阶段设备挂起 → syscore → enter；唤醒逆序恢复
- **AOV 特有形态**："单帧 suspend-resume 循环"——每周期只处理 1 帧即回睡
- **唤醒源设计**：RTC 定时（心跳）、GPIO/PIR、WoWLAN/云指令（经保活芯片转发）、声音（AOA 异常声源/哭声）、小核 AI 命中
- **唤醒延迟**：新一代 <100ms vs 传统触发式 2~3s
- **防误睡/防睡死**：wakeup_count 竞态处理（休眠入口原子检查"锁计数+未决唤醒事件"）、状态看门狗（AOV 循环超上限保护）

#### 3.5 第四层：占空比录像策略

核心公式：**P_avg ≈ P_sleep + (P_wake − P_sleep) × duty**
（例：休眠 40mW + 每秒醒 10ms@1W ≈ 50mW；**唤醒窗口每省 5ms，续航近翻倍**）

- 值守帧率：1fps 主流（海思/瑞芯微/国科微），君正更激进 0.5~4fps 缩时可调
- 事件切换：切 15~30fps 全速，**滞回设计**（连续 5 帧无目标才退回值守）
- 值守降质：降分辨率（VGA）/缩略图/灰度；帧差+光感动态阈值（误报 -80%）
- 编码存储：智能编码省 50% 码率；**抓拍替代全帧省 90% 存储**（觅睿全天 600MB vs 15GB）
- 学术参照 sleepyCAM：PIR+继电器门控等待期 5.4mW vs 主机常开 1423.6mW（6000mAh→108 天）

#### 3.6 第五层：存储与网络链路省电

- **SD 卡三级省电**：idle 1~3mA / 时钟门控数百 μA / **断电 130μA**（MOS 管开关，须守时序：VDD<0.5V 保持 1ms、上电 74 clk 后 CMD0、<400kHz 初始化）；实测整机 15mA→6mA
- **攒批落盘**：AOV 缓冲满（海思 1MB）或事件唤醒时才写卡；休眠前 sync+卸载驱动
- **WiFi 省电**：DTIM/listen interval 调参（延迟 100ms~1s 换功耗降至 1/3~1/10）；主控深睡时 WiFi 芯片/MCU 保活 + UART 唤醒
- **事件上传完成 = 休眠前置条件**

---

### 4. 本项目指标基线建议（调研反推）

依据业界公开数据反推，建议本项目（OH L1 + 海思 IPC 平台）采用以下分级指标：

| 指标项 | 保底目标 | 竞争目标 | 对标依据 |
|---|---|---|---|
| AOV 值守功耗（1fps 持续录像，整板含 sensor+WiFi 保活） | ≤80mW | **≤45mW** | 海思营销 80mW；国科微单板 42mW；君正 T33 26mW；RV1106 40mW |
| STR 深睡功耗（DDR self-refresh+PMU 驻留，整板） | ≤40mW | **≤10mW** | 工程口径"较好的芯片 40mW"；RV1126B 核心板 7mW；宣称 1mW 级为裸片口径 |
| 唤醒延迟（唤醒源触发 → 首帧出图） | ≤500ms | **≤250ms** | 君正 TTFF<90ms；RV1106 250ms 抓图；留 OH L1 软件栈余量 |
| 事件切换全速（AI 命中 → 15~30fps 录像） | ≤1.5s | ≤1s | RV1106 1s 人脸识别；Fast AE 3 帧收敛 |
| 冷启动快启（上电 → 首帧） | ≤1.5s | **≤1s** | 全志 V853 700ms 冷启动；OH L1 需裁剪配合 |
| 续航（9000mAh，AOV 全时录像） | ≥10 天 | **≥13 天** | 觅睿 V7 实测口径 13~15 天 |
| 续航（5000mAh，AOV 全时录像） | ≥5 天 | ≥7 天 | Tapo C460 1s 间隔 8 天（10000mAh）折算 |
| AOV 存储占用 | ≤1GB/天 | **≤600MB/天** | 觅睿全天 AOV 600MB；抓拍替代全帧省 90% |
| WiFi 保活功耗（主控深睡时） | ≤5mA | ≤1mA | WiFi STA PS ~5mA；全志 DTIM10 180μA |

**口径纪律**（报告评审与验收时必须遵守）：每项指标注明测试条件（芯片/核心板/单板含 sensor/整机含 WiFi 与电池管理）、帧率、分辨率、彩转黑模式、环境温度。业界宣传值与实测值差异可达 4~8 倍（如海思 80mW 营销 vs 整板实测 350mW），**本项目验收建议统一采用"整板含 sensor、WiFi 保活、25℃、1fps 2MP"口径**。

---

### 5. AOV 技术点 → OH L1 系统层落点映射矩阵

> 衔接阶段 2（现状与差距分析）的核心输入。L1 小型系统 = LiteOS-A 内核 + small 形态子系统（powermgr_lite/battery_lite/wlan_lite 等）+ HDF。

| # | AOV 技术点（业界方案） | OH L1 落点 | 现状评估 | 差距/动作 |
|---|---|---|---|---|
| 1 | 4 级功耗状态机 | `kernel/liteos_a` PM 组件（原生 4 档 NORMAL/LIGHT/DEEP/SHUTDOWN）+ `powermgr_lite` 的 `SuspendDevice/WakeupDevice` 服务（含 APPLICATION/TIMEOUT 挂起原因、CAMERA_LAUNCH/WAKE_MOTION 等唤醒原因枚举） | 内核 PM 框架已有；`OsIdleTask` 为 WEAK 符号（默认仅 WFI），平台可覆写接入完整低功耗流程；powermgr_lite 服务化接口已有 | 定义 AOV 业务状态机（Active/AOV/Standby/Soft-off）映射到内核 4 档；切换条件集中管理 |
| 2 | PM 锁/防误睡 | LiteOS `LOS_PmLockRequest`（带超时自动释放）+ powermgr_lite RunningLock（`RUNNINGLOCK_BACKGROUND`、`FLAG_WAKEUP_WHEN_ACQUIRED` 加锁即唤醒） | 已有双机制 | 统一治理规范（"不许睡"一律走带超时的锁）；补 wakeup_count 式竞态语义（休眠入口原子检查锁计数+未决唤醒事件） |
| 3 | tickless idle | LiteOS 跨节拍 + tick timer 补偿机制 | 内核已支持 | BSP 使能并实测空闲功耗收益 |
| 4 | DVFS | liteos_a cpup / BSP 调频调压 | 部分支持 | AOV 场景策略："唤醒全速冲刺、空闲降频"；可先做两档+锁联动 |
| 5 | 驱动 PM（外设电源域） | HDF PM / LiteOS `LosPmDevice`/`LosPmSysctrl` 注册制 | 注册制已有 | 缺 Zephyr 式 runtime PM（引用计数+busy 保护）；建议封装统一设备 PM 接口；"越底层越晚睡越早醒"恢复序 |
| 6 | DDR self-refresh / CPU retention / 电源域序列 | `device/soc/hisilicon` BSP 的 `deepSuspend/deepResume` 钩子 | **当前为空位**（平台层最大缺口） | 依赖海思 SDK KOL/PM 驱动移植；对照 `ss_mpi_syskol_*` 4 级休眠定义打通 DEEP 态 |
| 7 | 单帧循环（SINGLE 采集模式） | AOV 应用层策略任务 + VI/VENC 通道按需启停 | 海思 sample_kol 参考实现公开（24 文件） | PoC 以 sample_kol 为蓝本移植到 OH L1 业务框架 |
| 8 | 快启（TTFF） | bootloader 裁剪、kernel XIP、init 精简、组件裁剪（**借鉴 RP2 mini 裁剪方法论**）、延迟加载 | OH L1 支持组件裁剪与按需编译 | 建立 TTFF 分段打点（bootloader/kernel/init/驱动/应用出图）；无分段计时就没有优化 |
| 9 | 唤醒源接入（RTC/GPIO/WiFi/UART） | HDF GPIO/RTC 驱动 + WiFi 驱动 + powermgr_lite WakeupDevice reason | 枚举已定义 | 实机唤醒链路逐项验证（海思 KOL 用 always-on BSP timer，OH 侧需对应 HDF timer/RTC 驱动） |
| 10 | 占空比录像策略 | 应用层策略任务（非 OH 系统组件） | — | 设计滞回切换（值守↔全速）、1fps RTC 定时唤醒、唤醒窗口时间预算管理 |
| 11 | 攒批落盘/SD 断电 | 文件系统（FATFS/LittleFS）写策略 + SD 驱动 PM（HDF） | — | 1MB 攒批满或事件时写卡；休眠前 sync；SD 断电时序由驱动 PM 管理 |
| 12 | WiFi 省电/保活 | `wlan_lite` / WiFi 驱动 PS 模式 | — | DTIM/listen interval 参数化；深睡时保活+UART 唤醒链路（依赖 WiFi 芯片能力） |
| 13 | 电量联动降档 | `battery_lite` 电池服务 | L1 已有 | 状态机订阅电池状态：低电量 AOV→保活降档、太阳能输入升档 |
| 14 | AI 检测联动 | SVP/NPU 驱动 + 子流（768×448）检测 | 平台相关 | 值守期用低分辨率子流做 AI 过滤，命中才切全速（误报与功耗双收益） |
| 15 | 音频保活（AOA） | 海思 KOL USER 模式 `audio_cken` 位 / AI 通道 | SDK 有钩子 | 可选演进项（AOV 3.0 方向），本期仅预留状态机接口 |

**三大核心缺口结论**（阶段 2 重点验证）：
1. **平台层 deepSuspend/deepResume 空置**——DDR self-refresh/电源域序列需 BSP 补齐，是 AOV 的地基；
2. **缺设备级 runtime PM**——驱动挂起/恢复序与引用计数保护需体系化建设；
3. **缺分段功耗/时间计量**——TTFF 打点、suspend/resume 耗时、持锁者导出，无计量则无优化。

---

### 6. 信息缺口与风险提示（汇总）

| 类别 | 缺口 | 影响 | 对策 |
|---|---|---|---|
| 海思 | SoC 级 AOV 各休眠态 mW 官方值；《KOL模式使用指南》《电池类低功耗设计指导书》原文；`ss_mpi_syskol_suspend` 新版本开放性；KOL DEEP 态 DDR 寄存器级细节；官方续航-帧率曲线 | 指标对标依赖营销值与板级实测 | 公开头文件+sample 源码已足够支撑架构设计；数值以 PoC 实测为准；如有商业 SDK 渠道再补 |
| 海思 | CV100/Hi3518EV300/DV300 一手 datasheet 低功耗章节 | 老平台迁移路线细节受限 | 老平台无原生 KOL 已确认，方案按"外部 MCU 保活+STR+快启"设计 |
| 君正 | AOV 内存自刷新电路级机制白皮书；"40+mW"测试条件；T42/T33V 规格 | 跨平台借鉴深度受限 | 以选型指南+产品案例口径为准 |
| 其他厂商 | 星宸/全志/安凯微/富瀚微多项 AOV 态功耗与快启数值不可得；富瀚微 4.5mW 口径存疑 | 横向对比表部分留白 | 已标注，不采信存疑值做指标依据 |
| 国际 | Ambarella/Sony 安防线待机功耗从不公开 | 国际对标缺数值 | 以架构思想（低功耗岛、AI Timelapse）借鉴为主 |
| 终端 | Ring/Arlo 电池容量从不公布；部分国行价格/续航登录墙 | 产品级对比留白 | 不影响系统层方案设计 |

---

### 7. 对后续阶段的输入结论

1. **阶段 2（OH L1 现状与差距分析）**：以第 5 节映射矩阵 15 项为清单，逐项核对本地源码树（`kernel/liteos_a` PM、`powermgr_lite`、HDF PM、`device/soc/hisilicon` BSP），产出差距分析报告；重点验证三大核心缺口。
2. **阶段 3（业务分析与裁剪）**：AOV 值守期最小必需集 = VI(单帧)+VENC+AI 子流+SD 存储+RTC；裁剪对象 = 全速期才需要的 RTSP/ONVIF/音频/补光/云台等按需加载（借鉴 RP2 裁剪方法论与海思 LIGHT 态"保 RTSP"vs DEEP 态"按需起 RTSP"的分态设计）。
3. **阶段 4（方案设计）**：以海思 KOL 三态机 + 业界 4 级功耗状态机为蓝本，设计 OH L1 系统层 AOV 框架（状态机服务、PM 锁治理、唤醒链路、TTFF 预算）；指标采用第 4 节基线。
4. **阶段 5（PoC）**：以 sample_kol 公开参考实现为蓝本，最小验证"RTC 定时唤醒 → 单帧采集编码 → 攒批落盘 → DEEP 休眠"循环 + 分段功耗/时间打点。


## OH L1 小型系统低功耗现状与差距分析

### 1. 结论速览（TL;DR）

1. **内核 PM 是"骨架完整、实现掏空"**：4 档休眠枚举、sysctrl/device 回调时序、带超时 PM 锁、失败回滚、唤醒竞态保护均已就绪且已编入两个海思目标；但三档默认 handler 同为一条 WFI、tickless 补偿是空桩、无 arch 深睡支撑、无 DVFS、无 SMP 从核下线、idle task 不挂钩。
2. **"deepSuspend 空置"假设证实，且是三重空置**：内核占位（WFI）→ 平台零注册（全树无 `LOS_PmRegister(SYSCTRL)`）→ powermgr_lite small 形态挂起循环是 `sleep(10)` 模拟桩。
3. **框架链路意外地全**：HDF PM ↔ 内核 PM 桥（devmgr_pm_reg.c）、驱动 PM listener API、RunningLock→/proc/power→内核锁的真实通路、WiFi hi3881 芯片级 PM+WoWLAN（含 LiteOS 分支）——都在树内，缺的是"最后一公里"平台实现与驱动挂接。
4. **存在一条树内可落地的"浅 AOV"路径**（无需海思 NDA 资料）：WFI-idle + RTC alarm/GPIO 唤醒 + sensor `pfnStandby/pfnRestart` + `HI_MPI_SNAP` 单帧抓拍循环 + media_lite 分段录像，估 1~2 人月；功耗收益为"运行态→WFI+外设时钟停"量级，非深睡级。
5. **CV610 级深睡 AOV 存在硬阻塞**：dv300 的 PMU/电源域/DDR self-refresh 运行时代码树内为零，MPP 内核模块闭源（liteos 全预编译 .a，linux 版 pmops 空桩），uboot 仅预编译 bin——必须获取海思 dv300 低功耗 SDK/KOL 类支持（NDA）才能实施。
6. **AOV 致命缺口——时间连续性**：内核无系统时间 offset 注入点（深睡 CNTPCT 掉电即时间丢失）；NTP 对时链路断（lwip sntp 空桩未编入、无开机 RTC→系统时间同步）——录像时间轴无法保障，必须修复。
7. **平台选型建议**：深睡验证优先 hi3518ev300（单核，规避 SMP 从核无法下线问题）；dv300 双核需先做单核原型或自研从核 park 机制。

---

### 2. 分层现状盘点

#### 2.1 内核层（kernel/liteos_a）——PM 框架

编译状态：`LOSCFG_KERNEL_PM` Kconfig **default y**（`kernel/extended/Kconfig:44-49`），两板 kernel_configs 种子未关闭 → **已编入 taurus/aries**；`/proc/power/*` 节点已生成。

| 能力                  | 位置                                                                                     | 状态          | 说明                                                                                                                                                                        |
| ------------------- | -------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 4 档休眠枚举（含 SHUTDOWN） | `kernel/include/los_pm.h:41-46`                                                        | ✅ 已有        | NORMAL/LIGHT/DEEP/SHUTDOWN                                                                                                                                                |
| 各档行为差异              | `kernel/extended/power/los_pm.c:109-123,653-673`                                       | ❌ 缺失        | 三档默认 = `OsPmSuspendDefaultHandler`（PRINTK+WFI），行为完全相同；SHUTDOWN 默认 NULL → `LOS_PmModeSet` 直接拒绝（:393-396）                                                                   |
| PM 锁（含超时锁）          | `los_pm.c:503,512,589-622`                                                             | ✅ 已有        | `LOS_PmTimeLockRequest(name,ms)` 用软定时器自动释放，可用                                                                                                                             |
| 锁→休眠联动              | `los_pm.c:159-179`                                                                     | ⚠️ 部分       | **全局一票否决**（单一 UINT16 计数器），与头文件"分档否决"文档不符；无法表达"允许 LIGHT 禁止 DEEP"                                                                                                           |
| suspend/resume 时序框架 | `los_pm.c:181-227`                                                                     | ✅ 已有        | early→device.suspend→cpuSuspend→cpuResume→device.resume→late，含失败回滚（prepare 标志）；**关中断+锁调度同步阻塞模型**（ISR 在 late 后才执行）                                                         |
| 设备注册                | `los_pm.c:229-240`                                                                     | ⚠️ 缺陷       | `pm->device` **单指针覆盖**（非链表），后注册者静默顶掉前者；sysctrl 按字段合并稍好                                                                                                                    |
| tickless 补偿         | `los_pm.c:86-96`                                                                       | ❌ 空桩        | `OsPmTickTimerStop` 恒 FALSE；`enterSleepTime` 死字段；TICK_TIMER 类型注册被显式拒绝（:291-293）                                                                                           |
| 动态 tick（空闲不空转）      | `kernel/base/sched/los_sched.c:51-86` + `arch/arm/arm/src/arm_generic_timer.c:164-183` | ✅ 已有        | deadline 重编程常态生效（与 PM 解耦），1ms 粒度——LIGHT 场景时间基已正确                                                                                                                          |
| **系统时间 offset 注入**  | `los_sys.c:38-41`                                                                      | ❌ 缺失        | `LOS_TickCountGet = HalClockGetCycles()/OS_CYCLE_PER_TICK`，无软件累加/offset 变量 → **深睡掉电即时间丢失（AOV 致命）**                                                                        |
| OsIdleTask          | `kernel/base/core/los_task.c:126-131`                                                  | ⚠️ WEAK 未覆写 | 纯 `while(1){WFI;}`，无 PM 钩子；全树无覆写；**SMP 从核走独立路径**（`arch/arm/arm/src/smp.c:99-101`），覆写 OsIdleTask 管不到从核                                                                     |
| 休眠自动进入              | —                                                                                      | ❌ 缺失        | `LOS_PmSuspend` 唯一调用点 = `/proc/power/power_count` 调试节点（且权限 0444，依赖 procfs 不校验权限的实现漏洞）                                                                                     |
| DVFS/调频             | 全树                                                                                     | ❌ 缺失        | 零命中；CPUP 仅统计（`los_cpup.c:342` `LOS_HistorySysCpuUsage`）；`PERI_CRG30_BASE`（CPU 调频 CRG 寄存器）已在 `target_config.h:31-33` 定义但零引用                                                |
| arch 深睡支撑           | `arch/arm/`                                                                            | ❌ 缺失        | 无 suspend/resume 汇编；`OsSRSaveRegister/OsSRRestoreRegister`（`los_hw_runstop.S:39-40`）是无调用者的死代码（可作起点）；`cache.S` 只有区间 clean/inv，**无 full cache clean+invalidate**（深睡前置条件不满足） |
| SMP 从核下线            | 全树                                                                                     | ❌ 缺失        | 无 hotplug；dv300 双核下 core1 永远 WFI，阻碍 SoC 深度电源状态                                                                                                                            |
| 唤醒竞态保护              | `los_pm.c:351-359,204-206`                                                             | ✅ 已有        | `LOS_PmWakeSet` + suspend 前二次检查；但 `LOS_PmSuspend(wakeCount)` 参数被丢弃，无唤醒源管理                                                                                                 |
| PM syscall          | `syscall/`                                                                             | ❌ 缺失        | 用户态只能走 /proc/power                                                                                                                                                        |

#### 2.2 组件层（base/powermgr）

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

#### 2.3 驱动层（HDF）

| 能力 | 位置 | 状态 |
|---|---|---|
| HDF↔内核 PM 桥 | `drivers/hdf_core/adapter/khdf/liteos/manager/src/devmgr_pm_reg.c`（`LOS_PmRegister(LOS_PM_TYPE_DEVICE)` → PowerStateChange(SUSPEND)，失败自动回滚） | ✅ **已有**（LOSCFG_DRIVERS_HDF 默认编入） |
| PM 状态广播链 | `devmgr_service.c:444-476` → `devhost_service.c:167-224` → `power_state_token.c:60-85`（含 DOZE_SUSPEND/RESUME） | ✅ 已有 |
| 驱动 PM API | `HdfPmRegisterPowerListener`（`hdf_device_object.c:62-81`）+ `IPowerEventListener{Suspend,Resume,DozeSuspend,DozeResume}`；注意 HdfDriverEntry 本身无 PM 回调，走 listener 注册 | ✅ 已有 |
| 外设驱动 PM 实现 | 仅 touch（`hdf_touch.c:1087` 含 hcs suspendSeq/resumeSeq）、audio(sapm)、drm_panel 实现；**gpio/uart/mmc/rtc/spi/i2c/timer/watchdog/sensor/wlan-HDI 全部未实现** | ⚠️ ≈缺失 |
| PM 单测 | `framework/test/unittest/pm/hdf_pm_driver_test.c` 等 | ✅ 已有（框架级） |

#### 2.4 平台层（device/soc|board/hisilicon）——最大缺口

| 能力 | 现状 | 证据 |
|---|---|---|
| SYSCTRL 注册（deepSuspend/lightSuspend 平台实现） | ❌ **零注册** | 全树 `LOS_PmRegister` 仅 4 处调用，无一在 device/vendor 下注册 SYSCTRL；板级 board.c 中 Pm/Suspend/Idle/Power 全零命中 |
| PMU/电源域/时钟 gating 运行时代码 | ❌ 零 | DDR self-refresh 代码仅存在于 uboot DDR 训练流程（`ddr_training_impl.c:430-462`）；`sys_ctrl.h` 只有 SC_GEN/bootmode，无掉电序列；无 regulator 实体驱动 |
| OsIdleTask 平台覆写 | ❌ 无 | — |
| uboot 快启空间 | ❌ 无源码 | 仅预编译 bin + reg_info_*.bin（DDR/时钟寄存器表）→ 树内无法做 boot 裁剪 |
| MPP 低功耗钩子 | ❌ 闭源 | liteos 侧 vi/venc/isp 全预编译 .a 静态链入内核（`sdk_liteos/mpp/module_init/BUILD.gn`，MMZ 0x88000000/384MB）；linux 侧仅 vo/sys/hdmi/tde/hifb 开源且 pmops 空桩（`vou.c:441` hi_unused），唯一真实现是 TDE（`tde_ioctl.c:966-981`） |
| 调频寄存器 | ⚠️ 定义未用 | `PERI_CRG30_BASE`（cpu freq-mode CRG）已定义零引用；`get_bus_clk()` 硬编码 50MHz |
| DV300 SMP | ⚠️ 约束 | release.config `LOSCFG_KERNEL_SMP=y`，双核 + 无从核下线 |

#### 2.5 唤醒源清单

| 唤醒源             | 驱动                                                                                                                                                                                                                   | 能力                              | 状态                                                                              |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------- |
| RTC alarm       | `common/platform/rtc/rtc_hi35xx.c`（Alarm 读写:328/354、回调注册:380、中断使能:398、IRQ 处理:655-690）；hcs：dv300 irq=37@0x12080000、ev300 irq=32@0x120E0000                                                                            | 断电走时+alarm 中断链路完整               | ✅ **可唤醒 WFI/浅睡**；深睡唤醒域未配置；与内核 PM 零桥接（`LOS_PmWakeSet` 无调用者）                      |
| GPIO/按键         | `gpio_hi35xx.c`（PL061，IRQ 边沿/电平:316-342，irqStart=48）；input hcs 按键 gpioNum 1/31/32                                                                                                                                    | IRQ 完整                          | ✅ 可作 PIR/按键唤醒；无 PM 回调、无 wake-pin 专用配置（仅 pin hcs `PWR_WAKEUP` 复用定义）              |
| WiFi hi3881v100 | `common/platform/wifi/hi3881v100/`：`oal/plat_pm_wlan.c`（1419 行，含 `_PRE_OS_VERSION_LITEOS` 分支）、`mac/hmac/hmac_wow.c`（WoW pattern/wakeup_reason）、API `hi_wifi_api.h:464-478`（HI_LIGHT_SLEEP/HI_DEEP_SLEEP/WOW_PATTERN） | **芯片级 PM+WoWLAN 完整且已适配 LiteOS** | ✅ 已有但未接系统 PM；HDI `SetPowerSaveMode()` 全链路存在（client→hdi→hal `wifi_hal.c:377`→驱动） |
| Timer           | `timer_hi35xx.c`（SetOnce/SetTimeout，irq 33/34）                                                                                                                                                                       | 运行态周期唤醒                         | ⚠️ 非深睡唤醒源                                                                       |
| UART            | uart_hi35xx/uart_pl011                                                                                                                                                                                               | 无 RX 唤醒、无 PM                    | ❌ 缺失                                                                            |
| Watchdog/Sensor | —                                                                                                                                                                                                                    | 无 PM                            | ❌ 缺失                                                                            |

#### 2.6 AOV 业务相关系统能力

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

### 3. 三大核心缺口验证（对照调研报告 §5 假设）

| 假设缺口                            | 验证结论                                                                                                                                                        | 修正后表述                                                                                                                             |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| ① 平台层 deepSuspend/deepResume 空置 | **证实，且为三重空置**：内核默认 handler=WFI（los_pm.c:653-676）→ 平台零 SYSCTRL 注册 → powermgr small 挂起循环 sleep(10) 假休眠                                                        | 好消息：框架链路（内核 PM↔HDF PowerStateChange↔驱动 listener）全部现成；mini 版实现可作 small 修复参照。**真正的深睡实现被 NDA 阻塞**（dv300 PMU/DDR self-refresh 资料树内为零） |
| ② 缺设备级 runtime PM               | **部分证伪**：HDF 框架级 PM（listener 注册、状态广播、DOZE、wake token、单测）**已有且已桥接内核**；缺的是**外设驱动侧实现**（gpio/uart/mmc/rtc/sensor/wlan-HDI 全未挂 listener）与 Zephyr 式引用计数+busy 保护语义 | 工作量从"建框架"降级为"逐驱动挂接"（每项 1~2 人周）；device 单指针覆盖缺陷需先修（改链表或产品侧聚合分发器）                                                                    |
| ③ 缺分段功耗/时间计量                    | **证实**：hidumper/hievent 为通用 DFX，无 TTFF 分段打点、无 suspend/resume 耗时、无持锁者导出（`LOS_PmLockInfoShow` 有但仅 printk）                                                     | 需自建 PM 埋点体系（阶段 4 方案必含项）；CPUP 统计可作 DVFS 决策输入                                                                                       |

**新增发现的关键缺口**（调研阶段未预判）：

- **④ 时间连续性双缺口（AOV 致命）**：深睡 CNTPCT 掉电无 offset 补偿（内核必改：`OsGetCurrSchedTimeCycle` 加全局 offset + 唤醒后 RTC 读回累加）；NTP 链路断 + 无开机 RTC 校时。AOV 录像时间轴、文件命名、缩时摄影连续性全部依赖此项。
- **⑤ SMP 从核无法下线**：dv300 双核，core1 停在独立 WFI 路径（smp.c:99-101），深睡收益大打折扣 → 建议 ev300 单核先行验证。
- **⑥ PM 锁全局一票否决**：与文档语义不符，AOV 需要分档锁（"禁 DEEP 允 LIGHT"）；且 `LOS_PmReadLock` 超时硬编码 500ms 恒返 LOS_OK，PM 管理任务需自行循环重试。
- **⑦ 休眠触发入口异常**：`LOS_PmSuspend` 唯一入口 /proc/power/power_count 权限 0444（依赖 procfs 不校验权限的漏洞），无 syscall——产品化必须新增正式触发通道。

---

### 4. AOV 状态机 → 现有能力映射可行性

| AOV 状态（业界 4 级） | 期望落点 | 可行性 | 阻碍与动作 |
|---|---|---|---|
| 全速 Active（15~30fps 录像+推流+AI） | PM 锁持有，不休眠 | ✅ 立即可用 | `AcquireRunningLock(BACKGROUND)`→内核锁链路已通；注意全局否决副作用 |
| AOV 值守（1fps 单帧循环） | LIGHT_SLEEP 档 + RTC alarm 定时唤醒 + MPI SNAP 单帧 | 🟡 **浅 AOV 可行**（树内） | 槽位有、实现缺：LIGHT 默认=WFI 与 NORMAL 无差；需自研 lightSuspend（时钟门控级）+ RTC alarm→PM 唤醒桥接 + 单帧循环业务任务；**不依赖 NDA** |
| STR 深睡（DDR self-refresh+PMU 驻留） | DEEP_SLEEP 档 | ❌ **当前不可用** | 三重硬缺口：时间补偿缺失、无 full cache clean+inv、SMP 从核不下线；平台实现被 NDA 阻塞（dv300 PMU/DDR 资料为零；MPP 闭源只能整模块 deinit/re-init，代价与风险高） |
| 保活/软关机（WiFi PS / 4G PSM，SoC 下电） | SHUTDOWN 档 + hi3881 WoWLAN | 🟡 部分可行 | SHUTDOWN 档被内核主动禁用（handler NULL）需先注册；**hi3881 芯片级 PM+WoW 已就绪**（LiteOS 分支存在），接入系统 PM 为中等工作量；uboot 预编译 → 冷启动快启无树内空间 |
| 降频运行维度（DVFS） | — | ❌ 内核无此维度 | 4 档模型只描述"睡多深"不描述"跑多快"；需绕过内核直操 `PERI_CRG30_BASE` + CPUP 闭环（寄存器地址已给出） |

---

### 5. 差距清单（按优先级，含工作量判断）

#### P0 —— 阻塞项（不解决则 AOV 不成立）

| #    | 差距                            | 落点                                           | 动作                                                                      | 工作量             |
| ---- | ----------------------------- | -------------------------------------------- | ----------------------------------------------------------------------- | --------------- |
| P0-1 | small 挂起循环是 sleep(10) 桩       | powermgr_lite `small/auto_suspend_loop.c:29` | 照抄 mini 版接 `LOS_PmReadLock+LOS_PmSuspend`（或新增 syscall/修正 proc 权限）       | **天级**          |
| P0-2 | 休眠无自动进入机制                     | 内核 OsIdleTask（WEAK）                          | 产品侧覆写 OsIdleTask 或建 PM 管理任务（等锁释放→触发 suspend）；注意 SMP 从核例外                | 周级              |
| P0-3 | 深睡时间丢失                        | 内核 `los_sched_pri.h:82-85`/`los_sys.c:38-41` | 引入全局时间 offset：休眠前记 CNTPCT、唤醒后 RTC 读回累加（RTC alarm 驱动已就绪）                 | 周级（**改内核，需评审**） |
| P0-4 | NTP/RTC 校时断链                  | third_party/lwip sntp + init                 | 编入 sntp.c、实现 SNTP_SET_SYSTEM_TIME、开机 RTC→settimeofday、周期校时任务            | 周级              |
| P0-5 | 平台 SYSCTRL 零注册（light/deep 实现） | device/soc 或 board hisilicon                 | 浅 AOV：自研 lightSuspend（WFI+可控时钟门控）；深睡：**依赖海思 dv300 低功耗 SDK（NDA）——外部硬阻塞** | 浅:月级 / 深:阻塞     |

#### P1 —— 显著影响效果

| #    | 差距                             | 动作                                                                                                                                                                    | 工作量        |
| ---- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| P1-1 | PM 锁全局一票否决、无分档                 | 扩展为按档位锁计数数组（内核改动）                                                                                                                                                     | 周级         |
| P1-2 | device 注册单指针覆盖                 | 改 LOS_DL_LIST 链表（参照 lockList）或产品侧聚合分发器                                                                                                                                | 周级         |
| P1-3 | 外设驱动无 PM listener              | mmc/rtc/gpio/uart/wlan-HDI 逐个挂 `HdfPmRegisterPowerListener`（框架已就绪）                                                                                                    | 每项 1~2 人周  |
| P1-4 | hi3881 WoWLAN 未接系统 PM          | 芯片 PM 已有（含 LiteOS 分支），桥接到 suspend 流程 + SetPowerSaveMode 策略化                                                                                                           | 中等         |
| P1-5 | SMP 从核不下线（dv300）               | ~~优先 ev300 单核验证；dv300 关 SMP 做单核原型~~ **【修订：T6 第三批实证 dv300 关 SMP 链接失败（MPP 预编译库依赖 SMP spinlock 符号）】**→ dv300 保持 SMP + 自研从核 park（唯一路线）；单核机制验证用 ev300（MPP 为 .so 形态，依赖性待验证） | 从核 park:月级 |
| P1-6 | 无 DVFS                         | 直操 PERI_CRG30_BASE 两档调频 + CPUP 闭环（"唤醒全速冲刺、空闲降频"）                                                                                                                      | 周级         |
| P1-7 | arch 深睡底层（full cache 操作/上下文保存） | 以 `los_hw_runstop.S` 死代码为起点补 full cache clean+inv 与关电序列（配合 P0-5 NDA 资料）                                                                                               | 月级         |

#### P2 —— 工程质量

| # | 差距 | 动作 |
|---|---|---|
| P2-1 | 无 PM 计量 | TTFF 分段打点（boot/kernel/init/驱动/出图）、suspend/resume 耗时、持锁者导出（扩展 LOS_PmLockInfoShow）——**无计量则无优化** |
| P2-2 | 唤醒源管理缺失 | 建唤醒源注册/使能接口（RTC/GPIO/WiFi/UART 集合管理），补 wakeup_count 竞态语义 |
| P2-3 | battery_lite 是模拟器 | IBattery vtable 对接真实电量/充电检测（电池 IPC 必需；常电场景可缓） |
| P2-4 | 无 PM 单测/回归 | 补 testsuites pm 用例；`LOS_PmReadLock` 缺陷修复（超时硬编码/恒 LOS_OK） |
| P2-5 | aries 未启用 powermgr | config.json 追加 powermgr 子系统块 + 确认 ipc 依赖 |
| P2-6 | 权限与安全 | SuspendDevice/WakeupDevice 无权限校验；/proc/power 权限位修正 |

---

### 6. 实施路径建议（输入阶段 3/4）

**三步走，先浅后深、先单核后双核：**

1. **第一步：浅 AOV（树内闭环，1~2 人月）**
   P0-1~P0-4 + 浅版 P0-5：修复 small 挂起桩 → 覆写 idle/PM 任务自动进入 → RTC alarm 唤醒桥接 → LIGHT 档实现（WFI+时钟门控）→ MPI SNAP 单帧循环 + sensor standby/restart + media_lite 分段录像 + 攒批 fsync 落盘 → PM 分段计量打点。**产出可实测的 AOV 原型与功耗基线**（预期量级：运行态数百 mW → 值守 WFI 级，具体以实测为准）。
2. **第二步：标准 AOV 增强（2~3 人月，与海思资料获取并行）**
   P1 全部：分档锁、设备链表、驱动 listener 逐个挂接、hi3881 WoW 接入（WiFi 保活+主控浅睡）、DVFS 两档、唤醒源管理、battery 对接。对标业界"AOV 值守 40~80mW"档位。
3. **第三步：深睡 AOV（依赖 NDA，获取后 2~3 人月起）**
   海思 dv300 低功耗 SDK（PMU/DDR self-refresh/电源域序列）→ DEEP_SLEEP 平台实现（arch 底层 + 时间 offset 联调）→ MPP 模块级 deinit/re-init 策略（闭源约束下的唯一路径，需评估 MMZ/ISP 重建代价）→ 对标业界"STR 1~40mW"档位。若 NDA 不可得，**方案上限锁定在浅 AOV+WiFi 保活组合**，指标基线相应下调（阶段 1 报告 §4 的"保底目标"口径）。

**平台策略**：ev300（单核）作为深睡机制验证平台；dv300（双核）作为目标产品平台，SMP 从核 park 列入第三步。

---

### 7. 证据附录（关键文件索引）

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


## AOV 业务分析与系统裁剪方案

### 1. 结论速览（TL;DR）

1. **业务模型**：AOV 业务拆为三个工作期——**值守期**（1fps 单帧循环，功耗敏感）、**事件期**（AI 命中切全速录像）、**维护期**（联网预览/OTA/配置）。裁剪原则：**值守期最小集常驻，事件期能力延迟加载，维护期能力按需拉起，无屏形态 UI 全家桶直接裁剪**。
2. **组件级**：taurus 现有 50 组件，分级处置后建议**裁剪 17 个、延迟/按需 9 个、保留 24 个**；最大收益来自无屏化（UI/图形/示例应用 7 项）与去软总线族（dsoftbus+device_auth+device_security_level+dmsfwk_lite+dslm 5 项，RAM 声明值合计 ~49MB）。
3. **MPP 模块级**：32 个静态库中值守期最小集约 11 个；**树内存在完整 `sdk_exit.c`（含 `SDK_exit()`，模块级 exit 序列齐全）**——阶段 2"无官方 mod_exit 顺序"判断修正，**模块级 deinit/re-init 策略树内可行**（MPP 闭源约束下的最优路径），但当前无任何调用者，需接管并验证。
4. **内存布局重配**：DDR 512MB = 内核系统内存 ~127MB（`SYS_MEM_SIZE_DEFAULT 0x07f00000`）+ MMZ 静态 384MB（`sdk_init.c:32-33`）。AOV 值守期不需要大 VB 池，建议 **MMZ 降至 128~192MB + VB 池双档位动态申请**（值守小池/事件大池），释放的内存换 kernel 堆余量或缩小 DDR 有效容量以省功耗。
5. **服务启动重排**：15 个 init 服务分为快启关键路径（3 个：foundation/media_server/shell[量产可裁]）与延迟组；无屏化后 wms_server/appspawn/apphilogcat/bundle_daemon 等 6 个可裁或延迟。
6. **风险**：bundle.json 声明预算不可靠（dsoftbus RAM 声明 40MB 等），裁剪收益必须以构建产物实测为准；组件间依赖需按 RP2 方法逐个反查后再动刀。

---

### 2. AOV 业务分析

#### 2.1 三工作期业务模型（借鉴海思 KOL 三态机 + 业界 4 级功耗状态机）

```
        AI命中/PIR/云指令                 长时无事件/低电量
┌────────┐ ──────────────► ┌────────┐ ──────────────► ┌────────┐
│ 维护期  │                 │ 事件期  │                 │ 值守期  │
│(联网/预 │ ◄────────────── │(全速录像│ ◄────────────── │(1fps单 │
│ 览/OTA)│   用户拉起/推流   │ 15~30fps)│   滞回:连续N帧    │ 帧循环) │
└────────┘                 └────────┘   无目标退回      └────────┘
   功耗:Active级              功耗:1~3W               功耗:目标≤80mW
```

| 工作期 | 业务内容 | 对应 KOL 状态 | 服务/模块需求 |
|---|---|---|---|
| **值守期** | RTC 定时唤醒 → sensor restart → 单帧采集 → 编码 → AI/MD 检测 → 攒批落盘 → sensor standby → 回睡 | KOL DEEP + SINGLE 采集 | VI/ISP/VENC/RC/H264e或H265e/(RGN 时间戳)/NNIE或IVE或MD/SD存储/RTC；**不需要**：VO/显示/音频/推流/软总线/UI |
| **事件期** | 切 15~30fps 全速录像 + JPEG 抓拍 + 补光 + 可选推流告警 | KOL NORMAL_RECORD | 值守集 + JPEGE + 大 VB 池 + (可选)音频 AENC + (可选)RTSP 推流（自研，树内无） |
| **维护期** | 联网预览、配置下发、OTA 升级、日志上传 | NORMAL（持 PM 锁） | 事件集 + WiFi 全速 + sys_installer_lite + huks/appverify（验签）+ curl/mbedtls |

#### 2.2 值守期最小必需集（裁剪的锚点）

- **采集编码链**：MIPI-RX → VI → ISP(简化 3A，曝光参数缓存借鉴 KOL Fast AE) → VENC(H.264/H.265 二选一) → RC
- **检测链**（三选一，功耗/精度权衡）：MPP libmd 移动侦测（最省）/ IVE 帧差 / NNIE 人形（最准，768×448 子流）
- **存储链**：FATFS + MMC/SD + 攒批 fsync（1MB 攒批满或事件时落盘，海思 KOL 同款策略）
- **时间链**：RTC（alarm 唤醒源 + 时间轴基准）+ 开机 RTC 校时（阶段 2 P0-4）
- **电源链**：powermgr_lite(RunningLock/Suspend 服务) + 内核 PM + PM 计量埋点（阶段 2 P2-1）
- **时间戳叠加**：RGN 模块（OSD，录像可回溯性必需，保留）

#### 2.3 业务分解 × 工作期映射总表

| 业务域 | 值守期 | 事件期 | 维护期 | 树内载体 | 处置 |
|---|---|---|---|---|---|
| 视频采集 | 单帧 | 全速 | 预览流 | MPP VI/ISP（闭源 .a） | 常驻（最小配置） |
| 视频编码 | 单帧 I/P | 全速+抓拍 | 按需 | MPP VENC/H264E/H265E/JPEGE | 常驻（JPEGE 事件期） |
| AI 检测 | 子流推理 | 跟踪 | — | ai_engine+NNIE adapter / libmd | **延迟加载**（首帧录像后） |
| 音频 | 关 | 可选 | 对讲 | MPP audio 族+audio_lite | **裁剪或按需**（AOA 方向预留） |
| 显示/OSD | OSD only | OSD | — | RGN 保留；VO/TDE/HDMI/HIFB | VO 族**裁剪**（无屏） |
| 本地存储 | 攒批写 | 全速写 | — | FATFS+MMC+fsync | 常驻 |
| 网络推流 | 关 | 告警上传 | RTSP 预览 | lwip+hi3881(PS)+curl；RTSP 无组件 | WiFi 常驻（PS 模式）；RTSP **自研按需** |
| 分布式协同 | — | — | — | dsoftbus 族 | **裁剪**（单体 IPC 无场景） |
| UI/应用 | — | — | — | ace/ui_lite/window/surface/graphic/sample apps | **裁剪**（无屏） |
| OTA | — | — | 升级窗口 | sys_installer_lite+huks+appverify | **延迟**（维护期拉起） |
| 包管理/应用孵化 | — | — | — | bundle_framework_lite/appspawn | **裁剪**（纯原生服务形态） |
| DFX | 降级 | 全 | 全 | hilog/hidumper/hievent | hilog 保留降级，hidumper 裁 |
| 电池管理 | 电量采样 | — | — | battery_lite（模拟器） | 保留（数据源接真实，阶段 2 P2-3） |

---

### 3. MPP 模块级裁剪方案（32 静态库分级）

依据：`sdk_liteos/mpp/module_init/BUILD.gn`（32 个 hi3516cv500_* 静态库链入内核）、`src/sdk_init.c`（mod_init 序列）、`src/sdk_exit.c`（**mod_exit 序列齐全，`SDK_exit()` @ :277**）。

| 分级 | 模块 | 数量 | 说明 |
|---|---|---|---|
| **值守期常驻** | base、sys、vi、isp、rc、venc、h264e **或** h265e、rgn、chnl、mipi(rx/tx 归 sensor 通路)、ive **或** nnie（检测二选一） | ~11 | h264e/h265e 二选一（按产品编码格式定）；nnie/ive/md 三选一 |
| **事件期启用** | jpege（抓拍）、vpss（子流缩放，若值守期用 venc 直连可延后）、aenc/ai/aio/acodec（音频，若保留） | 2~6 | 随事件态 deinit→init 或启动即 init 但不开通道 |
| **裁剪（无屏/无场景）** | vo、tde、hdmi、hifb、vgs、dis、gdc、vdec、jpegd、vfmw、vedu* | ~11 | vedu 为 CV500 编码硬件单元，需确认 venc 依赖关系后定（保守保留）；cipher 若做码流加密则保留 |
| **系统必需** | wdt（看门狗）、cipher（按需） | 1~2 | AOV 防睡死看门狗（阶段 1 报告 §3.4）依赖 wdt |

**模块级电源策略（MPP 闭源约束下的可行路径）**：
- 树内 `SDK_exit()` 提供完整逆序 exit（BASE→MMZ→SYS→ISP→VI→RGN→…→IVE/NNIE），**当前全树无调用者**——由 hisi_sdk HDF 驱动（`common/platform/hisi_sdk/hisi_sdk.c:31` 调 `SDK_init()`）对称接管，新增 `SDK_exit` 触发通道；
- 深睡（第三步，依赖 NDA 资料）前执行"模块级 deinit → 电源域关断 → 唤醒后 re-init"，规避闭源驱动内做电源钩子的不可行性；
- **风险**：MMZ/ISP 重建代价与正确性未知，需实测 deinit→re-init 循环稳定性与耗时（列入阶段 5 PoC）；exit 序列中 HIFB/PWM/PIRIS 等为空实现或桩，逐模块验证。

**MMZ 重配**：
- 现状：`g_mmz_start=0x88000000, g_mmz_size=384MB` 内核 cmdline 静态划死（`sdk_init.c:55`）；
- 建议：MMZ 降至 **128~192MB**（值守期 1fps 低分辨率 VB 需求极小），VB 池改**双档位**：值守小池（如 2MP×2buf）常驻、事件大池（1080p/4K×Nbuf）进入事件期时 `HI_MPI_VB` 动态申请、退回值守时释放；
- 收益：① 释放 192~256MB 物理内存（可降低 DDR 有效容量/为深睡 DDR 自刷新缩小保持域）；② 值守期 VB 缓冲少 → DDR 访问功耗降。

---

### 4. 组件级裁剪方案（50 组件分级处置）

依据：`vendor/hisilicon/hispark_taurus/config.json`（50 组件）+ 各 bundle.json 资源声明 + 阶段 2 能力盘点。**处置前必须按 RP2 方法反查 BUILD.gn 依赖链**（下表为方案建议，非最终清单）。

#### 4.1 裁剪（17 项）——无屏形态 + 去分布式 + 去测试

| 组件 | 理由 | ROM/RAM 声明值参考 |
|---|---|---|
| window_manager_lite / surface_lite / graphic_utils_lite | 无屏 | 110KB+110KB+450KB / ~150KB |
| ui_lite / ace_engine_lite | 无 UI 应用 | 900KB+521KB / ~172KB |
| camera_sample_app / camera_screensaver_app | 示例应用（applications/sample/camera） | — |
| ability_lite | 无 UI ability 形态（原生服务直跑；裁剪前反查 media/camera 服务对 ability 的依赖） | 未声明 |
| dsoftbus | 单体 IPC 无分布式场景；**RAM 声明 40MB 为最大单项** | 3000KB / **40MB** |
| device_auth / device_security_level / dmsfwk_lite | 软总线配套族，随之裁剪（dslm_server/deviceauth_service/devattest_service 同步从 init cfg 移除） | 4096KB+200KB+未声明 / 4MB+2.5MB |
| drivers_peripheral_display / usb / vibrator / light | 无对应外设 | — |
| i18n_lite / resource_management_lite | UI 资源配套 | 未声明+200KB / 900KB |
| xts（acts / tools / device_attest_lite） | 测试套件，量产镜像不进 | — |
| syscap_codec | 开发期工具 | — |

#### 4.2 延迟/按需（9 项）——快启关键路径之外

| 组件 | 策略 |
|---|---|
| ai_engine（+NNIE adapter） | 首帧录像完成后拉起 ai_server（值守检测可先用 libmd 移动侦测顶替冷启窗口） |
| sys_installer_lite + huks + appverify | OTA 窗口按需初始化（huks_server 延迟启动；验签能力维护期才需要） |
| bundle_framework_lite | 纯原生服务形态可不启动 bundle_daemon（组件保留、服务延迟） |
| appspawn | 无 UI 应用则不启动（组件可保留备用） |
| sensor_lite + drivers_peripheral_sensor | 带 PIR 机型保留（唤醒源），无 PIR 机型裁 |
| audio_lite + drivers_peripheral_audio | AOA（音频唤醒）演进预留；纯视频 AOV 机型裁 |
| permission_lite | 无第三方应用则可裁（安全评审定） |

#### 4.3 保留常驻（24 项）

liteos_a、bootstrap_lite、init、samgr_lite、safwk_lite、ipc、hdf_core、drivers_adapter、drivers_tools、camera_lite、media_lite、powermgr_lite、battery_lite、hilog_lite、hidumper_lite（可降级）、drivers_peripheral_wlan、drivers_peripheral_input（按键唤醒）、drivers_peripheral_sensor（PIR 机型）等 + 存储栈（内核 FATFS/MMC 非组件项）。

#### 4.4 裁剪收益预估（声明值口径，**必须实测修正**）

| 维度 | 预估收益 | 主要来源 |
|---|---|---|
| RAM | **~55MB+（声明口径）** | dsoftbus 40MB + device_auth 4MB + device_security_level 2.5MB + appspawn 13MB（延迟）+ UI 族 ~0.4MB + samgr/safwk 常驻但 UI 服务不再注册 |
| ROM | **~12MB+（声明口径）** | dsoftbus 3MB + huks 5MB（延迟非裁）+ appverify 5MB（延迟）+ device_auth 4MB + UI 族 ~1.5MB + init 3.9MB 中裁剪部分 |
| 启动时间 | 关键路径服务从 15 → 3~5 个 | 见 §5 |

> ⚠️ bundle.json 声明值普遍偏大且口径混乱（如 dsoftbus RAM 40MB 为上限声明），**实际收益以裁剪前后构建产物 size + 运行时内存水位实测为准**（阶段 5 PoC 计量项）。

---

### 5. 服务启动顺序重排（init_liteos_a_3516dv300.cfg）

现状 15 个服务：foundation、shell、appspawn、apphilogcat、media_server、wms_server、bundle_daemon、hiview、huks_server、sensor_service、ai_server、softbus_server、deviceauth_service、devattest_service、dslm_server。

| 分组 | 服务 | 处置 |
|---|---|---|
| **快启关键路径**（上电→首帧录像） | foundation（samgr 宿主）、media_server（录像服务） | 最高优先级，pre-init 完成挂载后立即拉起 |
| 调试（量产可裁） | shell、apphilogcat、hiview | 量产镜像裁 shell/apphilogcat，hiview 保留（异常上报） |
| **延迟组**（首帧后/按需） | ai_server、huks_server、bundle_daemon、sensor_service | 首帧录像达成后串行拉起（借鉴 RP2/业界"rcS 主程序优先+业务并行"） |
| **裁剪组** | wms_server（无屏）、appspawn（无应用）、softbus_server、deviceauth_service、devattest_service、dslm_server（软总线族） | 随组件裁剪移除 |

**AOV 快启目标分解**（对标业界 TTFF，阶段 1 §3.3）：
```
上电 → uboot(预编译,树内不可裁) → kernel+MPP静态模块 init → 挂载 SD
     → foundation+media_server → AOV 首帧落盘
预算：uboot ~x ms（实测）+ kernel ~x + MPP init ~x + 业务 ~x → 目标冷启动首帧 ≤1.5s（保底）/≤1s（竞争）
要求：全链路分段打点（阶段 2 P2-1 计量体系），当前无任何打点 → PoC 第一项工作
```

---

### 6. 与阶段 2 差距清单的衔接

| 阶段 2 差距 | 本方案的裁剪侧配合 |
|---|---|
| P0-2 休眠自动进入 | 裁剪后常驻任务减少 → PM 锁持有者收敛（仅 media/AOV 策略任务/存储），锁治理面变小 |
| P0-3/P0-4 时间连续性 | 值守期时间戳依赖 RTC+校时服务，裁剪不影响；RGN OSD 时间戳保留 |
| P1-3 驱动 PM listener | 裁剪 display/usb/vibrator/light 后，需挂 listener 的驱动集合缩小为 mmc/rtc/gpio/wlan/input(+sensor) |
| P1-5 SMP 从核 | 裁剪降低从核负载必要性，dv300 单核原型（关 SMP）可行性提高 |
| P2-3 battery 模拟器 | battery_lite 保留并列入接入计划 |
| 浅 AOV 路径（§6 第一步） | 本方案值守期最小集 = 浅 AOV 单帧循环的模块清单，两者一致 |

---

### 7. 风险与验证清单（动刀前置条件）

1. **依赖反查**（RP2 方法）：每个裁剪项执行树内 BUILD.gn 反向依赖检索（如 ability_lite 被 media/camera 服务依赖与否、ai_engine 对 softbus 的依赖、ipc 组件被裁项引用情况），输出《裁剪依赖核查表》后才改 config.json；
2. **SDK_exit 可用性验证**：`SDK_exit()` 无调用者历史，deinit→re-init 循环的稳定性/耗时/MMZ 重建正确性需 PoC 实测（模块级电源策略的前提）；
3. **声明值不可靠**：所有 ROM/RAM 收益以实测为准（构建产物 size + /proc 内存水位 + memdump）；
4. **vedu/cipher/vpss 归属存疑**：CV500 系 vedu 与 venc/h264e 的硬件依赖关系、vpss 在值守链路是否必需（venc 直连可行性）需结合 MPP 文档/实测确认；
5. **hispark_taurus_mini_system 参照**：树内已有极简产品配置（仅 startup+security），可作裁剪下限参照与 config.json 语法样板；
6. **aries 同步评估**：hi3518ev300 的 MPP 库集（hi3516ev200_* 35 个 .so）与 dv300 不同构，深睡验证平台（阶段 2 建议）裁剪清单需单独出一版。

---

### 8. 交付物与下一步

- 本文档 = 阶段 3 方案建议稿（业务模型 + 三层裁剪方案 + 预算）；
- **下一步（阶段 4）**：以本方案值守期最小集 + 阶段 2 P0/P1 差距清单为输入，设计《AOV 系统级低功耗方案设计文档》：功耗状态机服务、PM 锁治理规范、唤醒链路（RTC/GPIO/WiFi WoW）、时间连续性方案（内核 offset+RTC 校时+NTP）、TTFF 预算与计量体系、模块级 deinit/re-init 电源策略；
- **并行前置动作**：①裁剪依赖核查表（可立即启动）；②向海思确认 dv300 低功耗 SDK/KOL 支持的可获得性（深睡路径 NDA 硬阻塞，决定方案上限）。


## AOV 系统级低功耗方案设计

### 1. 设计目标与指标

#### 1.1 总体目标

支撑 OpenHarmony L1 小型系统低功耗竞争力提升：在 OH small 系统（LiteOS-A）+ 海思 IPC 平台上构建**系统级 AOV 低功耗框架**，实现全天候持续录像（1fps 值守 + 事件全速），并使 OH L1 具备可复用的低功耗基础能力（状态机、PM 锁治理、唤醒链路、时间连续性、计量体系）。

#### 1.2 分步指标（承接阶段 1 §4 基线，按三步走分解）

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

### 2. 总体架构

#### 2.1 五层架构

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

#### 2.2 功耗状态机（核心设计）

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

### 3. 子系统方案设计

#### 3.1 L3 内核层增强（kernel/liteos_a，5 项改动）

| #   | 改动                        | 设计                                                                                                                                                                                                                                                         | 触点（阶段 2 证据）                                                                                        |
| --- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| K1  | **分档 PM 锁**               | `LosPmCB.lock`（单一 UINT16）→ `lock[LOS_SYS_SHUTDOWN+1]` 按档计数数组；`LOS_PmLockRequestEx(name, mode)` 新 API，原 API 语义保持=否决所有档（兼容）；`OsPmSuspendCheck` 改为"取当前 pmMode 允许的最浅档"（锁否决 DEEP 时自动降级 LIGHT 而非放弃）                                                              | `los_pm.c:69,159-179,503`；修复头文件文档与实现不符                                                             |
| K2  | **时间 offset 补偿**（AOV 致命项） | 新增全局 `g_osTimeOffsetCycle`：`OsGetCurrSchedTimeCycle()` 返回值 + offset；suspend 前记录 CNTPCT + 同步 RTC；resume 后读 RTC 换算流逝 cycles 累加 offset；LIGHT 档 CNTPCT 不停走则 offset=0 跳过。配套：`HalClockTickTimerReload/GetTickTimerCycles`（现成原语）实现 `OsPmTickTimerStop/Start` 真实逻辑 | `los_sched_pri.h:82-85`、`los_sys.c:38-41`、`los_pm.c:86-96`、`arm_generic_timer.c:164-183`；RTC 驱动已就绪 |
| K3  | **device 注册链表化**          | `LosPmCB.device` 单指针 → `LOS_DL_LIST`（参照 lockList）；suspend 按注册逆序、resume 正序（"越底层越晚睡越早醒"）；单设备失败按现有 prepare 回滚机制处理并记录失败设备                                                                                                                                      | `los_pm.c:66-82,229-240`                                                                           |
| K4  | **休眠自动进入 + 触发通道正规化**      | 方案 A（推荐）：产品侧覆写 WEAK `OsIdleTask` → `while(1){ LOS_PmReadLock(); LOS_PmSuspend(0); }`（SMP 从核另建 park 钩子，第一步先单核验证）；方案 B：独立 PM 管理任务。修复 `/proc/power/power_count` 权限 0444→0664 + proc_file.c 补权限校验；评估新增 PM syscall（用户态正规通道）                                     | `los_task.c:126-131`、`smp.c:99-101`、`power_proc.c:257-263`、`proc_file.c:595-658`                   |
| K5  | **缺陷修复**                  | `LOS_PmReadLock`：超时参数化 + 返回语义修正（区分超时/成功）；`LOS_PmSuspend(wakeCount)` 参数启用（对接 K1 竞态检查）；`SchedTaskFreeze` 扩展为休眠前批量冻结延时任务（减少唤醒源）                                                                                                                               | `los_pm.c:624-638`、`los_sched_pri.h:605-649`                                                       |

#### 3.2 L4 电源服务层扩展（base/powermgr/powermgr_lite，4 项）

| # | 改动 | 设计 |
|---|---|---|
| S1 | **修 small 假挂起桩**（P0，天级） | `small/auto_suspend_loop.c:29` 的 `sleep(10)` → 照抄 mini 版：`LOS_PmReadLock()` 等锁释放 → 触发 `LOS_PmSuspend`（经修正后的 /proc 通道或 K4 syscall） |
| S2 | **WakeSource 管理 API**（新增） | innerkits 新增 `RegisterWakeSource(type, config)/EnableWakeSource/DisableWakeSource`；type：RTC_ALARM（周期/单次时刻）、GPIO（引脚+边沿）、WIFI_WOW（pattern）、UART；服务侧维护唤醒源注册表，SuspendDevice 前统一下发到驱动层（经 HDF listener/直接驱动 API），补齐 powermgr_lite 无唤醒源管理的缺口 |
| S3 | **battery 对接真实数据源** | 替换 `battery_device.c` 硬编码：IBattery vtable 接 ADC 电量计/充电 IC 驱动（硬件相关，PoC 阶段可先接 ADC 分压采样） |
| S4 | **SuspendDevice 语义补全** | `suspendImmed` 参数生效（立即挂起 vs 准入放行）；补权限校验（pid 白名单/权限位）；`WAKEUP_WHEN_ACQUIRED` 标志实现（加锁即触发 WakeupDevice 链路） |

#### 3.3 L2 平台/驱动层（device/soc|board/hisilicon + drivers，6 项）

| # | 改动 | 设计 |
|---|---|---|
| B1 | **SYSCTRL 注册（核心新增）** | 新增 `device/soc/hisilicon/common/platform/pm/`：`LOS_PmRegister(LOS_PM_TYPE_SYSCTRL)` 实现四档回调——第一步 lightSuspend=外设时钟门控+WFI（可自主实现）；第三步 deepSuspend=full cache clean+inv（新增汇编，以 `los_hw_runstop.S` 死代码为起点）→DDR self-refresh→电源域关断（**依赖海思 dv300 低功耗 SDK，NDA**）；early/late 挂时间 offset 同步点（K2）与唤醒源配置（S2） |
| B2 | **驱动 PM listener 挂接** | 按裁剪后集合逐个挂 `HdfPmRegisterPowerListener`：mmc（休眠前 sync+时钟门控/断电，SD 三级省电策略）、rtc（保持，唤醒源）、gpio（wake-pin 配置）、uart（RX 唤醒，补硬件能力）、wlan HDI（对接 hi3881 芯片 PM）；框架链路现成（devmgr_pm_reg.c 已桥接内核） |
| B3 | **WiFi WoW 桥接** | hi3881 芯片级 PM+WoWLAN 已有（`plat_pm_wlan.c` 含 LITEOS 分支、`hmac_wow.c`、HDI `SetPowerSaveMode` 全链路）：aov_policy 在进入 S1/S2 前调 `HI_WOW_PATTERN_ADD` + `HI_LIGHT_SLEEP/HI_DEEP_SLEEP`，主控睡后 WiFi 保活（DTIM10），云指令经 WoW→GPIO/SDIO 中断唤醒主控；PS 模式参数化（DTIM/listen interval 权衡延迟与功耗） |
| B4 | **MPP 模块电源策略** | `hisi_sdk.c`（HDF_PLATFORM_HISI_SDK）对称接管 `SDK_exit()`（树内已有完整 mod_exit 序列，当前零调用者）：S2 进入前按序 deinit（VO/TDE 等已裁模块不涉及；VI/ISP/VENC 等值守模块 deinit→re-init 或保持最小配置），新增 `HI_SDK_EXIT/INIT` 触发通道 + 循环稳定性验证（PoC 项）；MMZ 重配 384MB→128~192MB + VB 池双档位（阶段 3 §3） |
| B5 | **DVFS 两档** | 直操 `PERI_CRG30_BASE`（`target_config.h:33`，cpu freq-mode CRG）：高档（全速）/低档（值守冲刺），切换点=S0/S1 状态迁移；决策输入=`LOS_HistorySysCpuUsage`（CPUP 已有）；与 PM 锁联动（持锁期间禁降档）；先实测两档功耗/性能曲线再定频点 |
| B6 | **唤醒源硬件配置** | RTC alarm（irq37/32，驱动链路完整）：aov_policy 每周期设置下一唤醒时刻（1s 节拍或缩时 2~4s）；GPIO（PL061 irq48+）：PIR/按键边沿唤醒；唤醒后 GIC 状态恢复检查（深睡场景） |

#### 3.4 时间连续性方案（P0，贯穿 L2~L5）

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

#### 3.5 值守期单帧循环（L5 业务接口约定）

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

#### 3.6 快启（TTFF）与启动重排

承接阶段 3 §5：快启关键路径 = uboot（预编译，树内不可裁，实测记录）→ kernel+MPP 静态模块 init → SD 挂载 → foundation+media_server → AOV 首帧落盘。设计动作：
- init cfg 服务三分组（关键路径 3 个/延迟组 4 个/裁剪组 6 个）；
- 延迟组以"首帧达成"事件为触发（aov_policy 发布 samgr 广播），而非固定 sleep；
- MPP mod_init 序列裁剪（阶段 3 §3 值守集 11 模块优先 init，事件期模块延迟 init）；
- **全链路分段打点**（见 3.7），无打点不验收。

#### 3.7 计量体系（P2-1，"无计量则无优化"）

| 计量项 | 实现 | 输出 |
|---|---|---|
| TTFF 分段 | uboot 时间戳（reg_info 阶段打点受限于预编译，用 GPIO 翻转+逻辑分析仪替代）/kernel init 各 level 耗时/MPP mod_init 逐模块耗时（sdk_init.c 插桩）/业务首帧 | 分段瀑布图，每项预算告警 |
| suspend/resume 耗时 | K2 offset 机制顺带记录（进/出 CNTPCT 差），挂 hievent 上报 | 唤醒窗口时间预算达成率 |
| PM 锁审计 | 扩展 `LOS_PmLockInfoShow`：持锁者+持锁时长+超时记录，hidumper 节点导出 | 定位"谁阻止了休眠" |
| 功耗实测 | 硬件：串联功率计（整板）+ 分模块电流探针（sensor/DDR/WiFi/SD）；软件：状态驻留时长统计（aov_policy 记录各态累计时间→换算平均功耗） | 指标验收 + 功耗模型校准（P_avg ≈ P_sleep+(P_wake−P_sleep)×duty） |
| 时间连续性 | 值守 24h/深睡 7d 后校验录像文件时间戳 vs RTC/NTP 真值 | 误差 ≤1s 验收 |

---

### 4. 三步走实施路线（承接阶段 2 §6，含改动清单）

#### 第一步：浅 AOV（树内闭环，1~2 人月，ev300 单核先行）

| 交付 | 改动清单 | 仓库 |
|---|---|---|
| 真实休眠触发 | S1 修桩 + K4 idle 挂钩/PM 任务 + /proc 权限修复 | powermgr_lite、kernel/liteos_a、（可选 syscall） |
| LIGHT 档实现 | B1 lightSuspend（时钟门控+WFI）+ B6 RTC alarm 唤醒桥接 | device/soc/hisilicon/common/platform/pm（新增） |
| 时间连续性 | K2 offset + 3.4 开机 RTC 校时 + sntp 编入 | kernel/liteos_a、third_party/lwip、init cfg |
| 单帧循环 PoC | 3.5 主循环（SNAP+sensor standby+攒批落盘+libmd 检测） | 业务 sample（新增，参照 sample_kol 公开实现） |
| 计量基线 | 3.7 TTFF 打点 + suspend/resume 耗时 + 功耗实测方法 | sdk_init.c 插桩、hidumper 扩展 |
| 裁剪第一刀 | 无屏化 7 项 + xts 3 项（低风险先行），依赖核查表前置 | vendor config.json、init cfg |

**验收**：值守循环 7×24 稳定（1 万次唤醒无失败）、时间轴误差 ≤1s、TTFF/唤醒窗口分段数据齐备、整板值守功耗基线实测值（作为第二步目标锚点）。

#### 第二步：标准 AOV（2~3 人月，dv300 目标平台）

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

#### 第三步：深睡 AOV（依赖海思 NDA 资料，获取后 2~3 人月起）

| 交付 | 改动清单 | 前置 |
|---|---|---|
| DEEP_SLEEP 平台实现 | B1 deepSuspend/deepResume：full cache clean+inv 汇编（los_hw_runstop.S 起点）+ DDR self-refresh + 电源域序列 | **海思 dv300 低功耗 SDK/KOL 类支持（NDA 硬阻塞）** |
| MPP 模块电源 | B4 SDK_exit 接管 + deinit/re-init 循环策略 | SDK_exit 稳定性 PoC |
| SMP 从核 park | dv300 双核：从核下线钩子（smp.c 独立路径）或关 SMP 单核产品形态 | 第二步完成 |
| SHUTDOWN 档 | S3 SOFT_OFF：handler 注册 + WiFi WoW/4G PSM 保活 + 冷启动恢复 | — |
| AI 检测升级 | NNIE 人形（子流）替换 libmd，误报与功耗双优化 | ai_engine 延迟加载链路 |

**验收**：STR ≤40mW（保底）/≤10mW（竞争）、深睡 7 天时间误差 ≤1s、唤醒 ≤250ms、续航 ≥13 天（9000mAh）。

---

### 5. 关键设计决策与理由

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

### 6. 风险清单

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

### 7. 交付物与下一步

1. 本文档 = 阶段 4 方案设计稿 → **评审动作**：与内核/驱动/业务/测试代表评审 §3 改动清单与 §4 路线，确认第一步范围；
2. **并行前置**（不阻塞评审）：
   - 裁剪依赖核查表（阶段 3 §7.1，RP2 方法逐组件反查 BUILD.gn）；
   - 海思 dv300 低功耗 SDK 可得性确认（R1，决定第三步是否启动）；
3. **下一步（阶段 5）**：按 §4 第一步清单出《PoC 验证计划》：ev300 环境搭建 → 计量基线（TTFF/功耗打点先行）→ S1 修桩+K4 → LIGHT 档+RTC 唤醒 → 单帧循环 → 1 万次唤醒稳定性 → 浅 AOV 功耗基线报告。

## PoC 验证计划（浅 AOV·第一步）

### 1. 平台与环境

#### 1.1 平台选择（修订阶段 4 §5 决策）

| 平台 | 角色 | 理由 |
|---|---|---|
| **hispark_taurus（hi3516dv300）** | **PoC 主平台** | camera_lite/media_lite/powermgr_lite 产品配置齐全（config.json:174-180）；MPP 静态链入、HI_MPI_SNAP/imx335 钩子齐备；~~构建配置关 `LOSCFG_KERNEL_SMP` 做单核原型~~ **【T6 第三批实证否决：海思 MPP 预编译库/dwc_usb3 依赖 SMP 编译的 LOS_SpinLock 外部符号，关 SMP 链接失败】→ dv300 保持 SMP，深睡期从核 park 机制自研（阶段 4 P1-5 升为唯一路线）** |
| hispark_aries（hi3518ev300） | 跨平台对照（次优先） | 单核原生；powermgr 未启用——启用动作本身即验证项（阶段 2 P2-5）；MPP 为 hi3516ev200_* .so 不同构，业务层平台无关性检验 |

#### 1.2 构建环境现状与风险（T0 前置事实）

- 工具链已就位：`prebuilts/gcc/linux-x86/arm/gcc-linaro-7.5.0-arm-linux-gnueabi`（`workspace/openharmony_prebuilts` 同名 tar 已解包）；hb 已安装（pyenv shim）；python 3.9.23；
- **已知风险**：out/ 下存在一次失败构建记录（`ipcamera_hispark_taurus_linux` build.log：Broken pipe / UNKNOWN ERROR），且本代码树为 api_version 8 老世代 BSP + 新 manifest 混合——**构建打通是 T0 的第一风险项**，预留排障时间；
- 构建命令基线：`hb set`（选 ipcamera_hispark_taurus）+ `hb build -f --gn-args ohos_build_type='"release"'`；或 `./build.sh --product-name ipcamera_hispark_taurus`；
- 烧录/调试：串口（115200）+ SD 卡/eMMC 烧录（uboot 预编译，按海思 hispark 常规烧录流程）；
- 计量硬件：直流功率计/源表（整板串联，采样 ≥10Hz）、万用表、（可选）示波器或逻辑分析仪 + 空闲 GPIO×2（TTFF 硬件打点）、SD 卡（FAT32）。

---

### 2. 验证任务分解（T0~T7）

> 依赖关系：T0→T1→(T2→T3→T4)→T5→T7；T6 与 T2~T5 并行。

#### T0 构建打通与基线镜像（估 3~5 天，含排障）

| 项 | 内容 |
|---|---|
| 目的 | taurus（关 SMP）与 aries 双平台 release 镜像构建通过；建立裁剪/优化前基线 |
| 步骤 | ① 修复构建环境（参照 out/build.log 失败记录排障）② taurus kernel_configs 关 SMP 构建单核原型 ③ aries config.json 启用 powermgr 子系统块（照抄 taurus:174-180，不开 screensaver，确认 ipc 组件在列）④ 烧录启动，串口确认 foundation/media_server 正常、camera sample 可预览/录像 |
| 计量点 | **镜像基线**：各分区 bin size（uboot/kernel/rootfs/userfs）、启动后空闲内存水位（hidumper/meminfo）、空闲态整板功耗（WFI idle，功率计 10 分钟均值）、开机到 shell 就绪时间（串口时间戳） |
| 通过标准 | 双平台镜像可烧录、系统可启动、录像链路手动验证通过、基线数据四件套齐备 |
| 产出 | 《T0 基线报告》（size/内存/功耗/启动时间四基线）+ 可复现构建脚本 |

#### T1 计量埋点体系（估 3 天）

| 项 | 内容 |
|---|---|
| 目的 | "无计量则无优化"（阶段 2 P2-1）：TTFF 分段 + PM 事件打点先行，后续所有优化用它度量 |
| 改动 | ① `sdk_liteos/mpp/module_init/src/sdk_init.c`：逐 mod_init 前后插桩（时间戳+模块名，hilog/串口输出）② kernel init level 耗时（`LOS_MODULE_INIT` 链打点，los_pm.c 同款机制遍历）③ 业务首帧点：camera/media 首帧回调处 GPIO 翻转 + 串口时间戳 ④ PM 锁审计：扩展 `LOS_PmLockInfoShow`（持锁者+时长）挂 hidumper ⑤ suspend/resume 耗时钩子（K2 的 CNTPCT 记录点顺带输出） |
| 计量点 | TTFF 瀑布：uboot（GPIO 上电沿→kernel 首打印，硬件打点）/kernel/MPP mod_init/业务首帧，各段 ms 级 |
| 通过标准 | 冷启动 10 次采样，各段耗时可复现（方差 <10%），瀑布图输出脚本化 |
| 产出 | 埋点 patch 集 + 《TTFF 分段基线报告》 |

#### T2 真实休眠触发链路（估 4 天）——阶段 4 S1+K4

| 项 | 内容 |
|---|---|
| 目的 | 打通"业务允许睡 → 系统真的进入内核 PM 休眠"链路（当前三重空置的第一层） |
| 改动 | ① `powermgr_lite/services/src/power/small/auto_suspend_loop.c:29`：sleep(10) 桩 → 照抄 mini 版 `LOS_PmReadLock()+LOS_PmSuspend`（经修正通道）② `power_proc.c:257-263`：power_count 权限 0444→0664；`proc_file.c` 补权限校验 ③ 产品侧覆写 WEAK `OsIdleTask`（单核原型下无从核问题）：`while(1){LOS_PmReadLock(); LOS_PmSuspend(0);}` ④ `LOS_PmReadLock` 超时参数化+返回语义修复（los_pm.c:624-632） |
| 步骤 | RunningLock 持/放 API 触发（测试程序 AcquireRunningLock(BACKGROUND)→Release）→ 观察串口 PM 进入/退出打印（默认 handler PRINTK 即证据）→ 空闲态功耗对比 T0 基线（默认 handler=WFI，功耗应≈基线，本项验证**链路**不验证收益） |
| 通过标准 | 锁持有期间不进休眠；释放后 500ms 内进入 `OsPmSuspendDefaultHandler`；1000 次锁循环无死锁/无睡死（看门狗验证） |
| 产出 | patch（powermgr_lite×2 文件 + kernel×3 文件 + 产品覆写×1）+ 链路验证报告 |

#### T3 LIGHT 档 + RTC 定时唤醒（估 5~7 天）——阶段 4 B1(浅)+B6

| 项 | 内容 |
|---|---|
| 目的 | 值守态载体：LIGHT_SLEEP 档真实实现（时钟门控级）+ RTC alarm 周期唤醒闭环 |
| 改动 | ① 新增 `device/soc/hisilicon/common/platform/pm/`：`LOS_PmRegister(LOS_PM_TYPE_SYSCTRL)` 注册 lightSuspend/lightResume（第一步实现=可安全门控的外设时钟关断（保守清单：VO/显示类 CRG 位，逐个实测）+ WFI；深睡序列不做）② RTC alarm 唤醒桥接：测试程序经 HDF RTC API（`RtcWriteAlarm/RtcAlarmInterruptEnable`，rtc_hi35xx.c 链路已就绪，irq37）设 1s 周期 alarm → 休眠 → alarm 唤醒 → 回调计数 ③ GPIO 唤醒验证（PL061 边沿中断，按键/模拟 PIR） |
| 计量点 | 唤醒延迟分解：alarm IRQ→resume 完成→业务回调（串口时间戳）；LIGHT 态整板功耗 vs T0 空闲基线（时钟门控收益） |
| 通过标准 | 1s 周期 alarm 唤醒 24h 无丢失（86400±容差次）；唤醒延迟 ≤500ms（保底，实测记录分解）；LIGHT 态功耗低于 T0 空闲基线（收益为时钟门控级即可，深睡收益属第三步） |
| 产出 | pm 平台层 patch + RTC/GPIO 唤醒验证报告（含唤醒延迟分解表） |

#### T4 时间连续性（估 5 天）——阶段 4 K2+3.4

| 项 | 内容 |
|---|---|
| 目的 | AOV 致命项闭环：休眠/唤醒不丢时间，录像时间轴连续 |
| 改动 | ① 内核 offset：`los_sched_pri.h OsGetCurrSchedTimeCycle()` 加 `g_osTimeOffsetCycle`；suspend 前记 CNTPCT+读 RTC，resume 后 RTC 差值换算累加（LIGHT 档 CNTPCT 不停走则跳过，为第三步 DEEP 预埋）② `OsPmTickTimerStop/Start` 用 `HalClockTickTimerReload/GetTickTimerCycles` 实现真实逻辑（los_pm.c:86-96 空桩）③ 开机 RTC 校时：init pre-init job 或 foundation 内任务 `RtcReadTime→settimeofday` ④ sntp 编入：替换 `fixme.c:391` 空桩，编入 `third_party/lwip/src/apps/sntp/sntp.c` + `SNTP_SET_SYSTEM_TIME` 回调 + 周期校时（6h）+ 校时写回 RTC |
| 计量点 | 24h 值守循环后：录像文件时间戳 vs NTP 真值误差；gettimeofday/LOS_TickCountGet/软定时器三者一致性；跨休眠软定时器到期精度 |
| 通过标准 | **24h 时间轴误差 ≤1s**；休眠期软定时器不漂移（唤醒后到期时刻正确）；NTP 断网场景退化为 RTC 走时（误差记录） |
| 产出 | 时间连续性 patch（kernel×3 + lwip×2 + init cfg）+ 24h 校验报告 |

#### T5 值守单帧循环 + 稳定性（估 7~10 天）——阶段 4 §3.5

| 项 | 内容 |
|---|---|
| 目的 | 浅 AOV 业务闭环：RTC 唤醒→单帧采集编码→检测→攒批落盘→回睡 |
| 实现 | 新增 aov_poc 业务任务（media_server 内或独立 bin，参照海思公开 sample_kol 结构与树内 store_sample）：① sensor standby/restart（imx335 `pfnStandby/pfnRestart` 预编译钩子，先 MPI 层验证行为）② `HI_MPI_SNAP_TriggerPipe` 单帧采集（mpi_snap.h）③ VENC H.264/H.265 编码（GOP 策略：I 帧间隔=缩时段落锚点）④ libmd 移动侦测（MPP libmd.a，768×448 子流）命中→升全速 15fps×15s（滞回 5 帧）⑤ 攒批落盘：1MB 缓冲满/事件/休眠前 fsync（FATFS）⑥ 循环尾设下一 RTC alarm→经 T2/T3 链路休眠；唤醒窗口步骤②~⑥分段打点（T1 体系） |
| 稳定性 | 自动化：1s 周期×**1 万次唤醒**（≈2.8h）+ 4s 缩时周期×24h 长稳；串口日志解析脚本统计失败率/唤醒延迟分布/时间漂移/SD 写入错误 |
| 通过标准 | **1 万次唤醒 0 失败**；唤醒窗口（sensor restart→落盘完成）≤100ms 目标值实测（未达则给出分解与优化项）；24h 长稳录像文件时间轴连续（联动 T4 标准）；事件触发→全速切换 ≤2s（第一步口径） |
| 产出 | aov_poc 业务 patch + 稳定性测试脚本 + 《单帧循环验证报告》 |

#### T6 裁剪第一刀落地（估 3~4 天，与 T2~T5 并行）——核查表第一批

| 项 | 内容 |
|---|---|
| 目的 | 验证裁剪方案正确性与实测收益（修正声明值口径） |
| 范围 | 《裁剪依赖核查表》第一批 9 项：camera_sample_app、camera_screensaver_app、drivers_peripheral_light、device_auth、device_security_level、acts、tools、syscap_codec、device_attest_lite（仓库留树）+ enable_screensaver=false + 对应 init cfg×2 条目删除；aries 启用 powermgr（T0 已做） |
| 步骤 | 独立分支实施 → 双平台构建 → 烧录回归（启动链/录像/OTA 接口冒烟）→ 与 T0 基线对比 |
| 计量点 | 镜像 size 差（分区级+文件级 top20）、启动内存水位差、开机时间差、init 日志无 execv 失败噪声 |
| 通过标准 | 构建通过、系统功能回归无退化、**实测收益表**产出（替换阶段 3 声明值预估） |
| 产出 | 裁剪 patch 集 + config.json/init cfg 修订版 + 《第一批裁剪收益实测报告》 |

#### T7 浅 AOV 功耗基线报告（估 2 天，汇总）

| 项 | 内容 |
|---|---|
| 目的 | 第一步总验收 + 第二步目标锚定 |
| 内容 | ① 值守态（T5 循环运行中）整板平均功耗（功率计 ≥30min 采样，P_avg 与占空比公式互验）② 各状态功耗矩阵：全速/事件切换/值守/LIGHT 睡/空闲（T0）③ 唤醒窗口时间预算达成表 ④ TTFF 瀑布（T1）⑤ 续航折算（按 9000mAh/5V 换算天数，对照阶段 1 §4 基线表）⑥ 与业界对标差距分析（vs 80mW 保底/45mW 竞争）→ 输出第二步（标准 AOV）优化项优先级排序 |
| 通过标准 | 阶段 4 第一步验收四项全达成；差距分析给出第二步 P1 项的量化预期 |
| 产出 | **《浅 AOV PoC 功耗基线报告》**（阶段 5 核心交付物，第二步立项依据） |

---

### 3. 计量方法规范

| 计量项 | 方法 | 工具 |
|---|---|---|
| 整板功耗 | 电源串联功率计，采样 ≥10Hz；每状态 ≥10min 稳态均值；记录供电电压（5V/整板口径） | 功率计/源表 |
| 分段功耗（可选） | sensor/DDR/WiFi/SD 支路分流或替换供电点 | 万用表+分流器 |
| TTFF/唤醒延迟 | 硬件：GPIO 翻转+示波器（上电沿、kernel 首打印、首帧点）；软件：串口时间戳+hilog；两者交叉校准 | 示波器/串口脚本 |
| 时间漂移 | 录像文件时间戳 vs NTP 真值（PC 端脚本比对）；RTC 读数 vs 系统时间 | 测试脚本 |
| 内存水位 | hidumper/meminfo 启动后稳定值；裁剪前后同点位对比 | hidumper |
| 稳定性 | 自动化循环+串口日志解析（失败率/延迟分布/漂移统计） | python 脚本 |

### 4. 排期建议（单人 4~5 周 / 双人 3 周）

| 周 | 任务 |
|---|---|
| W1 | T0 构建打通（风险项优先）+ T1 埋点 |
| W2 | T2 休眠链路 + T3 LIGHT/RTC 唤醒（T6 并行启动） |
| W3 | T4 时间连续性 + T5 单帧循环开发 |
| W4 | T5 万次唤醒+24h 长稳 + T6 收益实测 |
| W5 | T7 汇总报告 + 补丁集整理归档 |

### 5. 风险与依赖

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| 1 | 老世代 BSP+新 manifest 混合树构建失败（已有失败记录） | **高** | T0 首位排障；备选：锁定纯 OpenHarmony 3.1/3.2 Release 对照树重建 |
| 2 | 硬件可得性：taurus/aries 板卡、功率计、示波器 | 高 | 启动前确认清单；无功率计则先以电流采样替代（精度降级标注） |
| 3 | imx335 standby/restart 钩子在 liteos 预编译库中的实际行为未知 | 中 | T5 先做 MPI 层单项验证；不通则以 VI stop/start 替代（收益降级记录） |
| 4 | HI_MPI_SNAP 在 dv300 liteos MPP 的行为/文档缺失 | 中 | 备选：VI-VENC 单帧通道启停方案（sample_venc 参照） |
| 5 | 关中断 suspend 模型下 RTC IRQ 唤醒时序异常 | 中 | T3 先裸验证 alarm IRQ 唤醒 WFI；异常则引入唤醒源前置使能（GIC 配置）专项 |
| 6 | SD 卡攒批写入掉电/休眠一致性 | 低 | fsync+休眠前 sync 纪律（阶段 4 3.5 步骤 7）；FATFS cache sync thread 评估开启 |
| 7 | PoC 补丁与基线分支管理混乱 | 低 | 独立 patch 集管理（每 T 一组 patch+README），不合入基线直至评审 |

### 6. 交付物清单（阶段 5 总产出）

1. PoC patch 集（T1~T6，按仓库分组：kernel_liteos_a / powermgr_lite / device_soc_hisilicon / vendor_hispark / lwip / init / aov_poc 业务）
2. 测试与计量脚本集（TTFF 解析、稳定性循环、时间漂移比对、功耗采样）
3. 报告：T0 基线 / TTFF 分段 / 唤醒延迟分解 / 时间连续性 24h / 单帧循环与万次唤醒 / 第一批裁剪收益实测 / **浅 AOV 功耗基线报告（T7，核心）**
4. 第二步（标准 AOV）优化项优先级排序与量化预期（T7 附属结论，作为阶段 4 §4 第二步的启动输入）
