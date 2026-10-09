# aries（ev300）对照构建报告：跨平台补丁可移植性验证

| 项目 | 内容 |
|---|---|
| 文档名称 | PoC 扩展项：hispark_aries（hi3518ev300）对照构建与基线修复报告 |
| 日期 | 2026-09-10 |
| 目的 | ① 验证共享补丁（pm 钩子/RTC 校时/sntp/内核 PM 扩展）在**单核 ev300** 的编译链接可移植性（深睡机制验证平台就绪，PoC 计划 T0 扩展项/总结行动#4）② aries 首次启用 powermgr（阶段 2 P2-5） |
| 结果 | ✅ aries 构建通过 + 符号验证通过；✅ taurus 最终 clean 重建复验通过；**发现并修复 6 项 aries 基线损坏**（均与本项目补丁无关，属 api-8 世代配置 vs 6.1 manifest 漂移） |

---

## 1. aries 基线问题与修复清单（6 项）

| # | 问题 | 根因 | 修复 | 仓 |
|---|---|---|---|---|
| 1 | LOAD 失败：`find component os_dump failed` | config.json 引用树内不存在的 os_dump 组件 | 删除该条目 | vendor |
| 2 | GN 失败：`hilogd → ffrt not found` | config 用标准世代组件名 `hilog`/`hidumper`（6.1 中为标准系统组件，走 ohos_part 标准路径拉 ffrt） | 改 `hilog_lite`/`hidumper_lite`（与 taurus 对齐） | vendor |
| 3 | GN 失败：`kv_store → access_token not found` | kv_store 组件 innerkits/distributeddata 面依赖标准组件 access_token（引用方全为标准组件，small 闭包零消费者） | 删除 kv_store 条目 | vendor |
| 4 | media HAL 拷贝失败：`libplugin_vdec_35xx.so` 不存在 | ev300 预编译快照缺失该文件（解码插件，AOV 纯录像非必需）；build.sh 无条件 cp | 改条件拷贝（dv300 行为不变） | device/soc |
| 5 | 内核链接失败：`undefined symbol: g_percpu`（引用方 lto.tmp:hil_vma_check） | **ev300 预编译 libhi_osal.a 按旧代内核 ABI 构建**（旧内核 UP 构建亦提供 g_percpu）；6.1 内核该符号仅 SMP 分支定义（los_percpu.c:35 guard） | los_percpu_pri.h/los_percpu.c 增 UP 兼容分支（`Percpu g_percpu[1]` 最小定义，风险注记：预编译代码按旧布局访问存在差异可能，hil_vma_check 为 OSAL 调试路径，硬件验证期关注） | kernel |
| 6 | jffs2 打包失败：`mksh_rootfs/bin/hidumper: does not exist!` | 共享 devtable `build/lite/make_rootfs/rootfs_liteos.config` 含 `/bin/hidumper` 陈旧条目（6.1 hidumper_lite 不产出该 bin；taurus 走 vfat 不触发） | 删除该条目（仅 3 行，其余 2 条有效） | build |

**aries 启用项**（非修复）：config.json 增 `communication/ipc`（powermgr small 形态前置依赖）+ `powermgr`（powermgr_lite/battery_lite，不开屏保）；kernel_configs×2 增 `LOSCFG_DRIVERS_HDF_PLATFORM_PM=y`。

## 2. 跨平台验证结果

### 2.1 aries 镜像与符号（共享补丁全部生效）

| 验证项 | aries（UP 单核） | taurus（SMP 双核）对照 |
|---|---|---|
| OHOS_Image.bin | 4,554,752 B | 6,463,488 B |
| 镜像格式 | jffs2 ×3（打包成功） | vfat ×3 |
| OsIdleTask 覆写 | **0x7c(124B)**，UP 分支（无 cpuid 判断）✓ | 0x88(136B)，SMP 分支 ✓ |

