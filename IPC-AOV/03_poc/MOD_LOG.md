# MOD_LOG — 修改登记册（可回溯性总账）

> 每行 = 一次修改的完整回溯链：问题来源 → 代码改动（含 `Fixes:` 注释）→ 补丁归档 → 构建/符号验证 → 待硬件验证项
> 维护规则：此后对 oh_release 的任何修改必须先在此登记编号再动手

## 2026-09-17 批次（审查修复批次）

基线：旧 FINAL 补丁集（resource 仓 git HEAD 版）；验证基线文档：`Kimi/05_文档真实性验证记录.md`
补丁归档：`patches/FINAL_*.patch`（全量，已重导）+ `patches/fix/20260917/FIX_20260917_*.patch`（纯增量）

| 编号 | 问题来源 | 修改内容 | 涉及仓/文件 | 补丁 | 构建验证 | 待硬件验证 |
|---|---|---|---|---|---|---|
| FIX-S1 | Kimi/02 #S1（严重） | los_pm.c EXIT 路径重排：设备 resume + `sysctrl->late` 移到 `LOS_SpinUnlockRestore`/`LOS_TaskUnlock` 之后；los_pm.h 增补 LosPmSysctrl 全回调执行上下文契约注释 | kernel/liteos_a: los_pm.c, los_pm.h | FIX_20260917_kernel_liteos_a.patch | ✅ taurus+aries 构建零错误；OsIdleTask 128B/108B 不变 | D1 万次唤醒（重点第 64 次整数倍统计打印点不再死锁） |
| FIX-S2 | Kimi/02 #S2（严重） | pm_hi35xx.c：RTC epoch 起点采集移入 `HiPmEarlySuspend`（可睡眠上下文）；offset 补偿逻辑迁入新增 `HiPmDeepOffsetApply` 由 `HiPmLateResume` 调用；deepSuspend/deepResume 仅剩 WFI/空——关中断临界区不再有任何可睡眠操作；M1（64 位 offset 撕裂读）随之消除 | device/soc/hisilicon: pm_hi35xx.c | FIX_20260917_device_soc_hisilicon.patch | ✅ 双平台构建；`[AOV-PM]`×3 字符串在镜像 | B4 deep offset 自校验（增量≈0 机制自校验） |
| FIX-S3 | Kimi/02 #S3（严重） | sntp_port.c：新增 `g_sntpSynced` 标志，`LwipSntpSetSystemTime` 回调置位，`lwip_sntp_start` 轮询改为判标志——无 NTP 应答时正确等待 10s 超时返回失败，杜绝 1s 假成功；顺手修正 2 处过时注释（sntp_port.c 头注释、lwipopts.h:226、rtc_hi35xx.c 引用注释） | kernel/liteos_a: sntp_port.c, lwipopts.h; device/soc: rtc_hi35xx.c | 同上两补丁 | ✅ 构建；ntpdate 命令字符串在镜像 | B5 断网用例必须 10s 超时失败 |
| FIX-M2 | Kimi/02 #M2 | los_pm.c `LOS_PmUnregister` 增"禁止运行期注销"约束注释（suspend 遍历不持锁，运行期注销有 UAF 风险；正式支持需先加锁） | kernel/liteos_a | 同上 | ✅ 文档级 | — |
| FIX-M3 | Kimi/02 #M3 | power_proc.c `PowerCountRead`：`LOS_PmReadLock` 返回值（事件位/超时码）换算回锁计数语义——超时打印实时计数，事件位打印 0；新增 los_event.h include | kernel/liteos_a: power_proc.c | 同上 | ✅ 构建 | 冒烟期 `cat /proc/power/power_count` 两次读数合理性 |
| FIX-M4 | Kimi/02 #M4 | rtc_hi35xx.c `HiRtcSyncSystemTime`：补 month/day/hour/min/sec 范围校验，RTC 寄存器越界值不再产生垃圾系统时间 | device/soc/hisilicon | 同上 | ✅ 构建；`[AOV-TIME]` 字符串 6→7（新增日志行） | A5 开机校时（含 RTC 未初始化场景） |
| FIX-M5 | Kimi/02 #M5 | power_proc.c `PowerCountWrite`：成功返回消费字节数（原 `-(int)LOS_OK`=0 违反 VFS write 语义，shell echo 报错） | kernel/liteos_a | 同上 | ✅ 构建 | 冒烟期 `echo 0 > /proc/power/power_count` 无报错且触发挂起 |
| FIX-M6 | Kimi/02 #M6 | aov_poc.c `AovActiveBurst`：计时改 burst 起点帧数快照（原用进程累计帧数，第二次起 ACTIVE 必立即退出、滞回失效）——**B6 MD 接入前置必修项** | vendor/hisilicon: aov_poc.c | FIX_20260917_vendor_hisilicon.patch | ✅ 构建；aov_poc 入 rootfs/bin，DT_NEEDED=17 | B6 ACTIVE 路径（MD 桩切换后） |
| FIX-M8 | Kimi/02 #M8 | aov_poc.c 分段语义修复：段路径跨 flush 持久化（`g_ctx.segPath`）；`segFrames` 改按帧计数（原按 flush 次数名存实亡）；段滚动时 `RequestIDR` 保证段首关键帧可独立回放；顺带：单 pack>1MB 直写防溢出（原堆溢出风险）、短写重试、fsync 返回值检查、GetStream 错误计数打印（原全吞静默空转）、mkdir 失败检查、`-i` 参数口径与 usage/头注释统一为 1~60s | vendor/hisilicon: aov_poc.c | 同上 | ✅ 构建 | B6 分段文件逐个可 ffplay 回放 |
| FIX-M9 | Kimi/02 #M9（决策：恢复音频） | 恢复 T6 三批对音频的内核侧裁剪：kernel_configs×4 `LOSCFG_DRIVERS_HDF_AUDIO(+CODEC_HI3516+CODEC_TF9879)=y`；hdf.hcs 恢复 5 条 audio include；device_info.hcs 恢复 107 行 audio host 块（与 HEAD 字节级一致）；ohos.build 恢复 hdf_audio_config。用户态 audio_lite/drivers_peripheral_audio 原本保留，现链路完整 | vendor/hisilicon×8 文件 | 同上 | ✅ 构建；内核镜像含 5 个 hdf_audio 服务名+11 处 audio 字符串；OHOS_Image.bin 6,463,488→6,529,024B（+64KB 音频驱动，预期） | A4 media_server 音频链路真实可用（原"空转假设"作废，改为正向验证） |
| FIX-M10 | Kimi/02 #M10 | **复查后驳回**：删除 devtable `/bin/hidumper` 行是 aries jffs2 打包的必要修复（aries对照构建报告 #6：hidumper_lite 不产出该 bin，条目存在则 mkfs.jffs2 失败），非 taurus 裁剪误伤。维持删除，不收口 | build（无改动） | — | ✅ aries 构建通过即实证 | — |
| FIX-M11 | Kimi/02 #M11 | huks_server 维持 post-init 延迟启动（T6 二批既定优化）。init cfg 为严格 JSON 不支持注释；改在此登记动机与风险：foundation/media_server 早期访问 huks 可能 IPC 失败重试 | 无代码改动 | — | — | A2 冒烟期观察 huks 相关日志 |
| FIX-H1 | 卫生项 | lwip_porting.gni 8 行 CRLF→LF（HEAD 原有 1 行 CRLF 不动）；build/.gitignore + `hb/ohos_build.egg-info/`；device_soc/.gitignore + `__pycache__/`、`ws63v100/sdk/output/`、mfg 签名 bin；drivers/hdf_core 新建 .gitignore（hdf_macro_test.h 生成物） | kernel/build/device_soc/hdf_core | 对应 FIX 补丁 | ✅ | — |
| FIX-P1 | Kimi/03 #P1（高） | **safwk_lite 尾随空格修复补归档**：新增 `FINAL_foundation_systemabilitymgr_safwk_lite.patch`（base 1b620e12，+3/-3），补丁集 11 仓**恢复完整可重放** | foundation/systemabilitymgr/safwk_lite | FINAL_..._safwk_lite.patch | ✅ 重放演练 11/11 IDENTICAL | — |
| FIX-P2 | Kimi/03 #P2 | `FINAL_base_commits.txt` 重生成：统计列按 `git diff --shortstat` 实测（含 add -N 新文件），修正 kernel 261/69→518/119 等陈旧值 | patches/ | — | ✅ | — |

