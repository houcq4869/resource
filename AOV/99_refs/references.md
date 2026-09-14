# 参考资料索引（核心一手来源）

> 访问日期均为 2026-09-10。完整参考列表（约 200 条，含可靠性分级）见各分项报告文末。
> 本索引仅收录**一手/官方/高价值**来源，营销与低可信来源不入索引（在各报告内已标注）。

## 分项报告索引

| 文件 | 主题 | 参考条数 |
|---|---|---|
| `../01_research/A_hisilicon_aov.md` | 海思 KOL/AOV（CV610/CV608/老平台） | 20 |
| `../01_research/B_ingenic_aov.md` | 君正 AOV（T41/T32/T33、选型指南、觅睿案例） | 28 |
| `../01_research/C_other_domestic_vendors.md` | 星宸/瑞芯微/全志/安凯微/富瀚微/国科微 | 35 |
| `../01_research/D_ambarella_sensor_products.md` | Ambarella/低功耗 sensor/国内外终端产品 | 67 |
| `../01_research/E_common_tech_topics.md` | 快启/STR/占空比/状态机/存储网络/RTOS 框架 | 55 |

## 一、海思（本项目直接对标）

- Hi3516CV610 官网产品页（含 OpenHarmony 4.1 SDK 支持声明）：https://www.hisilicon.com/cn/products/smart-vision/public-security/IPC/Hi3516CV610
- 《Hi3516CV610 产品简介》官方 PDF v04（典型功耗 1043mW，AOV 特性，型号差异表）：https://gitee.com/e-hi3516cv610/Docs/raw/master/产品规格书/Hi3516CV610%20超高清智慧视觉%20SoC%20产品简介.pdf
- GitCode 官方文档仓 HiSpark/Hi3516CV610（**Apache-2.0 头文件：`ot_common_syskol.h`、`ss_mpi_syskol.h`** 等；quick_start_demo、fast_ae 案例）：https://gitcode.com/HiSpark/Hi3516CV610
- 易百纳 MPP Sample 仓（**src/kol 参考实现全源码 24 文件**）：https://gitee.com/e-hi3516cv610/Hi3516CV610_SDK_V1.0.2.1_MPP_Sample
- 鸿鸥派 PICO(HI3516CV610) 规格书 V1.5（**§2.3 KOL 模式整板实测功耗**：深睡 350mW/浅睡 610mW）：https://gitee.com/e-hi3516cv610/Docs/raw/master/产品规格书/HongOUPI_PICO(HI3516CV610)规格书_V1.5.pdf
- KOL demo rootfs + sample_kol 二进制（静态分析对象）：https://gitee.com/shumjj/3516cv610_aov
- 海思官方公众号《越影 S610》方案文（转载）：https://www.elecfans.com/d/6742412.html

## 二、君正

- 《君正 AOV 方案选型指南》（三代芯片矩阵、40+mW、休眠 1mW 级）：https://www.ingenic.com.cn/news-detail/nid-383.html （公众号同文：https://mp.weixin.qq.com/s/wckvewzFPg3UD9-6Yw-GOg）
- Atlas 技术页（TTFF<90ms、RISC-V 协处理器）：https://www.ingenic.com.cn/technology/id-12.html ；Zeratul：https://www.ingenic.com.cn/technology/id-13.html
- T41 产品页 + brief PDF：https://www.ingenic.com.cn/products-detail/id-33.html
- Tassadar 平台（T32 首发）：https://www.ingenic.com.cn/news-detail/nid-364.html ；T33 系列：https://www.ingenic.com.cn/news-detail/nid-413.html
- 觅睿 AOV 技术进化之路（**V7 产品级功耗：AOV 白天 11mA/夜间 15mA，9000mAh 13~15 天，600MB/天**）：https://www.ingenic.com.cn/news-detail/nid-392.html ；觅睿 V7 产品页：https://www.meari.com/zh/products/V7
- T41 助力觅睿 24h AOV（2024-04）：https://mp.weixin.qq.com/s/suGz7oBF55injxJCtEctRg

## 三、其他国产厂商

- 瑞芯微 RV1106/RV1103 发布与产品页（250ms 抓图/1s 人脸识别）：https://www.rock-chips.com/a/cn/news/rockchip/2022/0217/1541.html 、https://www.rock-chips.com/a/cn/product/RV11xilie/2022/0926/1661.html
- RV1106B/RV1126B 产品页（AOV 3.0/AOA）：https://www.rock-chips.com/a/cn/product/RV11xilie/2025/1208/2117.html
- RV1106G2 AOV 整机 ~40mW@1fps、5200mAh 14 天：https://news.52solution.com/news/80062014/
- RV1126B AOV 实测连载（**三模式整板 1280/580/180mW、进出 AOV 流程、37h 上限**）：https://zhuanlan.zhihu.com/p/2069055163944457663
- 飞凌 OK1126BJ-C（AOV 值守核心板 0.007W 官方口径）：https://www.forlinx.com/product/240.html
- 国科微 GK7203V1/GK7206V1 官方新闻（**单板 42mW@1fps 含 sensor，业界最硬口径**）：http://www.gokemicro.com/News/info.aspx?itemid=433 、http://www.gokemicro.com/News/info.aspx?itemid=436
- 全志 V853 疾风系统（100/200/700ms）：https://www.allwinnertech.com/index.php?c=news&a=index&id=344 ；V821（Wi-Fi DTIM10 保活 180μA）：https://docs.aw-ol.com/docs/soc/v821/
- 安凯微 AK3918AV130 获奖新闻（整机 30mW@1fps、年出货千万颗）：http://anyka.com.cn/article/22/115.html
- 星宸 SSC303/306 介绍（工作 300mW、PIR 待机 μA 级、首帧 68ms）：https://zhuanlan.zhihu.com/p/2000568550117631855

