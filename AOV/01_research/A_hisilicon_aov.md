# 海思（HiSilicon）IPC 芯片 AOV（Always-On Video）低功耗方案调研

> 调研对象：Hi3516CV610 / Hi3516CV608（重点），兼顾 Hi3516CV100、Hi3518 系列等老平台
> 调研日期：2026-09-10（所有 URL 访问日期均为 2026-09-10，除非另行标注）
> 调研方法：海思官网产品页、官方公开 SDK 文档仓库（GitCode HiSpark）、官方公开 MPP Sample 源码仓库（Gitee 易百纳 e-hi3516cv610）、官方产品简介 PDF、开发板规格书 PDF、KOL 参考实现源码静态分析、行业媒体/论坛/博客交叉验证

---

## 0. 摘要（TL;DR）

1. **海思把 AOV 在 SDK 层命名为「KOL 模式」**（Keep-On-Line / 低功耗在线录像）。公开渠道可获得完整的 KOL 参考实现源码（`sample_kol`，24 个源文件）、官方头文件（`ot_common_syskol.h` / `ss_mpi_syskol.h`，Apache-2.0）、官方产品简介 PDF 与开发板实测功耗数据。
2. **AOV 的本质是「周期性休眠-唤醒-单帧采集」的占空比录像**：默认 `sleep_time = 1000ms` → 1 帧/秒；休眠模式分 `NONE / LIGHT / DEEP / USER` 四级；DEEP 模式所有 IP 停止、sensor 进入 standby、DDR 进入 STR（Suspend-To-RAM）。
3. **官方芯片级典型功耗**：Hi3516CV610 = **1043 mW**，Hi3516CV608 = **668 mW**（全速典型值，见官方产品简介 PDF）。**官方 PDF 并未给出 AOV 模式功耗数值**。
4. 市场流传的「**AOV 80mW @1fps**」仅见于开发板/方案商营销文案（CSDN 等），**公开渠道无法核实**；而公开的开发板规格书实测 KOL 深睡眠为 **70mA@5V ≈ 350mW（整板）**，浅睡眠 **122mA@5V ≈ 610mW（整板）**。80mW 与板级实测存在数量级差异，应理解为「SoC 级/优化后产品级」口径，公开数据不支持直接复现。
5. 老平台（Hi3516CV100、Hi3518EV200/EV300、Hi3516DV300/CV500）**没有原生 KOL/AOV**，电池类产品靠「外部超低功耗 MCU + PMU 保活 + SoC 完全下电 + 快启（fastboot/STR 恢复）」模拟，属事件触发型（PIR/门铃），存在录像断档，与 AOV 的连续低帧率录像有本质区别。

---

## 1. 方案概览

### 1.1 术语对应关系

| 市场/官方宣传用语 | SDK/代码层名称 | 说明 |
|---|---|---|
| AOV（Always-On Video） | **KOL 模式** | 低功耗在线录像；sample 目录 `mpp/sample/kol`，可执行文件 `sample_kol` |
| 越影 S610（方案品牌） | Hi3516CV610 + AiComponent | 上海海思官方 AOV 解决方案品牌名「越影」，对应芯片 S610=Hi3516CV610；组件 readme 名 `HiYueyingS610_AiComponent_readme.txt` |
| 快启 / 快速启动 | quick_start / fast_ae / warm boot | ISP/AE 状态保持 + DDR 参数保持，实现唤醒后 3 帧内出图 |
| 待机到 RAM | STR / Suspend-To-RAM | DEEP 休眠模式底层机制 |
| 亚帧级卷绕压缩 | VI wrap（`ss_mpi_vi_set_pipe_buf_wrap_attr`） | 降低内存带宽/延迟的 buffer 卷绕技术 |

来源：
- KOL=AOV 对应：Gitee 仓库 README（`sample源码路径:Hi3516CV610_SDK_V1.0.2.0/smp/a7_linux/source/mpp/sample/kol`）与 CSDN 开发板商品页「低功耗AOV例程（KOL）」，2026-09-10 访问。
- 越影 S610：电子发烧友转载海思官方公众号文章《芯闻速递 | 越影S610：无电无网无光？这个摄像头方案全搞定！》，2026-09-10 访问。

### 1.2 芯片矩阵与 AOV 支持

| 芯片 | 定位 | AOV/KOL 原生支持 | 关键低功耗特征 | 来源 |
|---|---|---|---|---|
| **Hi3516CV610** | 安防/消费 IPC SoC，4K@25/6M@30，1T NPU | **是**（官方 PDF 关键特性列「AOV 低功耗方案」） | KOL 三态状态机、4 级休眠、DDR STR、sensor standby、Fast AE、多目 MIPI-Switch | 官方产品简介 PDF v04 (2025-03-28) |
| **Hi3516CV608** | 消费类 IPC SoC，3M@30，0.2T NPU | **官方 PDF 未列 AOV**；SDK 提供 CV608 load 脚本与 ko，但无 AI ISP、无 WDR | 同代 KOL 框架可移植，但算力/ISP 阉割 | 官方产品简介 PDF v02 (2024-09-06)；Gitee load 脚本 |
| Hi3516CV100 | 老一代高清 IPC，ARM926，1080p30 H.264 | 否 | 仅常规时钟门控/模块级低功耗 | EmbedIc 器件页 |
| Hi3518EV200 / EV300 | 消费门铃/猫眼 | 否 | 外部 MCU+PMU 保活 + SoC 下电快启 | 52solution 方案页、CSDN |
| Hi3516DV300 / CV500 | 老一代 AI IPC | 否 | STR/快启模拟 | 行业资料 |

### 1.3 官方方案定位（越影 S610 AOV）

上海海思官方公众号（经电子发烧友转载，2025-06-16 发布）对越影 S610 AOV 方案的技术要点表述：

