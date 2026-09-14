# IPC AOV 业界方案调研报告

| 项目 | 内容 |
|---|---|
| 文档名称 | IPC AOV（Always-On Video）业界方案调研报告 |
| 文档版本 | V1.0 |
| 日期 | 2026-09-10 |
| 所属专项 | OpenHarmony L1 小型系统低功耗与小型化优化（基于海思 IPC 实现 AOV 全天候持续录像） |
| 文档目的 | 调研业界 AOV 方案，反推功耗指标基线，建立"AOV 技术点 → OH L1 系统层落点"映射，为后续差距分析与方案设计提供输入 |
| 资料来源 | 仅公开渠道（官网/官方 PDF/新闻/技术社区/学术资料），访问日期均 2026-09-10；商业授权 SDK 文档不可得处已显式标注 |
| 原始材料 | `01_research/A~E` 五篇分项调研（共 2130 行，含完整引用） |

---

## 1. AOV 定义与业务价值

### 1.1 定义

AOV（Always-On Video，全天候持续录像/全时录像）：**基于超低功耗内存（DDR self-refresh）的快速启动待机技术，实现电池 IPC 7×24 小时不间断录像**。2023 年 CPSE 由北京君正首发（T41），海思在 SDK 层将其命名为 **KOL 模式**（官方方案品牌"越影 S610"），瑞芯微有官方 AOV 产品系列（RV1106G2 / RV1126B "AOV 3.0"）。

### 1.2 业务价值：解决 PIR 触发式的三大痛点

| 痛点 | PIR 事件触发式 | AOV 全时录像 |
|---|---|---|
| 漏录 | 事件间隙无画面，事后无完整证据链 | 7×24 不间断，0 漏报（觅睿产品口径） |
| 检测距离 | PIR <10m，受热源/天气影响 | 图像 AI 检测 25~70m（日 30m/夜 20m 典型） |
| 误报 | PIR 误触发功耗与体验双损 | AI 人车过滤，误报大幅下降（帧差+光感动态阈值可再降 80%） |

### 1.3 竞争格局结论

- **AOV 是中国芯片生态主导的差异化路线**：君正、海思、瑞芯微、国科微、安凯微、富瀚微、全志、星宸均已布局；国内终端品牌（萤石、Tapo/TP-LINK、小米、乐橙、觅睿、海康）2024 年起全面 AOV 化。
- **国际四强（Ring/Arlo/Wyze/eufy）电池机均无 AOV**：其 24/7 连续录像强制"常电 + 订阅 + 云存储"（Ring Home Premium $19.99/月、Arlo Secure 云 30 天），与 AOV"电池供电 + 本地缩时存储 + 免订阅"形成鲜明路线差异。Ambarella 布局最早（S2Lm 2015 唤醒 <500ms 出流）但不使用 AOV 术语，待机功耗数值从未公开。
- 技术代际基准线：**传统 PIR 方案休眠 >100mW / 唤醒 2~3s → AOV 1fps 值守 ~40mW 级 → AOV 3.0（音频唤醒 AOA）待机 ~1mW 级**。

---

## 2. 厂商方案横向对比

### 2.1 主控芯片方案对比总表

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

### 2.2 海思 KOL 模式关键细节（本项目直接对标对象）

来源：Apache-2.0 公开头文件 `ss_mpi_syskol.h` 与 sample_kol 参考实现源码（24 文件，公开可得）。

- **API**：`ss_mpi_syskol_set/get_param`、`ss_mpi_syskol_sleep`、`ss_mpi_syskol_wakeup`、`ss_mpi_syskol_suspend`（下电方案，新版本是否开放待确认）
- **休眠 4 级**（`ot_syskol_param`）：NONE / LIGHT（保 RTSP 在线）/ **DEEP**（全 IP 停 + sensor standby + DDR STR，检测到目标才按需起 RTSP）/ USER（`audio_cken` 位可休眠保留音频 = AOA 基础）
- **采集模式**：NORMAL / **SINGLE**（睡后采 1 帧）——AOV 单帧循环的核心
- **AOV 周期时序**：restart sensor → 采 1 帧 → 编码 → AI 检测（768×448 子流）→ sensor standby → sleep（默认 1000ms → 1fps）
- **唤醒源**：always-on BSP timer（sysfs）、GPIO/input event、RTC、UART、MCU-4G
- **存储策略**：1MB 内存攒批满才落盘（减少 SD IO 唤醒次数）；多目走 MIPI-Switch 轮询 + 卷绕压缩（wrap）
- **老平台差异**：CV100 / Hi3518EV200/EV300 / Hi3516DV300/CV500 **无原生 KOL**，只能靠"外部超低功耗 MCU+PMU 保活 + SoC 下电/STR + 快启"做事件触发型待机，睡眠期存在录像断档
- **生态关键事实**：海思 CV610 官方 SDK 支持 OpenHarmony 4.1，OH + 海思 AOV 硬件通道已有官方背书

