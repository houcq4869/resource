# PoC 验证计划（浅 AOV·第一步）

| 项目 | 内容 |
|---|---|
| 文档名称 | AOV 浅 AOV PoC 验证计划（AOV 专项·阶段 5） |
| 文档版本 | V1.0 |
| 日期 | 2026-09-10 |
| 验证对象 | 阶段 4《AOV 系统级低功耗方案设计》§4 第一步"浅 AOV"全部交付项 |
| 验收锚点 | 阶段 4 §4 第一步验收：值守循环 7×24 稳定（1 万次唤醒无失败）、时间轴误差 ≤1s、TTFF/唤醒窗口分段数据齐备、整板值守功耗基线实测值 |
| 代码基线 | `/home/houcq/workspace/oh_release`（PoC 补丁不直接改基线，建独立分支/patch 集管理） |

---

## 1. 平台与环境

### 1.1 平台选择（修订阶段 4 §5 决策）

| 平台 | 角色 | 理由 |
|---|---|---|
| **hispark_taurus（hi3516dv300）** | **PoC 主平台** | camera_lite/media_lite/powermgr_lite 产品配置齐全（config.json:174-180）；MPP 静态链入、HI_MPI_SNAP/imx335 钩子齐备；~~构建配置关 `LOSCFG_KERNEL_SMP` 做单核原型~~ **【T6 第三批实证否决：海思 MPP 预编译库/dwc_usb3 依赖 SMP 编译的 LOS_SpinLock 外部符号，关 SMP 链接失败】→ dv300 保持 SMP，深睡期从核 park 机制自研（阶段 4 P1-5 升为唯一路线）** |
| hispark_aries（hi3518ev300） | 跨平台对照（次优先） | 单核原生；powermgr 未启用——启用动作本身即验证项（阶段 2 P2-5）；MPP 为 hi3516ev200_* .so 不同构，业务层平台无关性检验 |

### 1.2 构建环境现状与风险（T0 前置事实）

- 工具链已就位：`prebuilts/gcc/linux-x86/arm/gcc-linaro-7.5.0-arm-linux-gnueabi`（`workspace/openharmony_prebuilts` 同名 tar 已解包）；hb 已安装（pyenv shim）；python 3.9.23；
- **已知风险**：out/ 下存在一次失败构建记录（`ipcamera_hispark_taurus_linux` build.log：Broken pipe / UNKNOWN ERROR），且本代码树为 api_version 8 老世代 BSP + 新 manifest 混合——**构建打通是 T0 的第一风险项**，预留排障时间；
- 构建命令基线：`hb set`（选 ipcamera_hispark_taurus）+ `hb build -f --gn-args ohos_build_type='"release"'`；或 `./build.sh --product-name ipcamera_hispark_taurus`；
- 烧录/调试：串口（115200）+ SD 卡/eMMC 烧录（uboot 预编译，按海思 hispark 常规烧录流程）；
- 计量硬件：直流功率计/源表（整板串联，采样 ≥10Hz）、万用表、（可选）示波器或逻辑分析仪 + 空闲 GPIO×2（TTFF 硬件打点）、SD 卡（FAT32）。

---

## 2. 验证任务分解（T0~T7）

> 依赖关系：T0→T1→(T2→T3→T4)→T5→T7；T6 与 T2~T5 并行。

### T0 构建打通与基线镜像（估 3~5 天，含排障）

| 项 | 内容 |
|---|---|
| 目的 | taurus（关 SMP）与 aries 双平台 release 镜像构建通过；建立裁剪/优化前基线 |
| 步骤 | ① 修复构建环境（参照 out/build.log 失败记录排障）② taurus kernel_configs 关 SMP 构建单核原型 ③ aries config.json 启用 powermgr 子系统块（照抄 taurus:174-180，不开 screensaver，确认 ipc 组件在列）④ 烧录启动，串口确认 foundation/media_server 正常、camera sample 可预览/录像 |
| 计量点 | **镜像基线**：各分区 bin size（uboot/kernel/rootfs/userfs）、启动后空闲内存水位（hidumper/meminfo）、空闲态整板功耗（WFI idle，功率计 10 分钟均值）、开机到 shell 就绪时间（串口时间戳） |
| 通过标准 | 双平台镜像可烧录、系统可启动、录像链路手动验证通过、基线数据四件套齐备 |
| 产出 | 《T0 基线报告》（size/内存/功耗/启动时间四基线）+ 可复现构建脚本 |

### T1 计量埋点体系（估 3 天）