## 2026-10-21 批次（源码树还原）

| 编号 | 问题来源 | 修改内容 | 涉及仓/文件 | 补丁 | 构建验证 | 待硬件验证 |
|---|---|---|---|---|---|---|
| REV-20261021-01 | 用户指令（还原 oh_release 至补丁前基线；oh_lts/wukong100 已确认干净不受影响） | **全量回退 11 仓工作树改动**：回退前逐仓 `git apply --check --reverse` 校验归档补丁完整覆盖当前状态（11/11 通过，hilog_lite/vendor 两仓因 .patch 在笔记仓被规范化行尾空白需 `--ignore-whitespace`，内容语义一致）；随后 `git checkout -- .` 恢复被改文件 + 定向删除补丁新增文件（kernel: sntp_port.c；device_soc: common/platform/pm/；hdf_core: .gitignore；vendor: hispark_taurus/aov_poc/）。**未 commit，未触碰 oh_lts** | 全部 11 仓 | 无新补丁（FINAL_*.patch 即本次回退内容的完整归档，恢复方法：逐仓 `git apply --ignore-whitespace` 对应 FINAL patch） | ✅ 11 仓 HEAD 与 FINAL_base_commits.txt 基线逐一相符；源码文件 `git status` 零改动（device_soc/hdf_core/build 残留 ws63 `__pycache__`/`sdk/output/`/egg-info/生成头文件等**构建产物**，非补丁内容，下次构建会重新生成）；11/11 FINAL 补丁正向重放 dry-run 通过（可随时恢复 PoC 态） | — |

