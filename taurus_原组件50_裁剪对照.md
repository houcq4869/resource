# ipcamera_hispark_taurus 原组件 vs 裁剪后对照

## 方法

- 基线（裁剪前）：`vendor/hisilicon` 仓库基线提交 `cc5f726` 的 `hispark_taurus/config.json`（对应 `FINAL_vendor_hisilicon.patch` 的 `a/` 侧）
- 现状（裁剪后）：工作树 `vendor/hisilicon/hispark_taurus/config.json`（`FINAL_vendor_hisilicon.patch` 的 `b/` 侧）
- 交叉验证：AOV 文档 `02_report/L1组件逐项分析_功能与裁剪依据.md`（“50 组件 = 裁剪前 taurus 基线清单；最终构型 = 保留 30 项”）

## 结论

| 指标 | 裁剪前（原） | 裁剪后（现） | 变化 |
| --- | --- | --- | --- |
| 组件数 | **50** | **30** | -20 |
| 子系统数 | 21 | 14 | -7 |

> **原组件共 50 个**（分布于 21 个子系统）；当前裁剪后剩 30 个。

## 被裁剪的 20 个组件

| 序号 | 组件 | 子系统 | 原功能（裁剪前） |
| --- | --- | --- | --- |
| 1 | `ability_lite` | ability | 轻量 Ability 管理框架（AMS），应用生命周期与调度 |
| 2 | `dmsfwk_lite` | ability | 轻量分布式任务调度框架（跨设备 Ability 调度） |
| 3 | `camera_sample_app` | applications | 相机示例应用（预览/拍照 UI Demo） |
| 4 | `camera_screensaver_app` | applications | 相机屏保应用（依赖 enable_screensaver） |
| 5 | `device_auth` | security | 设备认证，设备间身份互认与可信关系（软总线配套） |
| 6 | `device_security_level` | security | 设备安全等级评估（软总线配套） |
| 7 | `window_manager_lite` | window | 轻量窗口管理，含输入分发 IMS（唯一 hdi_input 消费者） |
| 8 | `sensor_lite` | sensors | 轻量传感器框架（PIR 走 GPIO 时不使用） |
| 9 | `appspawn` | startup | 应用孵化服务，fork/拉起应用进程 |
| 10 | `dsoftbus` | communication | 分布式软总线（发现/组网/传输） |
| 11 | `ace_engine_lite` | arkui | 轻量 JS UI 引擎（声明式 UI 运行环境） |
| 12 | `ui_lite` | arkui | 轻量 UI 组件框架（控件绘制） |
| 13 | `drivers_peripheral_display` | hdf | 显示外设驱动（HDF display） |
| 14 | `drivers_peripheral_sensor` | hdf | 传感器外设驱动（HDF sensor） |
| 15 | `drivers_peripheral_vibrator` | hdf | 振动器/马达驱动（HDF vibrator） |
| 16 | `drivers_peripheral_light` | hdf | 灯/LED 驱动（HDF light） |
| 17 | `acts` | xts | XTS 应用兼容性测试套件 |
| 18 | `tools` | xts | XTS 测试工具集 |
| 19 | `device_attest_lite` | xts | 设备证明组件（XTS） |
| 20 | `syscap_codec` | developtools | SysCap 编解码工具 |

## 被裁掉的子系统（7 个）

- `ability`（ability_lite、dmsfwk_lite）
- `applications`（camera_sample_app、camera_screensaver_app）
- `arkui`（ace_engine_lite、ui_lite）
- `window`（window_manager_lite）
- `sensors`（sensor_lite）
- `xts`（acts、tools、device_attest_lite）
- `developtools`（syscap_codec）

> 裁剪仅删除 `config.json` 中组件条目，**源码目录仍保留在树内**（组件级裁剪，非物理删除），因此不影响其他产品构建。