- **系统级低功耗设计** + **AI ISP**（黑光全彩，4M 分辨率，0.5T 小算力提升 6dB 信噪比）
- **PIPE 极简全在线低功耗设计** + **亚帧级卷绕压缩技术**，支持**多目编码**
- **定向 AI 侦测算子**：人形检测精度 99.88%，最远 40 米、稳定 30 米
- **智能编码 2.0**：较上一代省 28% 码率；蜂窝信道自适应编码
- **天际通**：内置 4G Cat1 eSIM，160+ 国家开机即联网
- **DDR STR**：列为解决「长续航待机」的关键技术之一
- 商用落地：深圳芯睿视「臻全彩 AOV G6W」、太阳能路灯 4G 低功耗 AOV 双目枪球、XF5H 4G 低功耗四目黑光 AOV

> 注意：该官方宣传**未给出任何 mW 级功耗数值**。

---

## 2. 技术机制拆解

### 2.1 软件架构（CV610 代的重大变化）

- **MPP 媒体处理搬到用户态独立进程 `sdk_server`**：sample 通过 IPC（msg queue）与 `sdk_server` 通信，而非传统内核 ko 直调。这使整个媒体栈可随进程/系统一起被挂起。
  来源：官方《quick_start_demo 快速入门》「当前MPP媒体模块处于用户态，通过一个独立进程提供相关接口的调用服务……位于 samples/mpp/sdk_server」。
- **内核 ko 模块**（`ot_` 前缀，取代老 SDK 的 `hi_`）：`ot_osal / ot_mmz / ot_base / ot_vb / ot_vca / ot_sys / ot_rgn / ot_vpp / ot_vgs / ot_vpss / ot_vi / ot_isp / ot_chnl / ot_rc / ot_venc / ot_h264e / ot_h265e / ot_svac3e / ot_jpege / ot_svp_npu / ot_ive / ot_aiisp / ot_pm / 音频族 / 安全族`。
  - `ot_pm.ko`：电压/温度管理（SVB 动态调压、温度补偿、`pm_get/set_quick_start_flag`），license=Proprietary，kernel 5.10.221，工具链 GCC 10.3.0 musl-1.2.3（CS71.2.10.5.B002, 2025-03-05）。
  - `ot_sys.ko`：承载 syskol ioctl（`sys_ioctl_syskol_sleep/wakeup/get/set_syskol_param`），依赖 `osal_pm_media_suspend/resume`、`syskol_sleep_suspend/resume`。
  来源：对 Gitee `shumjj/3516cv610_aov` 仓库 ko 二进制的 `readelf/strings/modinfo` 静态分析（2026-09-10）。

### 2.2 电源域与休眠模式（官方头文件权威定义）

`soc/include/ot_common_syskol.h`（Apache-2.0，Copyright HiSilicon (Shanghai) / Shenshu Tech）：

```c
typedef enum {
    OT_SYSKOL_CAPTURE_MODE_NORMAL = 0, /* capture frame continuously */
    OT_SYSKOL_CAPTURE_MODE_SINGLE,     /* capture one frame after syskol_suspend or syskol_sleep done */
    OT_SYSKOL_CAPTURE_MODE_BUTT
} ot_syskol_capture_mode;

typedef enum {
    OT_SYSKOL_SLEEP_MODE_NONE,    /* next sleep with nothing */
    OT_SYSKOL_SLEEP_MODE_LIGHT,   /* next sleep light, only cpu run with slow freq */
    OT_SYSKOL_SLEEP_MODE_DEEP,    /* next sleep deep, all ip need stop working, sensor run with standby */
    OT_SYSKOL_SLEEP_MODE_USER,    /* next sleep with user config, some ip could work commpared with deep mode */
    OT_SYSKOL_SLEEP_MODE_BUTT
} ot_syskol_sleep_mode;

typedef union {
    struct { td_u32 audio_cken : 1; } bits;   /* 深睡时保留音频时钟 => AOA 音频唤醒基础 */
    td_u32 cken_mask;
} ot_syskol_sleep_user_param;

typedef struct {
    ot_syskol_capture_mode capture_mode;
    ot_syskol_sleep_mode   sleep_mode;
    ot_syskol_sleep_user_param user_param;
} ot_syskol_param;
```

要点：
- **CAPTURE_MODE_SINGLE** 是 AOV「1 秒 1 帧」的硬件语义：每次 sleep 结束只采一帧。
- **LIGHT**：仅 CPU 降频运行（网络/RTSP 可保持，见 2.6）。
- **DEEP**：所有 IP 停止、sensor standby、DDR STR；禁止访问 USB/网络/SDIO，SD 卡不可插拔。
- **USER**：在 DEEP 基础上用 `cken_mask` 选择性保留 IP；官方 sample 中唯一用到的位是 `audio_cken=1`（休眠保留音频采集 → 支持哭声/音频事件唤醒，即行业所称 AOA/AOV3.0 的硬件基础）。

### 2.3 KOL 三态状态机（官方 sample 源码）

`src/kol/state_machine/state_machine.h`：

```c
typedef enum { KOL_STATE = 0, NORMAL_CONVERGENC_STATE, NORMAL_RECORD_STATE, START_STATE_BUTT } kol_start_state;
typedef enum {
    KOL_TO_CONVERGENC_EVENT = 0, KOL_TO_RECORD_EVENT,
    CONVERGENC_TO_KOL_EVENT,     CONVERGENC_TO_RECORD_EVENT,
    RECORD_TO_KOL_EVENT,         RECORD_TO_CONVERGENC_EVENT, START_EVENT_BUTT
} kol_start_event;
```

