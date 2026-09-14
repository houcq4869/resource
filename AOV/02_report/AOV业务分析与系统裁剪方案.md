# AOV 业务分析与系统裁剪方案

| 项目 | 内容 |
|---|---|
| 文档名称 | AOV 业务分析与系统裁剪方案（AOV 专项·阶段 3） |
| 文档版本 | V1.0 |
| 日期 | 2026-09-10 |
| 分析基线 | `/home/houcq/workspace/oh_release`，产品 `ipcamera_hispark_taurus`（hi3516dv300，small/liteos_a） |
| 上游输入 | 阶段 1《IPC AOV 业界方案调研报告》§2/§3（海思 KOL 三态机、分态服务设计）；阶段 2《OH L1 低功耗现状与差距分析》 |
| 方法论 | 借鉴 RP2 裁剪专项：bundle.json（adapted_system_type/资源预算）→ 依赖反查（BUILD.gn）→ 分级处置（常驻/延迟/按需/裁剪）→ 预算核算 |
| 文档目的 | 定义 AOV 三工作期业务模型，给出组件级/MPP 模块级/服务级三层裁剪方案与 ROM/RAM 预算，支撑小型化目标并为阶段 4 方案设计提供输入 |

---

## 1. 结论速览（TL;DR）

1. **业务模型**：AOV 业务拆为三个工作期——**值守期**（1fps 单帧循环，功耗敏感）、**事件期**（AI 命中切全速录像）、**维护期**（联网预览/OTA/配置）。裁剪原则：**值守期最小集常驻，事件期能力延迟加载，维护期能力按需拉起，无屏形态 UI 全家桶直接裁剪**。
2. **组件级**：taurus 现有 50 组件，分级处置后建议**裁剪 17 个、延迟/按需 9 个、保留 24 个**；最大收益来自无屏化（UI/图形/示例应用 7 项）与去软总线族（dsoftbus+device_auth+device_security_level+dmsfwk_lite+dslm 5 项，RAM 声明值合计 ~49MB）。
3. **MPP 模块级**：32 个静态库中值守期最小集约 11 个；**树内存在完整 `sdk_exit.c`（含 `SDK_exit()`，模块级 exit 序列齐全）**——阶段 2"无官方 mod_exit 顺序"判断修正，**模块级 deinit/re-init 策略树内可行**（MPP 闭源约束下的最优路径），但当前无任何调用者，需接管并验证。
4. **内存布局重配**：DDR 512MB = 内核系统内存 ~127MB（`SYS_MEM_SIZE_DEFAULT 0x07f00000`）+ MMZ 静态 384MB（`sdk_init.c:32-33`）。AOV 值守期不需要大 VB 池，建议 **MMZ 降至 128~192MB + VB 池双档位动态申请**（值守小池/事件大池），释放的内存换 kernel 堆余量或缩小 DDR 有效容量以省功耗。
5. **服务启动重排**：15 个 init 服务分为快启关键路径（3 个：foundation/media_server/shell[量产可裁]）与延迟组；无屏化后 wms_server/appspawn/apphilogcat/bundle_daemon 等 6 个可裁或延迟。
6. **风险**：bundle.json 声明预算不可靠（dsoftbus RAM 声明 40MB 等），裁剪收益必须以构建产物实测为准；组件间依赖需按 RP2 方法逐个反查后再动刀。

---

## 2. AOV 业务分析

### 2.1 三工作期业务模型（借鉴海思 KOL 三态机 + 业界 4 级功耗状态机）

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

### 2.2 值守期最小必需集（裁剪的锚点）

- **采集编码链**：MIPI-RX → VI → ISP(简化 3A，曝光参数缓存借鉴 KOL Fast AE) → VENC(H.264/H.265 二选一) → RC
- **检测链**（三选一，功耗/精度权衡）：MPP libmd 移动侦测（最省）/ IVE 帧差 / NNIE 人形（最准，768×448 子流）
- **存储链**：FATFS + MMC/SD + 攒批 fsync（1MB 攒批满或事件时落盘，海思 KOL 同款策略）
- **时间链**：RTC（alarm 唤醒源 + 时间轴基准）+ 开机 RTC 校时（阶段 2 P0-4）
- **电源链**：powermgr_lite(RunningLock/Suspend 服务) + 内核 PM + PM 计量埋点（阶段 2 P2-1）
- **时间戳叠加**：RGN 模块（OSD，录像可回溯性必需，保留）

### 2.3 业务分解 × 工作期映射总表

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

## 3. MPP 模块级裁剪方案（32 静态库分级）

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

## 4. 组件级裁剪方案（50 组件分级处置）

依据：`vendor/hisilicon/hispark_taurus/config.json`（50 组件）+ 各 bundle.json 资源声明 + 阶段 2 能力盘点。**处置前必须按 RP2 方法反查 BUILD.gn 依赖链**（下表为方案建议，非最终清单）。

### 4.1 裁剪（17 项）——无屏形态 + 去分布式 + 去测试

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

### 4.2 延迟/按需（9 项）——快启关键路径之外