## 修改后验证快照（2026-09-17，对照 Kimi/05 §3）

| 指标 | 修改前 | 修改后 | 说明 |
|---|---|---|---|
| taurus 构建 | ✅ | ✅ 零错误 | `build successful` |
| aries 构建 | ✅ | ✅ 零错误 | 增量 |
| OHOS_Image.bin | 6,463,488 | 6,529,024（+64KB） | = FIX-M9 音频驱动恢复 |
| rootfs 内容 | 19,459,145 | 19,463,138 | +3,993（aov_poc 重编） |
| userfs 内容 | 5,114,020 | 5,114,020 | 不变 |
| OsIdleTask | 128B / aries 108B | 不变 | |
| g_pmDevicePool / g_osPmTimeOffsetCycle | 96B / 8B | 不变 | |
| init 服务 | 7 | 7 | 不变 |
| aov_poc DT_NEEDED | 17 | 17 | 不变 |
| 补丁重放 | 10/11（缺 safwk） | **11/11 全 IDENTICAL** | FIX-P1 |

## 未修复项（留待后续，原因在案）

- M1（offset 64 位撕裂读）：已随 FIX-S2 消除（offset 计算收敛到 late 单线程上下文），无需单独修。
- aov_poc 其余轻微项（ISP/standby 竞态 M7、TickMs 49 天回卷、init 错误路径资源释放）：M7 属硬件联调项（B6 阶段验证），其余列入第二步产品化清单。
- 已知遗留：wakeCount ABA、锁计数边界（los_pm.c 理论项）；`OsPmTickTimerStop/Start` 空桩（G1 tickless 第二步一并处理）。

## 流程约定（自今日起生效）

1. 修改前：在本文件追加登记行（编号 FIX-<源问题号> 或 NEW-<日期>-<序号>）。
2. 代码内必须带 `Fixes: Kimi/02_代码审查报告.md #编号` 或对应溯源注释。
3. 修改后：双平台构建 → 更新本文件验证列 → 重导受影响 FINAL patch + 重算 base_commits → 重放演练全 IDENTICAL。
4. 硬件验证完成后回填"待硬件验证"列，并同步《方案验证对照报告》。