流转（源码注释原文）：
```
上电 → NORMAL_CONVERGENC_STATE（AE/AWB 收敛）
KOL→CONVERGENC: kol_running → kol_exit → convergenc_enter → convergenc_running
CONVERGENC→KOL: convergenc_running → convergenc_exit → kol_enter → kol_running
KOL→RECORD:     kol_running → kol_exit → record_enter → record_running
RECORD→KOL:     record_running → record_exit → kol_enter → kol_running
```
- **KOL_STATE**：低功耗占空比录像（单帧采集 + 休眠）。
- **NORMAL_CONVERGENC_STATE**：亮度剧变/AE 未收敛时进入，连续采集直至收敛（`CONVERGENC_RUN_FRAME_COUNT=20` 帧上限，`CONVERGENC_TIMEOUT=5`）。
- **NORMAL_RECORD_STATE**：事件触发后全帧率录像（`RECORD_STREAM_TIME=15` 秒，每秒重置 `RECORD_RUN_FRAME_COUNT=30` 帧 ≈30fps），同时 `media_trigger_jpeg()` 抓图、开启 AI 跟踪、按需开白光。

### 2.4 一个 AOV 周期的完整时序（`kol_running` + 时间戳埋点）

`dfx/kol_timestamp.h` 定义了单帧周期的全部埋点：
```
after_suspend → sensor_restart → frame_pts → run_end_pts → before_osd → after_osd
→ before_aidetect → after_aidetect → before_wait_venc → after_wait_venc → before_suspend
```
`kol_running()` 单周期流程：
1. `sem_post(g_sem_sensor_standby)` / `sem_post(g_sem_kol_run)`
2. `kol_frame_proc(i)`（取帧 + OSD + AI 检测 + 送编码）
3. `restart_sensor(route_num)`（唤醒 sensor 出 1 帧）
4. 等待 `g_sem_kol_done`（编码完成）
5. 判定：AE 未收敛 → 转 CONVERGENC；`g_is_detected_target || kol_get_wakeup_record()` → 转 RECORD
6. `communicate_with_mcu()`
7. `wait_sensor_standby_done()` → `kol_suspend(g_kol_sleep_time)` → 清信号量 → 记录 `after_suspend`

`kol_suspend()`：
```c
if (g_kol_sleep_mode == OT_SYSKOL_SLEEP_MODE_DEEP) wakeup_timer_start(time);  // 深睡先武装 always-on 定时器
ss_mpi_syskol_sleep(time);                                                     // 阻塞休眠 time ms
if (g_kol_sleep_mode == OT_SYSKOL_SLEEP_MODE_DEEP) wakeup_timer_stop();
```
**帧率 = 1000 / sleep_time**（默认 1000ms → 1fps；范围 [100,5000]ms 或 -1）。

### 2.5 Sensor 低功耗与快启（Fast AE / Quick Start）

**Sensor 驱动必须实现的回调**（`ot_sns_ctrl.h` / `ot_common_sns.h`）：
- `pfn_standby(vi_pipe)` / `pfn_restart(vi_pipe)`
- `pfn_cmos_get_standby_cfg(vi_pipe, sns_regs_info)` / `pfn_cmos_get_restart_cfg(...)`：standby/restart 只写必要寄存器子集（而非完整 init 序列），是「快」的关键
- `pfn_set_fast_ae(vi_pipe, fast_ae_attr)`、`pfn_cmos_ae_quick_start_status_set(...)`

**Sensor 选型硬约束**（淇诺论坛转《KOL模式使用指南》，2026-01-14）：
- 支持 Standby 模式，休眠后寄存器值保持不变
- **帧消隐区（vertical blanking）≥ 33ms**（保证 1fps 占空比下 sensor 有足够时间 standby）
- 休眠期间不依赖主控时钟
- 唤醒后可立即曝光并传输数据

**AE/ISP 快启参数**（`ot_common_ae.h` / `ot_common_isp.h`）：
```c
typedef struct {
    td_bool quick_start_enable;
    td_u8   black_frame_num;    /* 唤醒后丢弃/压暗的前 N 帧 */
    td_bool ir_mode_en;
    td_u32  init_exposure_ir;
    td_u32  iso_thr_ir;         /* 对应 sample_kol -d light on threshold / kol_set_iso_threshold */
    td_u16  ir_cut_delay_time;
} ot_isp_quick_start_param;
/* ot_isp_ctrl_param: */
ot_isp_run_wakeup_select isp_run_wakeup_select; /* FE_START 或 BE_END 驱动 ISP 线程 */
td_bool quick_start_en;                          /* ISP Quick Start */
ot_isp_alg_run_select alg_run_select;           /* NORM 或 FE_ONLY（降功耗） */
/* ot_isp_vd_type 含 OT_ISP_VD_STANDBY_FE_END（standby 专用帧同步事件） */
```

**曝光参数缓存（"有光敏快启"）**：sample 在休眠前按 4 种光照模式（`KOL_COLOR_MODE_ONLY / KOL_IR_MODE_ONLY / KOL_COLOR_MODE_WITH_LIGHT / KOL_IR_MODE_WITH_LIGHT`）缓存 `exp_time / a_gain / d_gain / isp_d_gain`（`kol_exp_info.last_exp[]`），唤醒后直接写回 → 单帧即正确曝光。官方《fast_ae 快速入门》给出收敛指标：**有光敏快启 3 帧内收敛；无光敏（初始曝光偏差 500 倍）10 帧内收敛**；`EXPOSURE_DELAY_NUM=3`。

**补光时序细节**：红外补光在 `pfn_restart` **之前**打开（`restart_sensor_by_route` 中先 `kol_ir_light_controll(TD_TRUE)`），保证唤醒首帧即有照明；standby 时关闭。白光 PWM1（period 1ms, duty 33%）、红外 PWM3（period 1ms, duty 28%）；`KOL_CLOSE_LIGHT_ISO=150`（ISO 低于 150 关补光）。