| 项 | 内容 |
|---|---|
| 目的 | "无计量则无优化"（阶段 2 P2-1）：TTFF 分段 + PM 事件打点先行，后续所有优化用它度量 |
| 改动 | ① `sdk_liteos/mpp/module_init/src/sdk_init.c`：逐 mod_init 前后插桩（时间戳+模块名，hilog/串口输出）② kernel init level 耗时（`LOS_MODULE_INIT` 链打点，los_pm.c 同款机制遍历）③ 业务首帧点：camera/media 首帧回调处 GPIO 翻转 + 串口时间戳 ④ PM 锁审计：扩展 `LOS_PmLockInfoShow`（持锁者+时长）挂 hidumper ⑤ suspend/resume 耗时钩子（K2 的 CNTPCT 记录点顺带输出） |
| 计量点 | TTFF 瀑布：uboot（GPIO 上电沿→kernel 首打印，硬件打点）/kernel/MPP mod_init/业务首帧，各段 ms 级 |
| 通过标准 | 冷启动 10 次采样，各段耗时可复现（方差 <10%），瀑布图输出脚本化 |
| 产出 | 埋点 patch 集 + 《TTFF 分段基线报告》 |

### T2 真实休眠触发链路（估 4 天）——阶段 4 S1+K4

| 项 | 内容 |
|---|---|
| 目的 | 打通"业务允许睡 → 系统真的进入内核 PM 休眠"链路（当前三重空置的第一层） |
| 改动 | ① `powermgr_lite/services/src/power/small/auto_suspend_loop.c:29`：sleep(10) 桩 → 照抄 mini 版 `LOS_PmReadLock()+LOS_PmSuspend`（经修正通道）② `power_proc.c:257-263`：power_count 权限 0444→0664；`proc_file.c` 补权限校验 ③ 产品侧覆写 WEAK `OsIdleTask`（单核原型下无从核问题）：`while(1){LOS_PmReadLock(); LOS_PmSuspend(0);}` ④ `LOS_PmReadLock` 超时参数化+返回语义修复（los_pm.c:624-632） |
| 步骤 | RunningLock 持/放 API 触发（测试程序 AcquireRunningLock(BACKGROUND)→Release）→ 观察串口 PM 进入/退出打印（默认 handler PRINTK 即证据）→ 空闲态功耗对比 T0 基线（默认 handler=WFI，功耗应≈基线，本项验证**链路**不验证收益） |
| 通过标准 | 锁持有期间不进休眠；释放后 500ms 内进入 `OsPmSuspendDefaultHandler`；1000 次锁循环无死锁/无睡死（看门狗验证） |
| 产出 | patch（powermgr_lite×2 文件 + kernel×3 文件 + 产品覆写×1）+ 链路验证报告 |

### T3 LIGHT 档 + RTC 定时唤醒（估 5~7 天）——阶段 4 B1(浅)+B6

| 项 | 内容 |
|---|---|
| 目的 | 值守态载体：LIGHT_SLEEP 档真实实现（时钟门控级）+ RTC alarm 周期唤醒闭环 |
| 改动 | ① 新增 `device/soc/hisilicon/common/platform/pm/`：`LOS_PmRegister(LOS_PM_TYPE_SYSCTRL)` 注册 lightSuspend/lightResume（第一步实现=可安全门控的外设时钟关断（保守清单：VO/显示类 CRG 位，逐个实测）+ WFI；深睡序列不做）② RTC alarm 唤醒桥接：测试程序经 HDF RTC API（`RtcWriteAlarm/RtcAlarmInterruptEnable`，rtc_hi35xx.c 链路已就绪，irq37）设 1s 周期 alarm → 休眠 → alarm 唤醒 → 回调计数 ③ GPIO 唤醒验证（PL061 边沿中断，按键/模拟 PIR） |
| 计量点 | 唤醒延迟分解：alarm IRQ→resume 完成→业务回调（串口时间戳）；LIGHT 态整板功耗 vs T0 空闲基线（时钟门控收益） |
| 通过标准 | 1s 周期 alarm 唤醒 24h 无丢失（86400±容差次）；唤醒延迟 ≤500ms（保底，实测记录分解）；LIGHT 态功耗低于 T0 空闲基线（收益为时钟门控级即可，深睡收益属第三步） |
| 产出 | pm 平台层 patch + RTC/GPIO 唤醒验证报告（含唤醒延迟分解表） |

### T4 时间连续性（估 5 天）——阶段 4 K2+3.4