### 2.3 终端产品指标对比（产品级，供反推续航基线）

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

## 3. 共性技术架构归纳

业界 AOV 方案收敛为**五层技术栈 + 一个功耗状态机**（详见 `01_research/E_common_tech_topics.md`）：

### 3.1 功耗状态机（业界收敛为 4 级）

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

| 状态 | 功耗数量级 | 代表数据点 |
|---|---|---|
| 全速 Active | **1~3W+** | T41 1080p30 整机 1.2~1.5W；RV1126B 整板全帧率+AI 1280mW |
| 空闲（未休眠） | 数百 mW | RV1126B 整板空闲 580mW |
| AOV 值守 | **40~180mW** | 君正 40+mW；CV610 80mW；RV1106 ~40mW；国科微单板 42mW |
| STR 深度休眠 | **1~40mW** | 君正 1mW 级（宣称）；RV1126B 核心板 7mW；工程口径"较好的芯片 40mW" |
| 网络保活（SoC 下电） | mA~μA 级 | WiFi STA PS ~5mA；4G Cat.1 PSM <5μA；全志 DTIM10 保活 180μA |
| 关机/仅 RTC | μA 级 | sensor 待机 <10μW；SSC303/306 μA 级 |

切换条件矩阵：事件（AI/PIR/音频）、RTC 定时、云指令、电量阈值（低电量降档 AOV→保活）、太阳能输入（升档）、**"上传完成才可休眠"**（强约束）。

### 3.2 第一层：硬件功耗域设计

- **DDR self-refresh**：CKE 拉低内部自刷新（退出需 tXS/ZQ 校准时序），AOV 的地基（"超低功耗内存"即指此）
- **CPU retention / PHY retention**：保持逻辑与信号状态，唤醒免重初始化
- **电源域分域关断 + 时钟树修剪**（MHz→32kHz）
- **低功耗岛常驻**：PMU/AOP 仲裁唤醒源；值守与处理硬件分离——君正 RISC-V 协处理器、星宸 M4 小核、全志双 RISC-V + XR806 WiFi MCU、瑞芯微 AOA 音频通路
- **sensor 低功耗**：standby <10μW、帧消隐 ≥33ms（海思硬约束）、快启出图 40~60ms（vs 传统 >250ms）、in-sensor 检测（Sony IMX500 片上 AI 3.1ms）

### 3.3 第二层：快速启动（TTFF 导向）

目标是**首帧时间（TTFF）而非开机时间**，三段流水线并行：

| 阶段 | 手段 | 典型收益 |
|---|---|---|
| bootloader | 裁剪/Falcon 模式（跳过 U-Boot 直接拉起 kernel）/加载与 sensor 初始化并行 | 省 300~500ms |
| kernel | 去打印（每条数 ms）、裁剪、**XIP 从 SPI NOR 直执**、出图驱动提权 | — |
| rootfs/应用 | ramfs 以内存换时间、rcS 主程序优先+业务并行、prelink/dlopen、非必需文件延后加载 | — |

业界快启标杆：君正 Atlas **<100ms**、RV1126B 0.1s、星宸 SSC306 首帧 68ms、全志 V853 200ms 首帧/700ms 冷启动、君正 T31 首帧 200ms。

### 3.4 第三层：STR 待机与唤醒

- **软件流程**（Linux 范式，RTOS 同构）：freeze 进程 → 6 阶段设备挂起 → syscore → enter；唤醒逆序恢复
- **AOV 特有形态**："单帧 suspend-resume 循环"——每周期只处理 1 帧即回睡
- **唤醒源设计**：RTC 定时（心跳）、GPIO/PIR、WoWLAN/云指令（经保活芯片转发）、声音（AOA 异常声源/哭声）、小核 AI 命中
- **唤醒延迟**：新一代 <100ms vs 传统触发式 2~3s
- **防误睡/防睡死**：wakeup_count 竞态处理（休眠入口原子检查"锁计数+未决唤醒事件"）、状态看门狗（AOV 循环超上限保护）

### 3.5 第四层：占空比录像策略

核心公式：**P_avg ≈ P_sleep + (P_wake − P_sleep) × duty**
（例：休眠 40mW + 每秒醒 10ms@1W ≈ 50mW；**唤醒窗口每省 5ms，续航近翻倍**）

- 值守帧率：1fps 主流（海思/瑞芯微/国科微），君正更激进 0.5~4fps 缩时可调
- 事件切换：切 15~30fps 全速，**滞回设计**（连续 5 帧无目标才退回值守）
- 值守降质：降分辨率（VGA）/缩略图/灰度；帧差+光感动态阈值（误报 -80%）
- 编码存储：智能编码省 50% 码率；**抓拍替代全帧省 90% 存储**（觅睿全天 600MB vs 15GB）
- 学术参照 sleepyCAM：PIR+继电器门控等待期 5.4mW vs 主机常开 1423.6mW（6000mAh→108 天）