### 2.6 唤醒源

sample/官方 release note 确认的唤醒源：
| 唤醒源 | 实现 | 说明 |
|---|---|---|
| **定时器（always-on BSP timer）** | sysfs `/sys/devices/platform/soc/soc:amba/11000000.bsp_timer/{power/wakeup, time_ms, timer_start}` | DEEP 模式主唤醒源；`wakeup_timer_start(ms)` |
| **GPIO / 按键 / PIR** | `/dev/input/event0` poll，`EV_KEY && value==1` → `ss_mpi_syskol_wakeup()` + `kol_set_wakeup_record(TRUE)` → 直接进 RECORD | 打印 `=========gpio wakeup===========` |
| **RTC** | 芯片集成独立供电 RTC；release note 列为 KOL 唤醒源 | |
| **UART** | release note 列为 KOL 唤醒源 | |
| **4G / 网络（经 MCU）** | MCU 通知 `info.wakeup == WAKEUP_4G_MODE` → 转 RECORD | 远程预览/平台唤醒 |
| **MCU 模式切换** | `MCU_SWITCH_STATE_ENTER_SINGLE/EXIT_SINGLE` | KOLB 板型按键切换 |

**LIGHT vs DEEP 的网络行为差异**（`kol_main.c` / `kol_proc_thread`）：
- LIGHT：`main()` 中直接 `kol_rtsp_server_start()` → 休眠期间 RTSP 预览在线（对应行业「AOV 低帧率模式保持 Wi-Fi/4G 保活」）。
- DEEP：默认无网络；**仅当 AI 检测到目标时**才 `kol_rtsp_server_start()`（按需联网），录像结束 `kol_rtsp_server_stop()`。

**MCU 协同协议**（`peripheral.c`）：UART2 `/dev/ttyAMA2` @115200 8N1；6 字节帧 `{0xEB,0x90,CMD,0,0,CS}`，CMD：`0xCC` 查询通知、`0xEE` 设模式、`0xDD` 读功耗测试数据（MCU 侧 AD 采样回传 voltage/current/power）；`peripheral_set_sleep_time(ms)` 通知 MCU 休眠时长。

### 2.7 录像占空比与存储策略（回答「1秒1帧？低分辨率？灰度？」）

- **帧率占空比**：KOL 态 1 帧/sleep_time（默认 1fps）；RECORD 态 ~30fps × 15s。
- **分辨率**：主码流全分辨率（sample 默认 sensor 2688×1520 / 4MP）；**AI 检测子码流固定 768×448**（`CHN1_WIDTH/HEIGHT`），VPSS chn1 + VENC chn1，`frame_rate_100x=1500`（15fps 上限供检测）。即 AOV 期间用低分辨率子流跑 AI，主流仅存关键帧。
- **灰度**：VENC 通道参数提供 `color_to_grey_en`（`ot_venc_chn_param`），但 **sample_kol 默认未启用灰度**；AOV 夜视走「红外黑白 / 白光全彩」四模式切换而非编码层灰度。
- **存储**：码流先入 1MB 内存缓冲（`g_srteam_buffer_size=1MB`），**满 1MB 或切新文件才 fwrite 落盘**（`/sd/`，vfat，`/dev/mmcblk0p1`），单文件上限 64MB → 减少 SD 卡 IO 唤醒；JPEG 单独即时落盘。收敛期码流不保存（`SAVE_CONVERGENC_BUFFER=0`）。
- **编码**：H.265/H.264/SVAC3.0；VENC 模块级 `low_power_mode`、`one_stream_buf`、`mini_buf_mode` 可选；智能编码 SVC V2（`ss_mpi_venc_send_svc_region` 把 AI 框送编码器做 ROI 码率分配，`qp_delta[15]=3`）。

### 2.8 多目 / MIPI-Switch / 卷绕压缩

- `MAX_ROUTE_CNT=4`（最多 4 目）。KOL 态双目/多目用 **MIPI Switch 分组轮询**：GPIO7_0（num 56）选组 → `ss_mpi_vi_distribute_one_frame(grp, pipe)` 单帧分发 → 逐组各拍 1 帧（官方「多目多帧」）。
- 多目帧同步：`restart_sensor_normal()` 按各路曝光时间 + 半帧长排序后依次 `usleep` 重启，并 `kol_sns_slave_ctrl` 使能 sensor 主从同步（寄存器 0x3222：0x01 slave / 0x00 master）。
- **卷绕压缩**：`ss_mpi_vi_set_pipe_buf_wrap_attr()` / `ot_vi_pipe_buf_wrap_attr`（VI buffer wrap），即官方宣传的「亚帧级卷绕压缩」，降低 DDR 带宽与首帧延迟；DDR 受限型号（10B/CV608）官方 readme 建议「减少 VB 或 enable wrap」。

### 2.9 DDR STR 与启动裁剪（快启的另一半）

- DEEP 休眠 = **Suspend-To-RAM**：`ss_mpi_syskol_suspend()`（当前版本 sample 标注「下电方案暂不支持，suspend 接口暂不可用」，实际走 sleep+STR）；热启动「从 STR 挂起状态恢复，直接回到挂起前运行位置，无需重新初始化」。
- **冷启动快启**：DDR 训练参数在 U-Boot 环境变量与 GSL（bootloader）宏中保存一致，warm boot 跳过 DDR 重新训练；官方《Hi35xxVxxx 快速启动优化指南》+ `sample_quick_start` 度量首帧时延（实测 dmesg：kernel 2.52s 进 sample，VI 首帧 gap≈33ms，ISP init≈13.7ms）。
- 内存布局（20S）：DDR 128MB = 32MB OS + 96MB MMZ（`mmz_start=0x42000000`）。