## 四、国际厂商与 sensor

- 思特威 SmartAOV/快启技术官方文（**快启 CIS 40~60ms、待机 <10μW、SC301HIOT 整套 <40mW@1fps**）：https://www.smartsenstech.com/page?id=242
- Ambarella 官网新闻/产品页（S2Lm、S6LM、CV5/CV72 功耗口径）：见 D 报告 §1.1 引用列表
- 大联大诠鼎 联咏+思特威 AOV 整机参考方案：见 D 报告 §2.4
- Tapo C460 官方续航表（1s 间隔 8 天 / 60s 间隔 55 天）：见 D 报告 §5.2

## 五、共性技术专题（框架/文档/论文）

- **OpenHarmony kernel_liteos_a 源码**（`los_pm.h`/`los_pm.c`：4 档休眠、LosPmDevice/LosPmSysctrl、PM 锁、tick 补偿；`los_task.c` WEAK OsIdleTask）：https://gitee.com/openharmony/kernel_liteos_a
- **OpenHarmony powermgr_lite 源码**（RunningLock/SuspendDevice/WakeupDevice 服务与枚举）：https://gitee.com/openharmony/powermgr_powermgr_lite
- OpenHarmony 电源管理子系统文档：https://github.com/openharmony/docs/blob/master/zh-cn/readme/电源管理子系统.md
- Zephyr PM 官方文档（系统/设备 PM、runtime PM 引用计数、DVFS）：https://docs.zephyrproject.org/latest/services/pm/index.html
- FreeRTOS Tickless Idle 官方文档：https://www.freertos.org/low-power-tickless-rtos.html
- Linux Kernel PM 官方文档（Sleep States / Devices & wakeup sources）：https://www.kernel.org/doc/html/latest/admin-guide/pm/sleep-states.html
- 海思 WS53 LPC 低功耗（设备 PM 注册/sleep veto/GPIO 唤醒）：https://docs.hisilicon.com/projects/fbb_ws53/master/samples/peripherals/lpc/lpc/
- 海思 WS63 WiFi 省电（DTIM=1/3/10 延迟功耗比、PS ~5mA）：https://docs.hisilicon.com/projects/fbb_ws63/master/samples/connectivity/wifi/power-save/power-save.html
- 涂鸦 TuyaOS《AOV 录像本地存储》（攒批写入/上传完成才可休眠/I 帧优先）：https://developer.tuya.com/cn/docs/iot-device-dev/tuyaos-package-ipc-device?id=Kcp17u98e8j19
- 易百纳《什么是 Atlas》（单帧 suspend-resume、大小核、RTC 微瓦级）：https://www.ebaina.com/articles/140000017746
- IPC 启动时间优化（三阶段分解）：https://blog.csdn.net/will_yanjx/article/details/136819208
- 嵌入式 Linux 启动逐段优化（Falcon 省 300~500ms、prelink）：https://raybyte.cn/post/2026/7/28/0db6b4f3
- ArtInChip XIP 官方文档：https://aicdoc.artinchip.com/topics/sdk/xip/xip_user_guide-lite.html
- SD NAND 低功耗与上下电时序（断电 130μA、整机 15mA→6mA）：https://zhuanlan.zhihu.com/p/2065036366740820586
- ESP-IDF WiFi 低功耗（DTIM 原理）：https://docs.espressif.com/projects/esp-idf/zh_CN/v5.4.2/esp32c61/api-guides/low-power-mode/low-power-mode-wifi.html
- DDR self-refresh 与 PHY retention 时序（JESD79-3F）：https://blog.csdn.net/hierro_zs/article/details/68485355
- 高通 STR/S2R 图解（电压域/时钟树/AOP 仲裁）：https://blog.csdn.net/weixin_33587161/article/details/161905927
- 论文 sleepyCAM（IEEE ICC 2017，等待期 5.4mW vs 常开 1423.6mW）：https://oulurepo.oulu.fi/bitstream/10024/25789/1/nbnfi-fe2019041812810.pdf
- 论文 Panoptes（ACM TOMCCAP 2005）：https://dl.acm.org/doi/10.1145/1062253.1062256
- arXiv 自适应占空比（2405.06372）：https://arxiv.org/abs/2405.06372
- 专利 US11137804B2（adaptive duty cycle）：https://patents.google.com/patent/US11137804B2/en
- 专利：低功耗 IPC 快速启动系统：https://www.xjishu.com/zhuanli/62/202310915908.html

## 六、过程证据留存

- 海思调研过程下载的 PDF/克隆源码/二进制分析产物：`/tmp/opencode/`（pdf/、kolrepo/、hs/、hsdoc/），如需长期保留请及时转移（/tmp 可能被清理）。