### 3.6 第五层：存储与网络链路省电

- **SD 卡三级省电**：idle 1~3mA / 时钟门控数百 μA / **断电 130μA**（MOS 管开关，须守时序：VDD<0.5V 保持 1ms、上电 74 clk 后 CMD0、<400kHz 初始化）；实测整机 15mA→6mA
- **攒批落盘**：AOV 缓冲满（海思 1MB）或事件唤醒时才写卡；休眠前 sync+卸载驱动
- **WiFi 省电**：DTIM/listen interval 调参（延迟 100ms~1s 换功耗降至 1/3~1/10）；主控深睡时 WiFi 芯片/MCU 保活 + UART 唤醒
- **事件上传完成 = 休眠前置条件**

---

## 4. 本项目指标基线建议（调研反推）

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

## 5. AOV 技术点 → OH L1 系统层落点映射矩阵

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

## 6. 信息缺口与风险提示（汇总）

| 类别 | 缺口 | 影响 | 对策 |
|---|---|---|---|
| 海思 | SoC 级 AOV 各休眠态 mW 官方值；《KOL模式使用指南》《电池类低功耗设计指导书》原文；`ss_mpi_syskol_suspend` 新版本开放性；KOL DEEP 态 DDR 寄存器级细节；官方续航-帧率曲线 | 指标对标依赖营销值与板级实测 | 公开头文件+sample 源码已足够支撑架构设计；数值以 PoC 实测为准；如有商业 SDK 渠道再补 |
| 海思 | CV100/Hi3518EV300/DV300 一手 datasheet 低功耗章节 | 老平台迁移路线细节受限 | 老平台无原生 KOL 已确认，方案按"外部 MCU 保活+STR+快启"设计 |
| 君正 | AOV 内存自刷新电路级机制白皮书；"40+mW"测试条件；T42/T33V 规格 | 跨平台借鉴深度受限 | 以选型指南+产品案例口径为准 |
| 其他厂商 | 星宸/全志/安凯微/富瀚微多项 AOV 态功耗与快启数值不可得；富瀚微 4.5mW 口径存疑 | 横向对比表部分留白 | 已标注，不采信存疑值做指标依据 |
| 国际 | Ambarella/Sony 安防线待机功耗从不公开 | 国际对标缺数值 | 以架构思想（低功耗岛、AI Timelapse）借鉴为主 |
| 终端 | Ring/Arlo 电池容量从不公布；部分国行价格/续航登录墙 | 产品级对比留白 | 不影响系统层方案设计 |

---

## 7. 对后续阶段的输入结论

1. **阶段 2（OH L1 现状与差距分析）**：以第 5 节映射矩阵 15 项为清单，逐项核对本地源码树（`kernel/liteos_a` PM、`powermgr_lite`、HDF PM、`device/soc/hisilicon` BSP），产出差距分析报告；重点验证三大核心缺口。
2. **阶段 3（业务分析与裁剪）**：AOV 值守期最小必需集 = VI(单帧)+VENC+AI 子流+SD 存储+RTC；裁剪对象 = 全速期才需要的 RTSP/ONVIF/音频/补光/云台等按需加载（借鉴 RP2 裁剪方法论与海思 LIGHT 态"保 RTSP"vs DEEP 态"按需起 RTSP"的分态设计）。
3. **阶段 4（方案设计）**：以海思 KOL 三态机 + 业界 4 级功耗状态机为蓝本，设计 OH L1 系统层 AOV 框架（状态机服务、PM 锁治理、唤醒链路、TTFF 预算）；指标采用第 4 节基线。
4. **阶段 5（PoC）**：以 sample_kol 公开参考实现为蓝本，最小验证"RTC 定时唤醒 → 单帧采集编码 → 攒批落盘 → DEEP 休眠"循环 + 分段功耗/时间打点。

---

## 8. 参考资料

完整参考资料（约 200 条，均含 URL 与访问日期 2026-09-10）见各分项报告文末：

| 分项报告 | 主题 | 参考条数 |
|---|---|---|
| `01_research/A_hisilicon_aov.md` | 海思 KOL/AOV 方案 | 含官方 PDF、Apache-2.0 头文件与源码、板级实测规格书 |
| `01_research/B_ingenic_aov.md` | 君正 AOV 方案与选型指南 | 28 条 |
| `01_research/C_other_domestic_vendors.md` | 瑞芯微/国科微/全志/星宸/安凯微/富瀚微 | 35 条 |
| `01_research/D_ambarella_sensor_products.md` | Ambarella/sensor/终端产品 | 67 条 |
| `01_research/E_common_tech_topics.md` | 快启/STR/占空比/状态机/存储网络/RTOS 框架 | 55 条 |

核心一手来源索引见 `99_refs/references.md`。