### 2.10 AI 检测与功耗的耦合

- `ss_mpi_aidetect_*`：最多 8 通道；12 类（FACE/HUMAN/VEHICLE/PET/GARBAGE/BAG/WALLET/PHONE/HEAD_SHOULDER/BICYCLE/MOTORCYCLE/PACKAGE）；每类可配 track / motion-detect 阈值；模型优先级抢占调度（`priority 0-7`、`priority_up_step_timeout`）→ AOV 低帧率检测可让位于正常态检测。
- 模型：`./model/aidetect/det_hvf_hor_ll_lite.bin`（hvf=人/车/人脸，lite=低算力版）。
- **SmartAE 闭环**：`ss_mpi_smartae_update_roi_info()` 把 AI 检测到的人脸/人形框（`OT_SMARTAE_OBJ_FACE/PEOPLE`，最多 5 框×2 类）反馈给 AE 做区域测光 → 唤醒单帧即正确曝光（`smart_ae_set_smart_exposure_attr`）。
- KOL 态关闭跟踪（`algorithm_set_track_attr(route_num, TD_FALSE)`），RECORD 态开启，省 NPU 功耗。

---

## 3. 功耗指标数据表

### 3.1 官方芯片级典型功耗（一手：官方产品简介 PDF）

| 芯片 | 文档版本/日期 | 典型功耗 | 内核电压 | 备注 |
|---|---|---|---|---|
| Hi3516CV610 | v04 / 2025-03-28 | **1043 mW** | 0.9V | 关键特性含「AOV 低功耗方案」；IO 1.8/3.3V；DDR3/3L 1.5/1.35V；-20~70℃；QFN 9×9 0.35mm |
| Hi3516CV608 | v02 / 2024-09-06 | **668 mW** | 0.9V | 关键特性**不含** AOV；无 AI ISP、无 WDR；内置 512Mb DDR2 1333Mbps；DDR2 1.5/1.8V |

> 官网网页版（hisilicon.com CV610 产品页）功耗栏为「典型功耗：TBD」，**数值仅在 PDF 版给出**；CV608/CV100 在官网无独立产品页（404）。

### 3.2 开发板实测 KOL 功耗（一手：鸿鸥派 PICO(HI3516CV610) 产品规格书 V1.5，2025-08-13，§2.3「KOL 模式功耗」）

| 运行程序 | 电流 @5V | 折算功率 @5V | 说明 |
|---|---|---|---|
| `sample_kol` 浅睡眠 | **122 mA**（空载） | **≈610 mW** | 识别到目标/环境曝光高时 ~240mA ≈1200mW |
| `sample_kol` 深睡眠 | **70 mA** | **≈350 mW** | 识别到目标/环境曝光高时 170–240mA ≈850–1200mW |
| `sample_venc`（全速编码） | 330 mA | ≈1650 mW | 对照 |
| `sample_svp`（NPU 满载） | 390 mA | ≈1950 mW | 对照 |
| 整板供电上限 | Type-C 5V/2A | ≤3 W | 7×24h 70℃ 高温测试 |

> 规格书版本历史 V1.4（2025-07-21）明确写「更新 kol 功耗描述」，说明该数据为板级实测。
> **解读**：板级深睡 350mW 包含 DCDC/LDO 转换损耗、以太网 PHY、sensor（standby 仍供电）、电平转换、LED、MCU 等；与「80mW」差异主要来自口径（整板 vs SoC）与外设裁剪。**公开渠道没有 SoC 级 AOV 功耗的官方数值。**

### 3.3 市场宣称值（二手/营销，可靠性低）

| 数值 | 出处 | 可靠性 |
|---|---|---|
| **AOV 运行功耗低至 80mW（1秒1帧）**，7×24 全天候录像 | CSDN 开发板/源码商品文（yichu5074，2025-09-09）；多处转载 | **低**：方案商营销口径，无测试条件/无口径说明；与板级实测 350mW 不符 |
| 触发后切 15fps 正常模式；AI 检测准确率 99%、距离 30m | 同上 | 低；sample 实际为 RECORD 态 ~30fps×15s |
| 人形检测精度 99.88%，最远 40m/稳定 30m | 海思官方公众号（越影 S610） | 中（官方宣传，无测试方法） |

### 3.4 竞品/行业对照（用于标定 80mW 的合理性）

| 平台 | AOV 待机/运行功耗 | 出处 |
|---|---|---|
| 瑞芯微 RV1126B | 典型 2.8W；AOV 待机 **1mW**；0.1s 极速启动 | CSDN 技术合辑（2026-07-22） |
| RV1126B 评估板 + SC850SL 实测 AOV 1fps | 整机 **≈122mW** | 同上（创龙评估板实测） |
| 行业「AOV3.0」 | 运行态 <40mW；音频事件唤醒待机 ~1mW | 搜狐行业稿（2025-08-01） |
| 传统 AOV（1.0/2.0） | 休眠 >100mW；唤醒延迟 2–3s；PIR ≤10m | 同上 |
| 3AR（全会录） | 2 节 18650 纯电续航 >3 天 | 同上 |

> 对照可见：RV1126B 板级 AOV 1fps 实测 122mW，与海思板级深睡 350mW 同量级；「80mW」若为 SoC 级或深度优化产品级则 plausible，但**公开数据无法证实**。

### 3.5 电池续航案例（公开）

- 户外场景：5W 太阳能板 + 10000mAh 电池，日均 6 次事件，实测续航 ~90 天（CSDN 合辑，行业口径，非海思专属）。
- 行业普遍做法：1 万/2 万 mAh 电池 + 太阳能板，「一次最少支持 7 天待机」（搜狐行业稿）。
- 海思官方/开发板规格书**未给出**电池续航曲线。→ 缺口。

---

## 4. 公开 SDK / API 细节