> **V1.1 尺寸演变注**：上表为当时（K1 前）实测值。K1 分档锁将 idle 循环简化（去 LockCountGet 前置判断，否决/降级逻辑收敛入内核）后，当前值为 **taurus 0x80(128B) / aries 0x6C(108B)**——与《第二步机制扩展_K1K3K5报告》及提交版文档口径一致。
| g_percpu 兼容符号 | .bss 4B（UP ABI 兼容）✓ | SMP 原生定义 |
| T4 链路 | Hi35xxRtcWriteSysTime(0x258)/Hi35xxRtcReadEpoch(0xdc)/sntp_init(0xa8) ✓ | 同款 ✓ + OsShellCmdNtpdate/LwipSntpSetSystemTime |
| AOV 字符串 | [AOV-PM]/[AOV-TIME]/[TTFF] 9 处 ✓ | 10 处 ✓ |
| powermgr 启用 | libpowermgr/libpowermgrservice/libbatterymgr/libbatteryservice 4 库入 rootfs ✓（**首次**） | 已启用且瘦身版 ✓ |
| aov_poc | 未编入（taurus 专属，dv300 MPP 依赖——**符合设计**；ev300 版业务骨架需按 hi3516ev200 MPP .so 形态适配，列硬件联调期） | rootfs/bin/aov_poc ✓ |
| rootfs/bin | 19 项（**aries 未裁剪**，保持基线形态——对照目的是补丁可移植性而非小型化） | 17 项（三批裁剪后+aov_poc） |

### 2.2 taurus 最终 clean 重建（刷新陈旧对象后复验）

背景：T4 期间发现 taurus 增量构建存在**陈旧对象**（api_shell.o 早于 LWIP_SNTP 启用未重编，depfile 未追踪 lwipopts.h）——最终 clean 重建（5129 targets）后全符号复验通过：LwipSntpSetSystemTime/OsShellCmdNtpdate/sntp_init/OsIdleTask（当时 136B，K1 简化后 128B）/Hi35xxRtcReadEpoch/g_osPmTimeOffsetCycle(.bss 8B) + aov_poc 在位；rootfs 19.46MB/userfs 5.11MB/img 19.85MB（与第三批一致，api_shell ntpdate 块移除属预期内微小变化）。

**构建纪律强化**：凡涉及 lwipopts.h/config.h 级宏变更，必须 clean 重建验证（depfile 对 imacros/多级重定向头追踪不完整）。

## 3. 结论与工程认知

1. **共享补丁跨平台可移植性成立**：pm 钩子（SMP/UP 双分支）、RTC 校时/回写/epoch、sntp 链路、内核 PM 扩展（ReadLock/权限/offset）在 ev300 单核全部编译链接通过 → **ev300 作为深睡机制验证平台就绪**（阶段 4 平台策略落地）；
2. **海思预编译库-内核配置强耦合模式再实证**：g_percpu（ev300 OSAL vs UP）与第三批 LOS_SpinLock（dv300 MPP vs UP）同类——**预编译库绑定特定内核世代+配置**，任何内核配置偏离（UP/关 SMP）都需逐库验证链接闭包；
3. **aries 基线在 6.1 manifest 下原本不可构建**（6 处损坏，本项目首次修通）——该树 aries 产品自 api-8 世代后未维护；修复已最小化且全部归档（taurus 零影响）；
4. 补丁总账更新：**10 仓 / 3234 行**（FINAL_*.patch + FINAL_base_commits.txt，含新增文件 add -N），双平台构建产物齐备。

## 4. 移交硬件阶段新增项

| 项 | 说明 |
|---|---|
| aries 上电冒烟 | jffs2 三镜像烧录（SPI NAND flash）；g_percpu 兼容符号运行时观察（hil_vma_check 若被调用且布局不符→异常日志关注点） |
| aries powermgr 链路 | RunningLock/SuspendDevice 服务在 ev300 的端到端验证（与 taurus B2 用例同款） |
| ev300 深睡验证 | 单核平台 DEEP 档机制验证（时间 offset 真实路径需 CNTPCT 停走——ev300 低功耗资料同样需向海思确认） |
| aov_poc ev300 适配 | 按 hi3516ev200_* .so MPP 形态移植业务骨架（API 同源，链接清单需重验） |