| 组件 | 策略 |
|---|---|
| ai_engine（+NNIE adapter） | 首帧录像完成后拉起 ai_server（值守检测可先用 libmd 移动侦测顶替冷启窗口） |
| sys_installer_lite + huks + appverify | OTA 窗口按需初始化（huks_server 延迟启动；验签能力维护期才需要） |
| bundle_framework_lite | 纯原生服务形态可不启动 bundle_daemon（组件保留、服务延迟） |
| appspawn | 无 UI 应用则不启动（组件可保留备用） |
| sensor_lite + drivers_peripheral_sensor | 带 PIR 机型保留（唤醒源），无 PIR 机型裁 |
| audio_lite + drivers_peripheral_audio | AOA（音频唤醒）演进预留；纯视频 AOV 机型裁 |
| permission_lite | 无第三方应用则可裁（安全评审定） |

### 4.3 保留常驻（24 项）

liteos_a、bootstrap_lite、init、samgr_lite、safwk_lite、ipc、hdf_core、drivers_adapter、drivers_tools、camera_lite、media_lite、powermgr_lite、battery_lite、hilog_lite、hidumper_lite（可降级）、drivers_peripheral_wlan、drivers_peripheral_input（按键唤醒）、drivers_peripheral_sensor（PIR 机型）等 + 存储栈（内核 FATFS/MMC 非组件项）。

### 4.4 裁剪收益预估（声明值口径，**必须实测修正**）

| 维度 | 预估收益 | 主要来源 |
|---|---|---|
| RAM | **~55MB+（声明口径）** | dsoftbus 40MB + device_auth 4MB + device_security_level 2.5MB + appspawn 13MB（延迟）+ UI 族 ~0.4MB + samgr/safwk 常驻但 UI 服务不再注册 |
| ROM | **~12MB+（声明口径）** | dsoftbus 3MB + huks 5MB（延迟非裁）+ appverify 5MB（延迟）+ device_auth 4MB + UI 族 ~1.5MB + init 3.9MB 中裁剪部分 |
| 启动时间 | 关键路径服务从 15 → 3~5 个 | 见 §5 |

> ⚠️ bundle.json 声明值普遍偏大且口径混乱（如 dsoftbus RAM 40MB 为上限声明），**实际收益以裁剪前后构建产物 size + 运行时内存水位实测为准**（阶段 5 PoC 计量项）。

---

## 5. 服务启动顺序重排（init_liteos_a_3516dv300.cfg）

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

## 6. 与阶段 2 差距清单的衔接

| 阶段 2 差距 | 本方案的裁剪侧配合 |
|---|---|
| P0-2 休眠自动进入 | 裁剪后常驻任务减少 → PM 锁持有者收敛（仅 media/AOV 策略任务/存储），锁治理面变小 |
| P0-3/P0-4 时间连续性 | 值守期时间戳依赖 RTC+校时服务，裁剪不影响；RGN OSD 时间戳保留 |
| P1-3 驱动 PM listener | 裁剪 display/usb/vibrator/light 后，需挂 listener 的驱动集合缩小为 mmc/rtc/gpio/wlan/input(+sensor) |
| P1-5 SMP 从核 | 裁剪降低从核负载必要性，dv300 单核原型（关 SMP）可行性提高 |
| P2-3 battery 模拟器 | battery_lite 保留并列入接入计划 |
| 浅 AOV 路径（§6 第一步） | 本方案值守期最小集 = 浅 AOV 单帧循环的模块清单，两者一致 |

---

## 7. 风险与验证清单（动刀前置条件）

1. **依赖反查**（RP2 方法）：每个裁剪项执行树内 BUILD.gn 反向依赖检索（如 ability_lite 被 media/camera 服务依赖与否、ai_engine 对 softbus 的依赖、ipc 组件被裁项引用情况），输出《裁剪依赖核查表》后才改 config.json；
2. **SDK_exit 可用性验证**：`SDK_exit()` 无调用者历史，deinit→re-init 循环的稳定性/耗时/MMZ 重建正确性需 PoC 实测（模块级电源策略的前提）；
3. **声明值不可靠**：所有 ROM/RAM 收益以实测为准（构建产物 size + /proc 内存水位 + memdump）；
4. **vedu/cipher/vpss 归属存疑**：CV500 系 vedu 与 venc/h264e 的硬件依赖关系、vpss 在值守链路是否必需（venc 直连可行性）需结合 MPP 文档/实测确认；
5. **hispark_taurus_mini_system 参照**：树内已有极简产品配置（仅 startup+security），可作裁剪下限参照与 config.json 语法样板；
6. **aries 同步评估**：hi3518ev300 的 MPP 库集（hi3516ev200_* 35 个 .so）与 dv300 不同构，深睡验证平台（阶段 2 建议）裁剪清单需单独出一版。

---

## 8. 交付物与下一步

- 本文档 = 阶段 3 方案建议稿（业务模型 + 三层裁剪方案 + 预算）；
- **下一步（阶段 4）**：以本方案值守期最小集 + 阶段 2 P0/P1 差距清单为输入，设计《AOV 系统级低功耗方案设计文档》：功耗状态机服务、PM 锁治理规范、唤醒链路（RTC/GPIO/WiFi WoW）、时间连续性方案（内核 offset+RTC 校时+NTP）、TTFF 预算与计量体系、模块级 deinit/re-init 电源策略；
- **并行前置动作**：①裁剪依赖核查表（可立即启动）；②向海思确认 dv300 低功耗 SDK/KOL 支持的可获得性（深睡路径 NDA 硬阻塞，决定方案上限）。