### 4.1 权威 API（官方公开头文件，Apache-2.0）

`soc/include/ss_mpi_syskol.h`（Copyright 2026 HiSilicon (Shanghai) Technologies Co., Ltd.，Apache-2.0）：
```c
td_s32 ss_mpi_syskol_set_param(const ot_syskol_param *param);
td_s32 ss_mpi_syskol_get_param(ot_syskol_param *param);
td_s32 ss_mpi_syskol_sleep(td_s32 milli_sec);   /* 阻塞休眠 ms */
td_s32 ss_mpi_syskol_wakeup(td_void);           /* 外部唤醒（GPIO/4G） */
td_s32 ss_mpi_syskol_suspend(td_void);          /* 下电/STR（当前版本 sample 标注暂不可用） */
```
（商业 SDK 中同名接口另有 `ot_mpi_syskol_*` 前缀变体，见 sample_kol 符号表。）

配套关键 API（同仓库头文件）：
- VI：`ss_mpi_vi_distribute_one_frame(grp, pipe)`、`ss_mpi_vi_set_pipe_buf_wrap_attr()`
- ISP/AE：`ss_mpi_isp_set_ae_route_sf_attr_ex()`（AOV 低帧率 AE route）、`ss_mpi_isp_query_exposure_info()`、`ot_isp_quick_start_param`、`pfn_set_fast_ae`
- VENC：`ot_venc_h264/h265/svac3_mod_param.low_power_mode`、`ot_venc_chn_param.color_to_grey_en / poll_wake_up_frame_cnt / frame_rate`、`ss_mpi_venc_request_idr`、`ss_mpi_venc_send_svc_region`
- AIDETECT：`ss_mpi_aidetect_create_chn/destroy_chn/process/query_status/set_chn_attr/get_chn_param`
- SmartAE：`ss_mpi_smartae_update_roi_info()`
- 内核 ioctl 入口：`sys_ioctl_syskol_{sleep,wakeup,get_param,set_param}`（ot_sys.ko）

### 4.2 sample_kol CLI（与二进制 `-h` 完全一致）

```
usage : sample_kol [-n N] [-k kol_mode] [-s sleep_mode] [-t sleep_time] [-r] [-c] [-p]
    -h: show help info.
    -n: set route num. [1, 2, 4]. default: 1
    -k: set kol mode. 0: auto mode, 1: record mode, 2: kol mode. default: 0
    -s: set sleep mode. 0: sleep none, 1: light sleep, 2: deep sleep, 3: user sleep. default: 1
    -t: set sleep time(ms). [100, 5000] || [-1]. default: 1000
    -r: run ai detect. 0:none, 1:route_0, 2:route_1, 3:route_0+route_1, 4:route_2, 8:route_3, 15:all. default: 0
    -i: scene auto ini. eg: ./param/sensor_hy006_3814_0011.
    -d: light on threshold. default: 1000
    -c: communicate with mcu.
    -p: print statistics
eg: sample_kol -n 1 -k 0 -s 0 -t 900 -r 1 -i ./param/sensor_hy006_3814_0011 -c -p
```
（淇诺论坛版本文档中 `-s` 多列「4=挂起」，为更新版本差异。）

### 4.3 KOL 参考实现源码结构（公开可得，24 文件）

```
src/kol/
├── kol_main.c                 # 入口、CLI、LIGHT 模式起 RTSP
├── state_machine/             # 通用 3 态状态机框架
├── state_machine_action.{c,h} # 核心：kol/convergenc/record 三态 enter/running/exit、sensor standby/restart、补光、IR-CUT、曝光缓存
├── media/{media.c,media_venc.c}# 通路配置(4 route/768x448 子流/wrap)、1MB 攒批落盘、JPEG
├── algorithm/                 # aidetect + SmartAE + SVC 智能编码
├── peripheral/                # MCU UART 协议、BSP timer 唤醒、GPIO 唤醒、PWM/GPIO 补光
├── region/ osd/ scene/ dfx/   # OSD 时间/状态叠加、场景参数、时间戳统计
└── Makefile                   # AIDETECT_ENABLE / LIGHT_ENABLE / IR_CUT_ENABLE 开关
```
版权头：`Copyright (c), 2001-2025, Shenshu Tech. Co., Ltd.`（海思 SDK 新主体署名；GitCode 公开头文件则为 `HiSilicon (Shanghai) Technologies Co., Ltd.` + Apache-2.0）。

### 4.4 构建/烧录流程（淇诺论坛转《KOL模式使用指南》）

- 不下电方案（推荐）：`sh smp/a7_linux/source/bsp/kol/build.sh sol_images`（DDR3；DDR2 改 CHIP=Hi3516CV608）
- 下电方案：**当前版本不支持**（`build.sh kol_images` 禁用）
- `make -j AIDETECT_ENABLE=y`；模型 `out/model/aidetect/det_hvf_hor.bin`
- rootfs：`rootfs_hi3516cv610_64k_kol.jffs2`（mkfs.jffs2 -e 0x10000），改 `nor_burn_table.xml`
- 运行：`./load3516cv610_00s_debug -i -sensor0 os04d10` → `./sample_kol -n 1 -k 0 -s 1 -t 1000 -r 1 -p`
- 定制点：`kol/media/media.c:g_route_num`、`media_venc.c:SD_CARD_PATH/g_srteam_buffer_size`、`peripheral.c:peripheral_mode_flag1/peripheral_set_uart_mode`、`algorithm.c:smart_ae_set_smart_exposure_attr/algorithm_svc_set_rect`

### 4.5 SDK 版本线索