| 项 | 内容 |
|---|---|
| 目的 | AOV 致命项闭环：休眠/唤醒不丢时间，录像时间轴连续 |
| 改动 | ① 内核 offset：`los_sched_pri.h OsGetCurrSchedTimeCycle()` 加 `g_osTimeOffsetCycle`；suspend 前记 CNTPCT+读 RTC，resume 后 RTC 差值换算累加（LIGHT 档 CNTPCT 不停走则跳过，为第三步 DEEP 预埋）② `OsPmTickTimerStop/Start` 用 `HalClockTickTimerReload/GetTickTimerCycles` 实现真实逻辑（los_pm.c:86-96 空桩）③ 开机 RTC 校时：init pre-init job 或 foundation 内任务 `RtcReadTime→settimeofday` ④ sntp 编入：替换 `fixme.c:391` 空桩，编入 `third_party/lwip/src/apps/sntp/sntp.c` + `SNTP_SET_SYSTEM_TIME` 回调 + 周期校时（6h）+ 校时写回 RTC |
| 计量点 | 24h 值守循环后：录像文件时间戳 vs NTP 真值误差；gettimeofday/LOS_TickCountGet/软定时器三者一致性；跨休眠软定时器到期精度 |
| 通过标准 | **24h 时间轴误差 ≤1s**；休眠期软定时器不漂移（唤醒后到期时刻正确）；NTP 断网场景退化为 RTC 走时（误差记录） |
| 产出 | 时间连续性 patch（kernel×3 + lwip×2 + init cfg）+ 24h 校验报告 |

### T5 值守单帧循环 + 稳定性（估 7~10 天）——阶段 4 §3.5

| 项 | 内容 |
|---|---|
| 目的 | 浅 AOV 业务闭环：RTC 唤醒→单帧采集编码→检测→攒批落盘→回睡 |
| 实现 | 新增 aov_poc 业务任务（media_server 内或独立 bin，参照海思公开 sample_kol 结构与树内 store_sample）：① sensor standby/restart（imx335 `pfnStandby/pfnRestart` 预编译钩子，先 MPI 层验证行为）② `HI_MPI_SNAP_TriggerPipe` 单帧采集（mpi_snap.h）③ VENC H.264/H.265 编码（GOP 策略：I 帧间隔=缩时段落锚点）④ libmd 移动侦测（MPP libmd.a，768×448 子流）命中→升全速 15fps×15s（滞回 5 帧）⑤ 攒批落盘：1MB 缓冲满/事件/休眠前 fsync（FATFS）⑥ 循环尾设下一 RTC alarm→经 T2/T3 链路休眠；唤醒窗口步骤②~⑥分段打点（T1 体系） |
| 稳定性 | 自动化：1s 周期×**1 万次唤醒**（≈2.8h）+ 4s 缩时周期×24h 长稳；串口日志解析脚本统计失败率/唤醒延迟分布/时间漂移/SD 写入错误 |
| 通过标准 | **1 万次唤醒 0 失败**；唤醒窗口（sensor restart→落盘完成）≤100ms 目标值实测（未达则给出分解与优化项）；24h 长稳录像文件时间轴连续（联动 T4 标准）；事件触发→全速切换 ≤2s（第一步口径） |
| 产出 | aov_poc 业务 patch + 稳定性测试脚本 + 《单帧循环验证报告》 |

### T6 裁剪第一刀落地（估 3~4 天，与 T2~T5 并行）——核查表第一批

| 项 | 内容 |
|---|---|
| 目的 | 验证裁剪方案正确性与实测收益（修正声明值口径） |
| 范围 | 《裁剪依赖核查表》第一批 9 项：camera_sample_app、camera_screensaver_app、drivers_peripheral_light、device_auth、device_security_level、acts、tools、syscap_codec、device_attest_lite（仓库留树）+ enable_screensaver=false + 对应 init cfg×2 条目删除；aries 启用 powermgr（T0 已做） |
| 步骤 | 独立分支实施 → 双平台构建 → 烧录回归（启动链/录像/OTA 接口冒烟）→ 与 T0 基线对比 |
| 计量点 | 镜像 size 差（分区级+文件级 top20）、启动内存水位差、开机时间差、init 日志无 execv 失败噪声 |
| 通过标准 | 构建通过、系统功能回归无退化、**实测收益表**产出（替换阶段 3 声明值预估） |
| 产出 | 裁剪 patch 集 + config.json/init cfg 修订版 + 《第一批裁剪收益实测报告》 |

### T7 浅 AOV 功耗基线报告（估 2 天，汇总）