- 商业 SDK：`Hi3516CV610_SDK_V1.0.2.0`（Gitee README）/ `V1.0.2.1`（易百纳 MPP Sample 仓库）；芯片版本 `R001C01SPC020/021`。
- KOL 特性引入版本：迅为公告称基于 **R001C01SPC020** 新增「KOL 特性、待机到 RAM、GPIO/定时器/RTC/UART 唤醒源、CPU 热插拔、《电池类产品低功耗设计指导书》《KOL模式使用指南》」。
- 公开社区 SDK（GitCode HiSpark/Hi3516CV610）**不含 kol sample 目录**（samples/mpp 仅 20 个目录，无 kol）→ KOL sample 仅随商业 SDK 与第三方镜像仓库流出。

### 4.6 型号配置差异（官方 PDF v04，2025-03-28，已逐格核对渲染图）

| 分类 | 10B | 20S | 20G | 00S | 00G |
|---|---|---|---|---|---|
| 最大性能 | 5M@30 | H.265/H.264 4K@25; SVAC3 6M@30 | 4K@25/6M@30 | H.265/H.264 4K@25; SVAC3 6M@30 | 4K@25/6M@30 |
| 最大分辨率 | 2880×1620 | 3840×2160（20S–00G 共用） | | | |
| 算力 | 0.5Tops | 1Tops（共用） | | | |
| 编码协议 | SVAC3.0/H.265/H.264（SVAC 不支持 SmartCRR） | SVAC3.0/H.265/H.264（共用） | | | |
| 最大编码能力 | 5M+D1 | 6M+720P（共用） | | | |
| WDR | 支持（全型号） | | | | |
| DDR | 内置 DDR2 1333Mbps / 512Mb | 内置 DDR3/3L 2133Mbps / 1Gb（20S,20G） | | 外置 DDR3/3L 2133Mbps / 最大 4Gb（00S,00G） | |
| eMMC | eMMC4.5 4线（10B–20G） | | | eMMC5.0 8线（00S,00G） | |
| 封装 | QFN9×9 0.35mm（10B–20G） | | | TFBGA12×13.3 0.65mm（00S,00G） | |
| 安全规格 | - | - | 支持 GB35114 | - | 支持 GB35114 |

> 命名解读（结合 load 脚本 mmz 实测）：首位=DDR 配置（1=内置DDR2 512Mb，2=内置DDR3 1Gb，0=外置DDR3 最大4Gb）；次位 B/S/G 中 **G=支持 GB35114**。load 脚本另含 00B/20B（20B 不加载 `ot_svac3e.ko`），官方简介未列。
> **纠错**：知乎某文称「00S=内置512Mb DDR2」与官方 PDF 矛盾（00S=外置 DDR3 最大 4Gb），不可采信。

---

## 5. 与老平台低功耗能力差异

| 维度 | Hi3516CV610/608（KOL/AOV） | Hi3516CV100 | Hi3518EV200/EV300 | Hi3516DV300/CV500 | 老 Hi3516（Full-HD） |
|---|---|---|---|---|---|
| 原生 AOV/KOL | **有**（syskol API + sample + 文档） | 无 | 无 | 无 | 无 |
| 休眠粒度 | 4 级（none/light/deep/user）+ 时钟门控 + IP 级 cken_mask | 时钟门控/模块级 | 依赖外部 MCU+PMU | STR/快启 | NORMAL + 时钟门控 + 模块级 + **DDR self-refresh** |
| DDR 低功耗 | STR（DEEP）+ wrap 降带宽 | 常规 | 常规 | STR | **自刷新模式**（datasheet 级） |
| 录像连续性 | 1fps 连续 + 事件 30fps×15s，无断档 | 事件触发 | 事件触发（门铃/猫眼） | 事件触发 | 事件触发 |
| 唤醒 | BSP timer/GPIO/RTC/UART/MCU-4G | 外部中断 | 外部 MCU 中断 | RTC/GPIO | 外部中断 |
| 快启 | 3 帧收敛（Fast AE）+ DDR 参数保持 + STR 热恢复 | 冷启动 | 冷启动（秒级） | 快启镜像 | 冷启动 |
| 典型电池架构 | SoC 自身 STR + 可选 MCU | — | **STM8L 超低功耗 MCU + ACT8946 PMU 保活，SoC 全下电** | — | — |

结论：老平台只能靠「STR/完全下电 + 快启 + 外部 MCU 保活」**模拟**低功耗待机，属 PIR/事件触发型，睡眠期无录像、有 0.5–3s 唤醒断档；CV610 代 KOL 是**芯片级占空比连续录像**，二者机制不同代。

---

## 6. 信息缺口（公开渠道不可得 / 不可核实）

1. **SoC 级 AOV 功耗数值**：官方仅给全速典型功耗（CV610 1043mW / CV608 668mW）；AOV/KOL 各休眠态的 SoC 级 mW 值**公开渠道不可得**。「80mW@1fps」为方案商营销口径，**不可核实**；板级实测深睡 350mW（整板）与之口径不同。
2. **《KOL模式使用指南》《电池类产品低功耗设计指导书》原文**：仅随商业 SDK 发放；公开仅有论坛转述与 sample 源码，**完整原文不可得**。
3. **`ss_mpi_syskol_suspend`（下电方案）可用性**：sample/论坛标注「当前版本不支持」；是否在新版本开放**不可得**。
4. **DDR self-refresh 在 KOL DEEP 态的确切寄存器/流程**：官方头文件与 sample 未暴露 DDR 控制器级细节；仅有「DDR STR」宣传语与老 Hi3516 datasheet 的自刷新描述。
5. **电池续航官方曲线/实测**：海思官方与开发板规格书均未给续航-帧率曲线；公开续航数据均为行业/竞品口径。
6. **CV608 的 AOV 官方背书**：官方 CV608 简介**未列** AOV；其 KOL 可用性仅有 load 脚本/ko 佐证，无官方声明。
7. **Hi3516CV100 / Hi3518 系列的官方低功耗白皮书**：公开仅分销器件页与 SEO 文，**一手 datasheet 低功耗章节不可得**。
8. **`Shenshu Tech. Co., Ltd.` 与海思的法律主体关系**：SDK 版权署名变化可见，但中文主体名与重组细节**未核实**，本文仅按字面记录。
9. **越影 S610 与 Hi3516CV610 的精确对应/差异**：宣传与芯片型号强相关，但是否存在独立 SKU**不可得**。

---

## 7. 参考资料列表（访问日期均 2026-09-10）

**一手 / 官方**
1. 海思官网 Hi3516CV610 产品页（智能安防）：https://www.hisilicon.com/cn/products/smart-vision/public-security/IPC/Hi3516CV610 （功耗栏 TBD，未提 AOV）
2. 《Hi3516CV610 超高清智慧视觉 SoC 产品简介》PDF v04 (2025-03-28)，版权所有©海思技术有限公司；镜像 https://gitee.com/e-hi3516cv610/Docs/raw/master/产品规格书/Hi3516CV610%20超高清智慧视觉%20SoC%20产品简介.pdf （典型功耗 1043mW；关键特性含 AOV；型号差异表）
3. 《Hi3516CV608 超高清智慧视觉 SoC 产品简介》PDF v02 (2024-09-06)；同目录 cv608 版（典型功耗 668mW；无 AOV/AI ISP/WDR）
4. GitCode 官方文档仓库 HiSpark/Hi3516CV610：https://gitcode.com/HiSpark/Hi3516CV610 （docs/ 全套指南；soc/include/ot_common_syskol.h、ss_mpi_syskol.h、ot_common_aidetect.h、ot_common_ae.h、ot_common_isp.h、ot_sns_ctrl.h、ot_common_venc.h 等 Apache-2.0 头文件；samples/mpp/quick_start_demo、fast_ae；**无 kol sample**）
5. 官方《quick_start_demo 快速入门》《fast_ae 快速入门》（同上仓库 docs/03参考案例）
6. Gitee 易百纳 e-hi3516cv610 组织：https://gitee.com/e-hi3516cv610 ；MPP Sample 仓库（含 **src/kol 全源码**、include/hisilicon 头文件）：https://gitee.com/e-hi3516cv610/Hi3516CV610_SDK_V1.0.2.1_MPP_Sample
7. 《HongOUPI PICO(HI3516CV610) 产品规格书》V1.5 (2025-08-13) §2.3 KOL 模式功耗：https://gitee.com/e-hi3516cv610/Docs/raw/master/产品规格书/HongOUPI_PICO(HI3516CV610)规格书_V1.5.pdf
8. 海思官方公众号文章（经电子发烧友转载）《芯闻速递 | 越影S610：无电无网无光？这个摄像头方案全搞定！》(2025-06-16)：https://www.elecfans.com/d/6742412.html

**SDK/源码流出与二进制分析（本文一手分析对象）**
9. Gitee shumjj/3516cv610_aov（官方 AOV demo rootfs + ko + sample_kol 二进制 + load 脚本）：https://gitee.com/shumjj/3516cv610_aov （本文对其 ko/二进制做 strings/readelf/modinfo 静态分析）
10. 本文克隆的 KOL 源码：e-hi3516cv610/Hi3516CV610_SDK_V1.0.2.1_MPP_Sample（src/kol，24 文件）

**二手 / 行业 / 论坛（可靠性分级标注于正文）**
11. 淇诺科技论坛《Hi3516CV610 的 KOL 模式》(2026-01-14，转《KOL模式使用指南》)：http://bbs.qinuo.com.cn/forum.php?mod=viewthread&tid=192 （中：与源码/二进制互证）
12. 迅为《iTOP-Hi3516CV610 开发板 SDK 升级（R001C01SPC020，KOL/待机到RAM/多唤醒源）》(2026-03-19)：https://blog.csdn.net/BeiJingXunWei/article/details/159243704 （中）
13. CSDN《海思Hi3516CV610/Hi3516CV608 AOV源码…80mW》(2025-09-09)：https://blog.csdn.net/yichu5074/article/details/151315879 （低：营销）
14. CSDN《低功耗 IPC 监控技术：AOV 全时录像》(2026-07-22，含 RV1126B 实测 122mW)：https://blog.csdn.net/u013669912/article/details/163114036 （中：竞品实测）
15. 搜狐《AOV 3.0技术加持！低功耗IPC芯片市场风云再起》(2025-08-01)：https://www.sohu.com/a/919901661_121124364 （中：行业口径）
16. 视觉物联/合肥优视《基于新一代海思芯片的低功耗AOV网络摄像机IPC方案》(2024-12-08)：https://www.besovideo.com/detail?t=2&i=1814 （中：市场时间线）
17. 52solution《XB120 基于海思Hi3518EV200低功耗WiFi可视门铃方案解析》：https://www.52solution.com/facs/8572 （中：老平台电池架构 BOM）
18. EmbedIc Hi3516CV100 器件页（ARM926/1080p30）：https://www.embedic.com/product/hi3516cv100 （中：基础规格）
19. CSDN 文库《Hi3516芯片电源管理与低功耗模式详解》（老 Hi3516 datasheet 摘要，含 DDR self-refresh）：https://wenku.csdn.net/doc/10tw9m7dcd （低-中）
20. 知乎《海思Hi3516CV610-00S作用有哪些》(2026-05-07)：https://zhuanlan.zhihu.com/p/2035758492875760271 （低：含与官方 PDF 矛盾的错误型号描述，仅作反例）

---
*报告完。所有「官方/一手」结论均给出 PDF/仓库/头文件出处；所有营销数值均标注可靠性等级；不可得项见 §6。*