| 项 | 内容 |
|---|---|
| 目的 | 第一步总验收 + 第二步目标锚定 |
| 内容 | ① 值守态（T5 循环运行中）整板平均功耗（功率计 ≥30min 采样，P_avg 与占空比公式互验）② 各状态功耗矩阵：全速/事件切换/值守/LIGHT 睡/空闲（T0）③ 唤醒窗口时间预算达成表 ④ TTFF 瀑布（T1）⑤ 续航折算（按 9000mAh/5V 换算天数，对照阶段 1 §4 基线表）⑥ 与业界对标差距分析（vs 80mW 保底/45mW 竞争）→ 输出第二步（标准 AOV）优化项优先级排序 |
| 通过标准 | 阶段 4 第一步验收四项全达成；差距分析给出第二步 P1 项的量化预期 |
| 产出 | **《浅 AOV PoC 功耗基线报告》**（阶段 5 核心交付物，第二步立项依据） |

---

## 3. 计量方法规范

| 计量项 | 方法 | 工具 |
|---|---|---|
| 整板功耗 | 电源串联功率计，采样 ≥10Hz；每状态 ≥10min 稳态均值；记录供电电压（5V/整板口径） | 功率计/源表 |
| 分段功耗（可选） | sensor/DDR/WiFi/SD 支路分流或替换供电点 | 万用表+分流器 |
| TTFF/唤醒延迟 | 硬件：GPIO 翻转+示波器（上电沿、kernel 首打印、首帧点）；软件：串口时间戳+hilog；两者交叉校准 | 示波器/串口脚本 |
| 时间漂移 | 录像文件时间戳 vs NTP 真值（PC 端脚本比对）；RTC 读数 vs 系统时间 | 测试脚本 |
| 内存水位 | hidumper/meminfo 启动后稳定值；裁剪前后同点位对比 | hidumper |
| 稳定性 | 自动化循环+串口日志解析（失败率/延迟分布/漂移统计） | python 脚本 |

## 4. 排期建议（单人 4~5 周 / 双人 3 周）

| 周 | 任务 |
|---|---|
| W1 | T0 构建打通（风险项优先）+ T1 埋点 |
| W2 | T2 休眠链路 + T3 LIGHT/RTC 唤醒（T6 并行启动） |
| W3 | T4 时间连续性 + T5 单帧循环开发 |
| W4 | T5 万次唤醒+24h 长稳 + T6 收益实测 |
| W5 | T7 汇总报告 + 补丁集整理归档 |

## 5. 风险与依赖

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| 1 | 老世代 BSP+新 manifest 混合树构建失败（已有失败记录） | **高** | T0 首位排障；备选：锁定纯 OpenHarmony 3.1/3.2 Release 对照树重建 |
| 2 | 硬件可得性：taurus/aries 板卡、功率计、示波器 | 高 | 启动前确认清单；无功率计则先以电流采样替代（精度降级标注） |
| 3 | imx335 standby/restart 钩子在 liteos 预编译库中的实际行为未知 | 中 | T5 先做 MPI 层单项验证；不通则以 VI stop/start 替代（收益降级记录） |
| 4 | HI_MPI_SNAP 在 dv300 liteos MPP 的行为/文档缺失 | 中 | 备选：VI-VENC 单帧通道启停方案（sample_venc 参照） |
| 5 | 关中断 suspend 模型下 RTC IRQ 唤醒时序异常 | 中 | T3 先裸验证 alarm IRQ 唤醒 WFI；异常则引入唤醒源前置使能（GIC 配置）专项 |
| 6 | SD 卡攒批写入掉电/休眠一致性 | 低 | fsync+休眠前 sync 纪律（阶段 4 3.5 步骤 7）；FATFS cache sync thread 评估开启 |
| 7 | PoC 补丁与基线分支管理混乱 | 低 | 独立 patch 集管理（每 T 一组 patch+README），不合入基线直至评审 |

## 6. 交付物清单（阶段 5 总产出）

1. PoC patch 集（T1~T6，按仓库分组：kernel_liteos_a / powermgr_lite / device_soc_hisilicon / vendor_hispark / lwip / init / aov_poc 业务）
2. 测试与计量脚本集（TTFF 解析、稳定性循环、时间漂移比对、功耗采样）
3. 报告：T0 基线 / TTFF 分段 / 唤醒延迟分解 / 时间连续性 24h / 单帧循环与万次唤醒 / 第一批裁剪收益实测 / **浅 AOV 功耗基线报告（T7，核心）**
4. 第二步（标准 AOV）优化项优先级排序与量化预期（T7 附属结论，作为阶段 4 §4 第二步的启动输入）
