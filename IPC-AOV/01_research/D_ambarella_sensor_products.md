# D. 国际芯片厂商 Always-On Video 方案与终端品牌 AOV 类产品调研

> 调研执行日期：2026-09-10（所有来源访问日期均为该日，以下不再逐条重复标注，仅在参考资料列表中统一注明）
> 调研方式：官网/官方新闻稿/官方规格页为一手来源；行业媒体实测与电商页面为二手来源。
> 可信度说明：文中标注【软广/低可信】的内容来自明显带有营销倾向的文章，仅作旁证；标注"公开渠道不可得"的为确认无法从公开渠道获取的数据，未做推测填充。

## 摘要（核心结论速览）

1. **Ambarella 不使用"AOV"这一营销术语**，但其电池摄像机产品线（S2Lm/S5L/S6LM、CV25/CV28M）从 2015 年起就围绕"快速唤醒 + 低功耗待机 + 智能编码"构建了同类能力：S2Lm 参考设计可在唤醒后 <500ms 开始 1080p30 录像、宣称 6 个月电池续航；S6LM 宣称误报后 <1 秒关断、电池相机续航 2–5 年。Ambarella 未公开 mW 级待机功耗与"低功耗岛"微架构细节（公开渠道不可得）。
2. **传感器侧 AOV 的核心玩家是思特威（SmartAOV™）与格科微（AOV+低功耗快启）**：思特威 SC301HIOT 公开了行业最完整的 sensor 级 AOV 功耗数据（1fps 全时录像整套方案 <40mW，30fps 工作时约 100mW）。Sony 的对标物是面向移动/IoT 的 Always-on（AO）传感技术与内置 AI 的 IMX500 智能视觉传感器，但其安防线 sensor 的低功耗参数不公开。
3. **国内终端品牌已全面 AOV 化**：萤石（AOV 2.0）、乐橙（B7E/AOV Dual/AOV PT 4K）、TP-LINK/Tapo（24/7 Capture）、小米（太阳能摄像机 4 Pro）、觅睿（V1）均有"低帧率缩时全天录像 + 事件全速录像"的电池产品，典型机制为无事件 1 帧/1~3 秒抓拍、检测到人车切换 12~15fps 全速录像，检测方式从 PIR 转向基于图像的 AI 检测（距离从 <10m 提升到 25~30m）。360 是唯一未发现 AOV 产品的主流品牌（BC60 为触发式电池机）。
4. **国际品牌（Ring/Arlo/Wyze/Eufy）的电池摄像头均未采用 AOV 式全天录像**，仍为 PIR/雷达/AI 事件触发录像；其"连续录像"（Ring 24/7 Recording、Arlo 24/7 Recording/CVR）明确要求设备接常电（AC/PoE）+ 付费订阅 + 云端存储。AOV（缩时全时录像、本地存储、免订阅）目前是中国生态（海思/君正/瑞芯微/国科微/星宸/联咏芯片 + 思特威/格科微传感器）主导的差异化路线。
5. 中国低功耗 IPC 市场：2023 年约 112.5 亿元/2250 万台 → 2024 年约 140 亿元/2800 万台（AIoT 星图研究院，转引自安防资讯网）；2025 年 CPSE 安博会超过 60% 参展摄像头企业推出 AOV 系列产品。

---

# 第一部分：国际芯片/传感器厂商

## 1. Ambarella CVseries 的低功耗 / Always-On Video 能力

### 1.1 产品线与功耗数据总表

Ambarella 官方技术页对低功耗的定位："我们的技术面向边缘嵌入式平台（如电池供电摄像机）设计，功耗效率相比竞品方案有时高出 5 倍以上"（未给出具体对比数值）[1]。

| 芯片 | 发布时间 | 制程 | 视频/AI 性能 | 官方公布的功耗数据 | 电池/低功耗相关定位 | 来源 |
|---|---|---|---|---|---|---|
| S2Lm | 2015（参考设计发布） | — | 1080p30 H.264 | 未公布芯片功耗；参考设计宣称**唤醒后 <500ms 开始 1080p30 录像、电池续航最长 6 个月** | 电池 IP 摄像机参考设计，SDK 含低功耗待机、wake-on-Wi-Fi、fast boot to Linux | [2] |
| CV2 | 2018-03-28 | 10nm | 4Kp60/8MP AVC+HEVC，CVflow DNN 性能为 CV1 的 20 倍，立体视觉 | 官方仅称"极低功耗"；第三方：CEO 称 4K+NN+ISP+HEVC 同跑 <5W；CES 2020 开发板实测目标识别负载 6.9W | 汽车/IP 安防/无人机/机器人 | [3][4] |
| CV25 | 2019-01-07 | 10nm 超低功耗工艺 | 4KP30+ AVC/HEVC，CVflow | 未公布具体数值 | **"针对需要长续航与小体积的 wire-free（无连线电池）摄像机应用优化"** | [5] |
| S6LM | 2019-04-08 | 10nm | 4K AVC/HEVC 多码流，SmartHEVC 4K 码率可低至 512Kbps，四核 A53 | 未公布具体数值；**宣称基于 S6LM 的电池相机/PIR 相机在误报（动物/阴影/雨）后可在 <1 秒内关断，整机电池续航可达 2–5 年** | 视频门铃、电池摄像机、PIR 相机 | [6] |
| CV28M | 2020-11-02 | 10nm 超低功耗工艺 | 4KP30 AVC/HEVC，CVflow，320MPixel/s ISP，三 sensor 输入 | 未公布具体数值 | **wire-free 电池相机优化**；AI Timelapse™ 场景感知录像、SmartAVC/SmartHEVC 智能码率控制 | [7] |
| CV5 / CV5S | 2021-01-11 | 5nm | 8K30 或 4×4K 编码，双核 A76，CVflow | 发布稿：**8K30 编码整机功耗 <2W**；现行官网产品页（CV5S）：8K30 录像 **<4W** | 高端 IP/无人机/机器人/运动相机（非电池 IPC 定位） | [8][9] |
| CV72S | 2023-03-21 | 5nm | 4KP60 AVC/HEVC，CVflow 3.0（Transformer 网络加速），AI 性能为上代 6 倍，16MP30 鱼眼去畸变、4×5MP30 多目 | **整机 <3W**（官方称主流安防市场最高每瓦 AI 性能）；支持 AISP（AI-ISP） | 主流专业安防（常电）；双核 A76 1.6GHz，LPDDR4x/5/5x | [10][9] |
| CV7 | 2026-01-05 | 4nm（三星） | 8Kp60 多码流，第三代 CVflow（AI 性能 >2.5×CV5），0.01Lux 低照 | **比上代 CV5 功耗降低 20%**；官方强调"极低功耗降低散热需求、延长电池续航" | 8K 消费/多目企业安防/机器人/车载多码流 | [11] |

注：CV22/CV25/CV28M 共用 SDK 与 CV 工具链 [7]；安防产品线现行型号为 CV22S/CV25S/CV28M/CV52S/CV5S/CV72S/CV75S（产品页）[9]。用户任务中提到的"CV28"对应安防量产型号 **CV28M**；"CV72"对应 **CV72S**（另有车载 CV72AE，不在本文范围）。

### 1.2 Ambarella 面向电池摄像机（AOV 类场景）的技术要点

- **快速唤醒/快速关断**：S2Lm 参考设计（2015）已实现 wake-up 到 1080p30 录像 <500ms、wake-on-Wi-Fi、fast boot to Linux，宣称 6 个月电池续航 [2]；S6LM（2019）强调误报后 <1s 关断以省电，宣称 PIR 电池相机 2–5 年续航 [6]。
- **低功耗待机参考架构**：S2Lm SDK 内含"low-power standby operation"参考实现 [2]。CV22/CV25 有配套电源管理参考设计（NXP AN13272，见 3.2 节）[12]。
- **智能编码降码率**：SmartAVC™/SmartHEVC™ 智能码率控制（CV2/CV28M 等），S6LM 4K 码率可低至 512Kbps [6][7]；CV28M 支持 AI-based rate control 与 **AI Timelapse™**（场景感知缩时录像，避免回看整段时间轴）[7]——AI Timelapse 是与国产 AOV"缩时录像"最接近的官方特性。
- **CVflow 架构**：专用视觉处理引擎，以高层算法描述编程，"以极低功耗扩展到每秒万亿次操作"，配合稀疏化/量化 CNN 编译工具链 [1]。
- **未公开项（公开渠道不可得）**：Ambarella 官网/新闻稿未给出 CV25/CV28M/S6LM 的待机（standby/休眠）mW 级功耗数值，也未公开"低功耗岛（low-power island）/always-on DSP"级别的微架构白皮书；其官网无"Always-On Video/AOV"专页。CV28 开发套件电源树可参考 ADI Circuit Note（CN 页面访问被拒 403，未能读取）[13]。

### 1.3 第三方功耗参考数据（二手来源，低置信度提示）

来自 Ambarella 合作伙伴 Rhonda Software 的技术博客 [4]：

| 芯片 | 第三方功耗数据 | 备注 |
|---|---|---|
| CV2 | <5W（4K 下同时跑 NN+ISP+HEVC 编码，CEO 财报会口径）；CV2AQ 支持 10 个 NN、6 路相机 30fps 时 <5W（Eyeris CEO 口径）；CES 2020 开发板目标识别 60fps 负载实测 6.9W | 常电场景 |
| CV22AQ | 约 2.5W | 常电场景 |
| CV25 | 低于 CV22（性能层级 CV25 < CV22 < CV2，功耗同向） | 定性描述 |

## 2. 低功耗图像传感器（Sony / 思特威 / 格科微）

### 2.1 Sony

**(a) Always-on（AO）传感技术（移动/IoT 线）** —— Sony 半导体官网技术页 [14]：
- 定位：让移动/IoT 设备"常开"感知环境变化，sensor 自带 AO 专用模式，低功耗且减轻外部处理器负担，实现连续感知并显著延长电池寿命。
- 三项关键技术：
  1. **灵活像素 binning 与检测时序**：按感知阶段自主切换分辨率（类似人眼"先察觉再细看"）；
  2. **Power gate 系统**：按系统负载动态关断电路，把待机漏电优化到所需水平；
  3. **片上 AI 引擎 + 轻量推理**：RAW 数据在 sensor 内直接处理压缩，输出"语义（meaning）"信息而非图像，降低整机通信与功耗负担。
- 目标应用：前摄注视亮屏/锁屏控制、手势免触控、2D 条码检测唤醒等（偏消费电子，非安防 AOV）。
- 未公布 AO 模式的具体功耗数值（公开渠道不可得）。

**(b) IMX500/IMX501 智能视觉传感器（in-sensor AI，2020-05-20 发布）** [15]：
- 全球首款内置 AI 处理功能的图像传感器：堆叠式（像素芯片 + 逻辑芯片），逻辑芯片含 AI 专用 DSP 与模型存储；
- 12.3MP 背照式像素；**MobileNet V1 推理 3.1ms，单帧内完成 ISP+AI 全流程**；
- 输出元数据（语义信息）而非图像 → 降低数据量/功耗/通信成本并保护隐私；可选 Bayer RAW / YUV/RGB / ROI / metadata 输出；
- 30fps（video+AI 或 metadata），AI 模型可重写升级；
- 与 AOV 的关系：为"sensor 侧事件检测唤醒主 SoC"提供了硬件基础（检测在 sensor 内完成，主系统可深度休眠）。Sony 未公布 IMX500 整机功耗数值（公开渠道不可得）。

**(c) 安防线**：Sony 安防传感器产品页（STARVIS/STARVIS 2 系列，如 IMX675/IMX678，及 2026 年新发布的 IMX908 4K LOFIC）[16][17]。**安防系列 datasheet 的低功耗模式/待机电流参数不对外公开（公开渠道不可得）**；Sony 目前没有面向安防电池 AOV 场景的"低帧率出图/事件检测唤醒"公开宣传（其 AO 与 in-sensor AI 技术均在移动/工业线）。

### 2.2 思特威 SmartSens

> 说明：任务中提到的"Wisen"经检索未发现与思特威存在公开关联（存在一家结构监测传感器公司"悟莘科技 Wisen Innovation"，与 CMOS 图像传感器无关）[18]。思特威的 AOV 技术商标为 **SmartAOV™**。

**(a) SC301HIOT（物联网 HIOT 系列首款，3MP，2024 年发布、2025Q1 量产）** —— 官网新闻 [19]，sensor 侧 AOV 支撑的标杆数据：

| 项目 | 数据 |
|---|---|
| 规格 | 2048×1536（4:3 画幅，适配鱼眼/双目拼接），DSI™-2 Plus 工艺 |
| **SmartAOV™ 全时录像** | 无事件时以 **1fps 超低帧率持续录制，整套方案工作功耗 <40mW**；事件触发时从休眠**快速启动**切换 **30fps 常规帧率**录制，启动耗时极低、不丢帧 |
| 常规工作功耗 | 30fps 下约 **100mW** |
| 低照/红外 | 850nm 峰值 QE 提升约 29%、940nm 提升约 35%；读取噪声 0.66e-、FPN 0.1e- |
| HDR | 双重曝光行交叠 HDR，>100dB |
| 目标应用 | 智能门铃/门锁、宠物喂食器、全景鱼眼、双目拼接、太阳能 4G 无电无网设备 |

**(b) SC450AI（高阶成像 AI 系列，4MP，2021）** [20]：1/1.8" BSI，SFCPixel®+PixGain，SNR1s 较同类降低 73%、感光度提升 3.7 倍，面向智能门铃/穿戴相机/家用监护等全天候 AI 相机；**是大联大诠鼎 AOV 参考方案的配套传感器**（见 2.4）。该页未公布功耗数值（公开渠道不可得）。

**(c) SC2331 / SC3332（AIoT 及安防 2MP/3MP，2022）** [21]：DSI-2 + 工艺升级 Pro；**工作功耗较行业同规格产品分别降低 49% / 32%**，官方明确指向"电池供电摄像头的低功耗成像方案、全天候拍摄需求"。

### 2.3 格科微 GalaxyCore

**GC20C3（新一代 2MP CIS，2025-06-06 发布）** [22]：
- FPPI® 专利像素工艺，80°C 高温下暗电流仍优于部分更大像素尺寸的竞品；
- **内置 10-bit ADC 与 ISP**，两线串口编程；
- **功耗较前代产品降低 30%**；**官方明确"支持 AOV 及低功耗快启功能"**，适配超低功耗应用场景（智慧物联单/多目摄像头、行车记录仪等）。
- 未公布 AOV 模式下的具体 mW 数值（公开渠道不可得）。

### 2.4 配套参考：AOV 整机参考方案（联咏 + 思特威，大联大诠鼎）

电子工程专辑报道 [23]：
- 方案构成：**联咏 NT98568 SoC + 思特威 SC450AI**（4MP）；
- NT98568：高度整合 SoC，高画质/低码率/低功耗，**官方支持 pre-roll 与 Always on Video 模式，面向电池供电应用**；2MP–5MP/8MP 边缘 IPC；双核 Cortex-A7、新一代 ISP、H.265/H.264、VPE、硬件 DLA；
- 方案工作逻辑（AOV 双模式）：
  - 低功耗模式：周期性截取单帧做 MD（运动）检测 → 无变化则休眠至下一周期；有变化 → AI 人像检测 → 无人则回到睡眠（此时帧率 1fps）；
  - 常规模式：检测到人像后以 **12fps** 抓图录像。

### 2.5 补充：中国 AOV 主控芯片生态（供对照，转引自行业媒体）

安防资讯网（2025-09）行业综述 [24]：AOV 技术定义 = "待机 1fps 低帧率采集 + NPU 实时目标检测 + 事件触发切换高清模式"。

| 厂商 | 芯片 | AOV 相关公开指标 |
|---|---|---|
| 国科微 | GK7203V1（Cortex-A7+RISC-V，0.2TOPS NPU，内置 64/128MB DDR，MIPI 双目可扩展 4 目） | **AOV 模式功耗低至 40mW**；高精度补光控制（采集与补光同步）；快启加速设计 |
| 瑞芯微 | RV1126B（3TOPS，AI-ISP） | **AOV 3.0 待机功耗降至 1mW**；新增音频事件唤醒（狗吠/玻璃破碎） |
| 北京君正 | T41ZM/ZG → T32V → T33V | 初代 T41 **首次实现"全时录像"电池 IPC，休眠功耗 1mW 级**；客户含捷高、**觅睿**等，百万级出货；T32V 内存 512Mb–2Gb 可选 |
| 星宸科技 | SSC308DE | 低功耗快速启动、智能编码 |
| 富瀚微 | FH8626V300 | 双摄 AOV 芯片，主打高检测精度与超低功耗 |
| 海思 | Hi3516CV610（基座级）、Hi3519AV200/Hi3516DV500（中高端）、Hi3559AV100（旗舰 8K） | 回归后覆盖全价位段（未公布 AOV 功耗数值） |
| 安凯微 | KM01A/W | 智能家居/穿戴（2025-04 曾发布"AOV 低功耗智能视觉"芯片公告 [25]） |

市场规模：低功耗 IPC 2023 年 112.5 亿元、出货 2250 万台（占 IPC 整体 10–20%）→ 2024 年 140 亿元、2800 万台（AIoT 星图研究院数据，转引 [24]）。

## 3. 内存（eMCP/低功耗 DDR）与电源管理（简要）

### 3.1 低功耗内存

- **Micron × Ambarella**：CV5 是 Ambarella 首款支持 LPDDR5/LPDDR5X 的芯片，开发期即在 CV5 测试芯片上验证 Micron LPDDR5/5X（1α 工艺，64-bit 系统带宽最高 68GB/s）；Micron 同时为 CV5 家族提供 e.MMC 5.1、i300 microSD、串行 NAND 与 Xccela flash [26]。
- **eMCP/uMCP**（eMMC+LPDDR 合封）是电池 IPC 常用的存储形态，可在单封装内提供存储+内存、缩小 PCB 并利于低功耗设计（科普综述见 [27][28]）。具体到 AOV 摄像机采用的 eMCP 型号/待机功耗，各整机厂未公开 BOM 细节（公开渠道不可得）。
- **AOV 对内存的低功耗要求实例**：海康威视 AOV 4G 球机官方技术说明提到"新引入 **DDR 自刷新（self-refresh）技术**，大幅降低无事件时工作功耗"，并"基于**超低功耗内存的快速启动待机技术**"实现 7×24 全时录像 [29]。

### 3.2 电池 IPC 电源管理（简要）

- **NXP AN13272**：面向 Ambarella CV22/CV25 的电源管理参考设计（应用笔记 PDF 公开可查）[12]。
- **ADI**：曾发布 Ambarella CV28 开发套件 Circuit Note（电源树），页面现访问受限（403）[13]。
- 整机侧低功耗电源设计实例（TP-LINK TL-IPC16B-F4GE 官方描述）[30]：芯片级深度休眠（主控休眠功耗毫瓦级）、电路级断电（1.8V 低压外设分支休眠自动断电）、存储级加速（新 Flash 读取速度翻倍）、电源级高效（DC-DC 转换效率 >90%）。

---

# 第二部分：终端品牌 AOV 类产品

## 4. AOV 产品形态综述

- **定义**（行业通用）：无事件时以低帧率（0.5~1fps 缩时抓拍）持续记录，检测到人/车等事件立即切换正常帧率（12~15fps）高清录像，形成"缩时 + 事件"融合的 7×24 小时全时录像 [23][29][31]。
- **市场**：2025 年 CPSE 安博会上超过 60% 参展摄像头企业推出 AOV 系列产品，相关技术方案占智能视频监控展区 45%；AOV 摄像机价格较三年前下降约 40%，与中高端 PIR 摄像机价格重叠（安防资讯网综述 [31]）。
- **检测机制演进**：传统电池机依赖 PIR（检测距离 <10m、受温度影响误报）→ AOV 机普遍改为"前端周期抓图 + AI 人形/车辆检测"（海康 25m、乐橙/觅睿 30m、Tapo 人 15m/车 30m+、萤石 AOV 2.0 白天 25m/夜间 12m）[29][32][33][34]。

## 5. 国内品牌

### 5.1 萤石 EZVIZ（海康威视消费品牌）

**AOV 2.0 官方技术描述**（萤石官网新品页）[34]：与传统电池相机 PIR 零星录像不同，AOV 模式下设备按设定时间间隔拍照检测；检测到人出现时录制一段正常速度视频，无人时将拍摄照片以**快放（缩时）录像**方式呈现；AOV 2.0 强调更低功耗、更完整录像、更远的图像检测距离（对比 PIR）。

| 产品 | 电池 | 分辨率/帧率 | 录像模式 | 检测/唤醒 | 续航宣称 | 价格 | 来源 |
|---|---|---|---|---|---|---|---|
| HB8 Lite 4G（CS-HB8c，2K+ 4G 云台电池机） | 5,200mAh 可充锂电 | 2K+（2560×1440），15fps（网传自适应），H.265/H.264，最大 4Mbps | **AOV 2.0 全天录像**：按预设间隔抓拍合成缩时视频；检测到活动切换正常速度录像；配太阳能板 + AOV Auto 模式可 24/7 不间断录像 | AI 人形+车形检测（图像检测，非 PIR）：**白天最远 25m、夜间 12m**（官方实验室；对比 PIR 机型约 9m）；智能追踪 | 未单独公布 AOV 模式天数（公开渠道不可得） | 国行售价公开渠道不可得 | [33] |
| HB8 室外云台 4G 电池摄像机 800 万（国行套装，含太阳能板） | 未公布（公开渠道不可得） | 800 万（4K 级） | "全新 AOV 模式"（官方商城卖点） | 智能全彩夜视；4G 双卡终身免流 | 未公布 | **¥499（原价 ¥643，萤石官方商城）** | [35] |
| CB2 室内全无线电池摄像机 | **2,000mAh**（全球官网规格） | 1080p，最高 15fps（网传自适应），H.265 | 全球版为事件录像；国内渠道（苏宁）标题标注"AOV 模式"，官方规格页未见 AOV 细节（公开渠道不可得） | **PIR（水平 88°，距离可调）+ 人形检测** | **50 天**（EZVIZ 实验室：每天 5 分钟触发录像口径） | **¥329–339（萤石官方商城）** | [36][37] |
| CB60 小魔方 4G 版（双目） | **2,600mAh** 可充锂电 | 双 400 万+400 万，8 倍混合变焦，360° 水平无极 | **AOV 低功耗全天录像**，提供延迟摄影（timelapse）一键切换；多种省电模式 | PIR 人体检测抓拍；红外夜视 8m | 未公布（公开渠道不可得） | 公开渠道不可得 | [34] |
| HB90 魔丸室外双摄三云台 4G 版 | 未公布（公开渠道不可得） | 双 400 万（2.8mm 广角 + 6mm 长焦，8 倍变焦），三云台 | **AOV 2.0**：间隔拍照检测，有人正常速度录像、无人缩时快放 | AI 人形/车型检测，声光警戒；4G 双卡槽终身免流（移动/联通/电信全网通） | 未公布 | 公开渠道不可得 | [34] |

注：萤石 HB8（全球版 2K+ Wi-Fi 款，10,400mAh、宣称 210 天续航（每天 5 分钟使用口径）、内置 32GB eMMC）为 PIR+人形检测的事件录像产品，不含 AOV，供对比 [38]。

### 5.2 TP-LINK / Tapo

**国行 TL-IPC16B-F4GE（600 万 4G 电池网络摄像机，2025-12 上市）** [30][39]：

| 项目 | 数据 |
|---|---|
| 分辨率 | 600 万（3200×1800），1/2.45" CMOS，H.265（64Kbps–2Mbps），4mm 定焦 |
| 电池 | **5,100mAh**，Type-C 充电（DC5V ≥1A），支持电池+电源+太阳能（选配 TL-S08W 8W 板）三种供电 |
| 工作模式 | **全功耗 / 人体红外感应（PIR）/ AOV 全时录像 / 待机** 四种，可自定义定时切换 |
| AOV 机制 | 每隔固定时间间隔自动唤醒抓图，算法侦测到事件时自动录像 |
| 续航（官方实测推算） | **PIR 模式 40–45 天；AOV 模式 9–10 天** |
| 低功耗技术 | 芯片级深度休眠（毫瓦级）、电路级断电（1.8V 外设分支休眠断电）、存储级加速（Flash 读取翻倍）、DC-DC 效率 >90% |
| 检测 | 1.5T 算力，AI 人/车识别；精密 PIR 透镜；毫秒级响应、出图时间缩短 96% |
| 网络 | 内置双 SIM（联通/电信双卡单待）、4G 免配置无限流量套餐；IP65；-10~45℃ |
| 价格 | 官网未标价；京东/淘宝渠道实时价公开渠道不可得（未登录） |

**国行 TL-IPC642XL-A4GY-S10C58（400 万 4G 警戒全彩 AOV 太阳能球机）** [40]：

| 项目 | 数据 |
|---|---|
| 分辨率 | 400 万（2560×1440），双白光+双红外，多种夜视模式 |
| 供电 | **58Wh 三元锂电池 + 11W A 级单晶太阳能板**；支持电池辅热，充放电温度 **-20~60℃** |
| 工作模式 | 全功耗 / 全时录像（AOV）/ 待机三种，手动或定时自动切换 |
| AOV 机制 | **默认低帧率录像，识别人车后进入标准帧率全功耗运行，人车离开后恢复低帧率** |
| 续航 | **连续阴雨天续航 5~7 天**（官方口径） |
| 价格 | 官网未标价（公开渠道不可得） |

**Tapo（国际版）"24/7 Capture"——电池机上的 AOV 实现**（官方 FAQ，2025-05 发布、2026-07 更新）[41]：
- 机制：按设定间隔连续快照（缩时回放），检测到运动/事件切换正常帧率录像（**以 Tapo C460 为例，事件录像 15fps**）；需 SD 卡或 Hub（H200/H500）本地存储，云存储不支持；
- 检测距离：24/7 Capture（图像差分检测）**人形最远 15m、车辆 30m+**，对比 PIR 约 9m；
- 抓拍间隔与续航（官方实验室：每天 23 次白天 + 12 次夜间事件、每次 13s 录像，其余时间待机，无太阳能板）：

| 抓拍间隔 | 满电续航 | 支撑一天所需太阳能充电时间 |
|---|---|---|
| 1s | 8 天 | 105 分钟 |
| 5s | 25 天 | <45 分钟 |
| 10s | 37 天 | <45 分钟 |
| 20s | 42 天 | <45 分钟 |
| 30s | 51 天 | <45 分钟 |
| 60s | 55 天 | <45 分钟 |

- 高频抓拍（1/3s、1/5s）夜间自动降为 1fps 防过热；Adaptive 模式可按电量自动调频（Quality First/Balanced/Battery Saver/Custom）；低电量自动关闭 24/7 Capture；
- 存储占用：10s 间隔约 173MB/天；1s 间隔约 1730MB/天（1s 间隔时 16GB 卡约存 9 天、512GB 约 294 天）。
- 代表机型 **Tapo C460**（电池户外机）：4K/8MP，**10,000mAh 电池，官方宣称单次充电最长 200 天**（标准测试口径），免费 AI 人/宠物/车检测，PIR 灵敏度 1–10 级，支持 Tapo 太阳能板 [42]；售价公开渠道不可得（区域官网未标价）。

### 5.3 小米

**小米智能太阳能摄像机 4 Pro 4G 双摄版（2026-07 上架）** [43]：

| 项目 | 数据 |
|---|---|
| 价格 | **¥649**（此前众筹价 ¥579） |
| 电池/供电 | **9,900mAh** 大容量电池 + **7.6W** 太阳能板，无需外联电源 |
| 摄像头 | 双 500 万（每颗 3K 超清），f/1.6 大光圈；双白光灯+双红外灯，夜间人形自动补光 |
| AOV 机制 | **AOV 智能录制：无人时自动降至 2 秒 1 帧缩时录影（宣称节约存储 90% 以上），有人时恢复正常录制速度**；智能帧率调节 |
| 续航 | 满电续航 1 周以上（官方口径，未注明测试条件） |
| 网络 | 内置双 4G SIM 卡、免费流量、免 Wi-Fi |

**小米室外摄像机电池版（2021，老款，对比用）** [44][45]：1080p，PIR 事件触发（非 AOV）；官方口径**续航 90 天**（测试条件：白天触发 10 次 + 夜间触发 10 次、每次 15 秒）；IP65；夜视 7m；上市价 ¥349；电池容量官网未公布（公开渠道不可得，第三方拆解文章称与可视化门铃同源方案）。

### 5.4 360（奇虎）

**结论：360 当前公开产品线未发现 AOV/全时录像电池摄像机**。官网摄像机线（小水滴 AI 版、云台 AI 版、云台变焦版、红色警戒、可视门铃等）均为常电产品 [46]。其电池产品为：

**360 电池摄像机 BC60（4G 双目版）** [47][48]：

| 项目 | 数据 |
|---|---|
| 价格 | **¥299**（360 商城，指导价 ¥379；第三方渠道促销价曾低至 ¥155–190【软广/低可信，smzdm 用户实测口径】） |
| 摄像头 | 双 300 万像素镜头，192° 超广角，夜视 8m |
| 电池 | **3,200mAh** 内置锂电 |
| 录像模式 | 触发录制为主：**官方口径连续录制约 5 小时；触发模式（每天 20 次、每次 10s）约 18 天**；未宣传 AOV 缩时全时录像 |
| 网络 | 自带 4G 流量卡"终身流量 0 自费"，免 Wi-Fi；磁吸/3M 胶安装 |

### 5.5 乐橙 Imou（大华消费品牌）

**乐橙 B7E-AOV 智能电池相机（2025-03/04 发布，乐橙首款 AOV 电池机）** [32][49]：

| 项目 | 数据 |
|---|---|
| 摄像头 | 500 万像素，智能夜视，24h 高清记录 |
| 电池/太阳能 | **10,000mAh** + **5W ETFE 太阳能板**（透光率 >90%、能效转化 23%+；微光/阴雨天日补电约 11%，晴天光照 2 小时补电 ≥15%） |
| AOV 机制 | **无人时每 2 秒抓 1 张图（缩时），检测到人立即正常录像**，形成"缩时+事件"融合的 24 小时录像（可回看事件前画面）；相同条件下比传统 5MP 相机连续录像**节省约 30 倍存储** |
| 续航 | **AOV 模式下即使每天 100 次事件，日耗电仅约 10%，可度过 10 个连续阴天**；自带辅热、自研低温充电技术 **-10℃ 以下仍可太阳能充电** |
| 检测 | **AI 人形检测替代 PIR**：有效距离 10m → **30m**，准确率 **99%** |
| 网络 | Wi-Fi + 4G（断 Wi-Fi 自动切 4G），4G 终身免流 |
| 价格 | 京东在售（500 万/1 万 mAh/5W 太阳能板 + 64G 卡配置），页面价格需登录（公开渠道不可得） |

**IMOU AOV Dual（国际版，双摄 4G+Wi-Fi）** [50]：

| 项目 | 数据 |
|---|---|
| 摄像头 | 双 5MP+5MP |
| AOV 机制 | **无事件时每 3 秒录 1 帧省电省存储，事件发生时立即切换全帧率录像**（"industry-leading Always-on Video (AOV) technology"官方措辞） |
| 电池 | **10,000mAh + 太阳能**（官方称"Unlimited Battery Life"） |
| 检测 | AI 人形/车辆检测，**25m 检测距离**；人形触发自动切全彩夜视 |
| 低温 | 支持 **-15℃ 低温充电** |
| 存储 | AOV 无事件模式下：32GB 卡存 15–20 天 / 64GB 30–40 天 / 128GB 70–80 天 / 256GB 150–160 天 / 512GB 300–310 天 |
| 4G 流量 | 官方口径：每天预览 5 次+回放 5 次（各 1 分钟）约消耗 166MB/天 |
| 价格 | 公开渠道不可得 |

**IMOU AOV PT 4K（国际版 4G/Wi-Fi 云台）** [51]：8MP（3840×2160）1/3" CMOS，3.6mm F1.6（105° 对角），云台 340°/90°，夜视 20m，最高 15fps；**15,000mAh 可充电池**；AOV 模式 + 人形/车辆检测；整机功耗 **<3.5W**（官方规格页口径，未注明工况）；DC5V2A 或 Imou 太阳能板供电；价格公开渠道不可得。

### 5.6 觅睿 Meari

**Meari Cam V1（4G AOV 电池云台机）** [52][53]：

| 项目 | 数据 |
|---|---|
| 定位 | "无网无电，24 小时不间断守护"；官方海外社媒明确称其为 "Smart 4G **AOV** Battery Camera V1"，主打全彩夜视 + 7×24h 连续录像 |
| 电池/供电 | **10,400mAh** 内置电池 + 太阳能充电 + 4G |
| 摄像头 | 300 万像素，云台 360° 水平 / 90° 垂直 |
| 检测 | AI 人形检测（可分析 **30m** 外人体），自定义运动区域 |
| 夜视 | 双 LED 聚光灯全彩夜视 |
| 防护/存储 | IP65；SD 卡本地 + 云存储双模式 |
| 价格 | 海外渠道（孟加拉等）有售，具体售价页面 JS 渲染未获取到（公开渠道不可得） |
| 芯片关联 | 行业报道称北京君正 T41 系列"全时录像"电池 IPC 芯片助力**觅睿**等客户实现百万级出货 [24]（觅睿官方未公开确认 V1 具体芯片方案） |

### 5.7 参照系：海康威视 AOV 超低功耗 4G 球机（a&s 安防知识网实测，2025-02）[29]

AOV 品类定义者（海康首款 AOV 太阳能 4G 球机），实测数据最完整，作为国产 AOV 技术基准收录：

| 项目 | 数据 |
|---|---|
| 摄像头 | 400 万 + F1.2 大光圈，红外/白光双补光，24h 全彩；0.1Lux+补光实测照射 18m（官方口径夜间补光 20–25m） |
| AOV 机制 | **无事件 1 帧/秒定时抓拍；检测到人/车切换 12.5 帧/秒正常录像** |
| 低功耗设计 | 深度定制低功耗控制系统：较上一代**低功耗性能提升 46%、功耗降低 30%**；**DDR 自刷新**降低无事件工作功耗；低功耗传感器**单次抓拍 <100ms**、较传统传感器功耗再降 10%+；低功耗 4G 模组（分布式架构）；SoC 软件层多系统协同实现 AOV |
| 电池/太阳能 | **32Wh 车用级三元锂电池 + 8W 单晶硅太阳能板**（光伏板功率较上代 +23%、电池片转换效率 +5%）；Type-C 可拆卸电池快充 |
| 续航 | 官方：**连续 7 个阴雨天**正常续航（口径：每日报警 50 分钟+预览 10 分钟）；第三方实测：不接太阳能、室内 13–20℃、日均触发 5–6 次报警，**3 天电量 58% → 12%**（约 15%/天，推算 6–7 天） |
| 检测 | 前端抓图 + AI 检测：**25m** 检测距离（传统 PIR <10m）；人/车识别准确率 **98%+**（15m 实验室口径）；可订阅云端 22 种情景算法（车型识别、安全帽、抽烟等） |
| 存储 | 本地 TF 卡；**AOV 模式下存储卡利用率达传统全时录像机的 5 倍**（官方实验室口径） |
| 价格 | 官方渠道未获取；【软广/低可信】CSDN 选型文称海康旗舰户外套装均价 ¥800–1200、太阳能 4G 款接近 ¥1500 [54] |

## 6. 国际品牌（Ring / Arlo / Wyze / Eufy）

**总体结论：四大国际品牌的电池摄像头均为事件触发录像（PIR/雷达/AI），无一采用 AOV 式"缩时全时录像"；其连续录像功能（Ring 24/7 Recording、Arlo 24/7 Recording/CVR）均要求设备接常电 + 付费订阅 + 云端存储。**

### 6.1 Ring（Amazon）

**24/7 Recording（2024-10 随 Ring Home 订阅改版推出）** [55][56]：
- 连续录制音视频（云端），**仅限接常电设备**（hardwired / plugged in / PoE）：Floodlight Cam 系列、Indoor Cam、Outdoor Cam 系列、Spotlight Cam 系列、Stick Up Cam Pro、Wired Doorbell 4K 等约 20 款——**所有电池供电型号不支持**；
- 需最高档订阅 **Ring Home Premium**（原 Ring Protect Pro，$19.99/月）；云端保存最长 **14 天**；单地点最多 **10 台**设备；
- Ring Elite 系列为独立附加订阅：$6–18/月/台（按视场角分档，仅美国）；
- 对比：Google Nest 连续录像需 Nest Aware Plus（约 $15/月）且同样限常电设备 [56]。

**电池产品现状（代表机型 Outdoor Cam Plus, Battery，原 Stick Up Cam Pro Battery）** [57][58]：
- $99.99；"Retinal 2K" 低照增强 2K 视频、宽视场；电池/插电/太阳能/有线/PoE 多供电形态；
- 录像为**运动事件触发**（motion-activated notifications），无本地连续录像；事件云录像需 Ring Home 订阅（PCMag 评测提及需额外预算约 $49.99/年的订阅费用 [58]）；
- 电池容量与续航数值官方不公布（公开渠道不可得；Ring 官方口径历来为"取决于使用频率"）。

### 6.2 Arlo

**24/7 Recording（原 CVR，连续录像）** [59]：
- 官方 KB 明确：**"Arlo cameras must be plugged into AC power to support 24/7 Recording"（必须接交流常电）**；每地点最多 **3 台**；需 **Arlo Secure Premium with 24/7 Recording** 订阅；云端连续录像保存 **30 天**、不支持下载；Ultra/Pro 系列还需 SmartHub 基站；上传带宽要求 2–3Mbps/台；门铃类不支持。
- 支持机型（接电时）：Ultra/Ultra 2/Ultra 4K(3rd Gen)、Pro 2–Pro(6th Gen)、Pro 3 Floodlight、Essential 室内系列等。

**电池产品线（美国官网现价，2026-09）** [60][61]：

| 型号 | 定位/规格 | 价格 | 电池 |
|---|---|---|---|
| Arlo Pro 6（6th Gen） | 2K HDR、160° 视场、双频 Wi-Fi、**可换电池** | $159.99（原 $229.99） | 容量未公布；官方估计单次充电约 **8 个月**（媒体转述，随使用而变）；有低电量模式 |
| Arlo Pro XL 6（6th Gen） | 同 Pro 6，2 倍电池续航 | $199.99 | 未公布 |
| Arlo Essential（3rd Gen）电池版 | 2K、130° 视场、彩夜 | $89.99（原 $129.99） | 未公布 |
| Arlo Essential XL（3rd Gen） | 4 倍电池续航 | $139.99（原 $219.99） | 未公布 |
| Arlo Ultra（3rd Gen） | 4K HDR、180°、自动变焦追踪、可换电池 | $279.99（原 $349.99） | 未公布 |
| Arlo Go 2 | Wi-Fi/LTE、microSD | $159.99 | 未公布 |
| 太阳能板配件 | 通用 | $39.99 | — |

录像模式：电池机型均为 PIR+AI 事件录像（订阅 Arlo Secure 后云端事件录像）；无缩时全时录像功能。

### 6.3 Wyze

**Wyze Battery Cam Pro（2024-08 发布）** [62]：

| 项目 | 数据 |
|---|---|
| 价格 | **$89.98**（1 台装；多台面装/含配件套装价 $107.98–$159.98 区间，页面未明确对应关系） |
| 电池 | **6,200mAh 可拆卸电池包**（备用电池 $22.99、双充底座 $23.98），充电约 9 小时；官方宣称**续航最长 6 个月** |
| 摄像头 | 2.5K QHD（2560×1440）星光 CMOS，F1.6，134° 对角视场，8x 数码变焦，H.264，昼/夜均 15fps |
| 检测/唤醒 | **雷达 + PIR 双传感器**（更早、更准的运动检测），自定义检测区域；Cam Plus AI 检测（人/包裹/车辆/鸟） |
| 录像模式 | **事件录像**：microSD 本地事件录像（最大 256GB，官方注明"本地录像会影响续航"）+ Cam Plus 云事件录像（$2.99/月/台，14 天）；**电池机不支持连续录像**（Wyze 的连续录像/缩时功能仅见于常电 Cam 系列的 SD 卡功能描述） |
| 其他 | 150 流明聚光灯+100dB 警报器、IP65、双频 Wi-Fi、免 Hub、太阳能板（$28.98）可选 |

### 6.4 Eufy（Anker）

**eufyCam S3 Pro（2024 年底发布的旗舰电池机）** [63][64][65]：

| 项目 | 数据 |
|---|---|
| 价格 | **单机（Add-on）$219.99**；4 台套装+1TB 硬盘 $879.99；4 台套装+HomeBase Professional S1 $1,379.99 |
| 电池 | **13,000mAh**；官方宣称 **365 天续航**（脚注口径：内部实验室测试；官方另注明"平均使用下一天一夜耗电 100–200mAh"） |
| 太阳能 | SolarPlus™ 2.0：内置太阳能板（最佳日照日收集 450–900mAh/天），可外挂扩展板；2,500lx 光照即开始充电；工作温度 -10~45℃ |
| 摄像头 | 4K（3840×2160）1/1.8" 堆栈式 CMOS、F1.0、135° 视场、8x 数码变焦、MaxColor Vision™ AI-ISP 全彩夜视（无需补光，识别人脸/车牌至 30ft/9m）、4 颗 IR LED（10m）、H.264/H.265、最高 15fps |
| 检测/唤醒 | **雷达 + PIR 双检测**，官方称误报减少 99%；人脸识别（BionicMind，HomeBase 本地） |
| 录像模式 | **事件录像**（本地 HomeBase 存储、免月费）；**不支持连续录像**（eufy 社区官方答复与用户反馈一致 [65]；eufy 官网"Continuous Recording"合集实际对应常电机型如 Indoor Cam/E330 等，S3 Pro 被列入属营销归类） |

**对比参考（Eufy 常电线）**：eufy 的 24/7 连续录像能力在有线产品（如 eufyCam E330、Indoor Cam 24/7 系列）上提供，电池线未跟进。

### 6.5 国内外产品指标对比总表

**国内 AOV 类电池摄像机：**

| 产品 | 电池 | 分辨率/事件帧率 | AOV 低帧率策略 | 检测机制（距离） | 续航宣称 | 价格 |
|---|---|---|---|---|---|---|
| 萤石 HB8 Lite 4G | 5,200mAh | 2K+ / 15fps | 间隔抓拍缩时 + 事件全速（AOV 2.0） | AI 人车图像检测（日 25m/夜 12m） | 未公布 | 不可得 |
| 萤石 HB8 4G 800 万套装 | 不可得 | 800 万 | AOV 模式 | AI+全彩夜视 | 不可得 | ¥499（含太阳能板） |
| 萤石 CB2 | 2,000mAh | 1080p / 15fps | 国内渠道标 AOV 模式（细节不可得） | PIR+人形 | 50 天（5 分钟/天） | ¥329–339 |
| 萤石 CB60 | 2,600mAh | 双 400 万 | AOV 全天录像+延迟摄影 | PIR 抓拍 | 不可得 | 不可得 |
| TP-LINK TL-IPC16B-F4GE | 5,100mAh | 600 万 | 间隔抓图+事件录像（AOV 模式） | 1.5T AI 人车+PIR | AOV 9–10 天 / PIR 40–45 天 | 不可得 |
| TP-LINK AOV 太阳能球机 | 58Wh | 400 万 | 低帧率↔人车标准帧率 | AI 人车 | 阴雨 5–7 天 | 不可得 |
| Tapo C460（国际） | 10,000mAh | 4K / 15fps | 24/7 Capture：1–60s 间隔快照缩时 | AI 人/宠/车 + PIR（人 15m/车 30m+） | 200 天（标准口径）；1s 间隔 AOV 8 天、60s 间隔 55 天 | 不可得 |
| 小米太阳能摄像机 4 Pro 4G | 9,900mAh + 7.6W 太阳能 | 双 500 万 3K | 无人 2s/帧缩时（省存储 >90%） | AI 人形（自动补光） | 满电 1 周+ | ¥649 |
| 360 BC60（非 AOV） | 3,200mAh | 双 300 万 | 无 AOV；触发式 | PIR/AI | 连录 5h；触发 18 天 | ¥299 |
| 乐橙 B7E | 10,000mAh + 5W 太阳能 | 500 万 | 2s/帧缩时 + 事件全速 | AI 人形 30m（99%） | 日耗电约 10%（100 事件/天）；10 个阴天 | 不可得（需登录） |
| 乐橙 AOV Dual（国际） | 10,000mAh + 太阳能 | 双 5MP | 3s/帧 + 事件全帧率 | AI 人车 25m | "无限续航"（太阳能口径） | 不可得 |
| 乐橙 AOV PT 4K（国际） | 15,000mAh | 8MP / 15fps | AOV 模式 | 人车检测 | 不可得；整机功耗 <3.5W | 不可得 |
| 觅睿 V1 | 10,400mAh + 太阳能 | 300 万云台 | AOV 7×24（官方社媒口径） | AI 人形 30m | 不可得 | 不可得 |
| 海康 AOV 4G 球机（参照） | 32Wh + 8W 太阳能 | 400 万 / 12.5fps | 1fps 定时抓拍 + 事件 12.5fps | AI 人车 25m（98%+） | 7 个连续阴雨天；实测约 15%/天 | ¥800–1500【低可信】 |

**国际品牌电池摄像机（均事件式）：**

| 产品 | 电池 | 分辨率/帧率 | 录像模式 | 检测机制 | 续航宣称 | 价格 |
|---|---|---|---|---|---|---|
| Ring Outdoor Cam Plus (Battery) | 未公布 | 2K | 事件云录像（订阅） | 运动检测 AI | 未公布 | $99.99 + 订阅 |
| Arlo Pro 6 | 未公布（可换） | 2K HDR | 事件录像（订阅云端） | PIR+AI | 约 8 个月（官方估计口径） | $159.99 |
| Arlo Ultra 3rd Gen | 未公布（可换） | 4K HDR | 事件录像 | PIR+AI 自动追踪 | 不可得 | $279.99 |
| Wyze Battery Cam Pro | 6,200mAh（可拆） | 2.5K / 15fps | 事件录像（microSD/云） | **雷达+PIR** | 最长 6 个月 | $89.98 |
| eufyCam S3 Pro | 13,000mAh | 4K / 15fps | 事件录像（HomeBase 本地） | **雷达+PIR**（-99% 误报） | 365 天（实验室口径） | $219.99（单机） |

> 国际品牌连续录像（CVR/24-7）横向对比：Ring 24/7 Recording = 常电 + Ring Home Premium（$19.99/月）+ 云 14 天 [55][56]；Arlo 24/7 Recording = 常电 + Secure Premium 订阅 + 云 30 天 + ≤3 台/地点 [59]；Google Nest = 常电 + Nest Aware Plus（约 $15/月）[56]。均与电池 AOV 路线（本地缩时存储、免订阅）形成鲜明对比。

---

# 信息缺口清单（公开渠道不可得项汇总）

**芯片/传感器侧：**
1. Ambarella CV25/CV28M/S6LM/CV72S 的待机/休眠功耗具体数值（mW 级）及"低功耗岛/always-on DSP"微架构细节——官方从未公布。
2. Ambarella 各芯片 Product Brief PDF（官网旧链接已 404/迁移，新站点产品页无 PDF 下载）。
3. Sony 安防系列（STARVIS 2 / IMX675/678/908）的低功耗模式参数、待机电流——datasheet 不公开；Sony AO 模式与 IMX500 的具体功耗数值未公布。
4. 思特威 SC450AI/SC2331/SC3332 的绝对功耗数值（官方仅给相对降幅或仅 SC301HIOT 给了绝对值）。
5. 格科微 GC20C3 AOV 模式下的绝对功耗数值。
6. "Wisen"品牌与思特威的关联——未检索到任何公开关联证据。
7. AOV 电池 IPC 所用 eMCP 具体型号及待机功耗（整机 BOM 不公开）；ADI CV28 开发套件电源树文档（页面 403）。

**终端产品侧：**
8. 萤石 HB8 Lite 4G / CB60 / HB90 / HB8 4G 版的国行价格与电池容量（部分）、AOV 模式下的官方续航天数。
9. 萤石 CB2 国行"AOV 模式"的官方机制说明（仅零售渠道标题提及，官网规格未见）。
10. TP-LINK TL-IPC16B-F4GE、TL-IPC642XL-A4GY-S10C58、Tapo C460 的官方零售价（官网不标价；电商实时价需登录）。
11. 乐橙 B7E 京东实时价格（登录墙）；AOV Dual / AOV PT 4K 各区域售价。
12. 觅睿 V1 的售价与 AOV 帧率策略细节（官网产品页无功耗/帧率参数）。
13. 小米太阳能摄像机 4 Pro "满电续航 1 周+"的测试条件口径。
14. 360 是否有未上架官网的 AOV 产品（现有公开渠道未发现）。
15. Ring/Arlo 电池机的电池容量 mAh（两家官方均不公布）；Ring Outdoor Cam Plus 电池续航官方数值（Ring 仅给"取决于使用"口径）。
16. Wyze Battery Cam Pro"6 个月续航"与 eufy S3 Pro"365 天续航"的具体测试条件全文（官网仅脚注简述）。
17. 海康威视 AOV 4G 球机的官方定价（官网商城未检索到公开标价；仅有低可信软文口径 ¥800–1500）。

---

# 参考资料

一手来源（官方）：
1. Ambarella Technology（CVflow / Low power）：https://www.ambarella.com/technology/ （访问 2026-09-10）
2. Ambarella S2Lm 电池 IP 相机参考设计新闻稿（2015）：https://cn.ambarella.com/news/ambarella-s2lm-battery-powered-ip-camera-reference-design-enables-new-generation-of-wire-free-security-cameras/ （访问 2026-09-10）
3. Ambarella CV2 发布稿（2018-03-28）：https://investor.ambarella.com/news-releases/news-release-details/ambarella-introduces-cv2-4k-computer-vision-soc-cvflowtm （访问 2026-09-10）
4. Rhonda Software《How to choose an Ambarella CVflow SoC for your camera》（第三方功耗汇总）：https://www.rhondasoftware.com/how-to-choose-an-ambarella-cvflow-soc-for-your-camera-2/ （访问 2026-09-10）
5. Ambarella CV25 发布稿（2019-01-07）：https://investor.ambarella.com/news-releases/news-release-details/ambarella-introduces-cv25-soc-cvflowtm-computer-vision-enable （访问 2026-09-10）
6. Ambarella S6LM 发布稿（2019-04-08）：https://investor.ambarella.com/news-releases/news-release-details/ambarella-introduces-s6lm-soc-latest-imaging-technology （访问 2026-09-10）
7. Ambarella CV28M 发布稿（2020-11-02）：https://investor.ambarella.com/news-releases/news-release-details/ambarella-introduces-cv28m-soc-cvflowr-enable-new-categories （访问 2026-09-10）
8. Ambarella CV5 发布稿（2021-01-11）：https://investor.ambarella.com/news-releases/news-release-details/ambarella-introduces-cv5-high-performance-ai-vision-processor （访问 2026-09-10）
9. Ambarella 安防产品页（CV22S/CV25S/CV28M/CV52S/CV5S/CV72S/CV75S/S6LM 等）：https://www.ambarella.com/products/security/ （访问 2026-09-10）
10. Ambarella CV72S 发布稿（2023-03-21）：https://www.ambarella.com/news/ambarella-launches-4k-5nm-edge-ai-soc-for-mainstream-security-cameras-with-new-highs-in-ai-performance-per-watt-image-quality-and-sensor-fusion/ （访问 2026-09-10）
11. Ambarella CV7 发布稿（2026-01-05）：https://www.ambarella.com/news/ambarella-launches-powerful-edge-ai-8k-vision-soc-with-industry-leading-ai-and-multi-sensor-perception-performance/ （访问 2026-09-10）
12. NXP AN13272《Power Management Solution for CV22/CV25》：https://www.nxp.com/docs/en/application-note/AN13272.pdf （访问 2026-09-10）
13. ADI CV28 Development Kit Circuit Note（403 受限，未能读取）：https://www.analog.com/en/resources/reference-designs/circuits-from-the-lab/cv28-dk.html （访问 2026-09-10）
14. Sony Semiconductor《Always-on》技术页：https://www.sony-semicon.com/en/technology/mobile/always-on.html （访问 2026-09-10）
15. Sony IMX500 智能视觉传感器发布稿（2020-05-20）：https://www.sony.com/en/SonyInfo/News/Press/202005/20-037E/ （访问 2026-09-10）
16. Sony 安防图像传感器产品页：https://www.sony-semicon.com/en/products/is/security/security.html （访问 2026-09-10）
17. Sony IMX908 4K LOFIC 安防传感器发布（2026-04，PRNewswire）：https://www.prnewswire.com/news-releases/sony-semiconductor-solutions-to-release-4k-image-sensor-for-security-cameras-with-the-industrys-smallest-1-45-m-lofic-pixels-302712099.html （访问 2026-09-10）
18. Wisen Innovation（悟莘科技，与思特威无关的佐证检索）：https://www.wisencn.com/gyws_en （访问 2026-09-10）
19. 思特威 SC301HIOT 官方新闻（SmartAOV™，<40mW@1fps，~100mW@30fps）：https://www.smartsenstech.com/mpage?id=273 （访问 2026-09-10）
20. 思特威 SC450AI 官方新闻：https://www.smartsenstech.com/mpage?id=141 （访问 2026-09-10）
21. 思特威 SC2331/SC3332 官方新闻（工作功耗 -49%/-32%）：https://www.smartsenstech.com/mpage?id=192 （访问 2026-09-10）
22. 格科微 GC20C3 发布报道（EET-China，2025-06-06，官方通稿转载）：https://www.eet-china.com/mp/a410283.html （访问 2026-09-10）
23. 大联大诠鼎 AOV 摄像头方案（NT98568+SC450AI，EET-China）：https://www.eet-china.com/mp/a355820.html （访问 2026-09-10）
24. 安防资讯网《安防 IPC 芯片站在"技术+场景"风口》（2025-09-01，国科微/瑞芯微/君正/星宸/富瀚微/海思 AOV 芯片生态与市场规模）：https://www.anfangnews.com/2025/0901/13063.shtml （访问 2026-09-10）
25. 安凯微 AOV 低功耗智能视觉芯片公告（2025-04-02，PDF）：http://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESH_STOCK/2025/2025-4/2025-04-02/10840696.PDF （访问 2026-09-10）
26. Micron 博客《Ambarella selects Micron for next gen edge AI perception SoC platform》（CV5 LPDDR5/5X 验证、eMMC/i300/Xccela）：https://in.micron.com/about/blog/company/partners/ambarella-selects-micron-for-next-gen-edge-ai-perception-soc-platform （访问 2026-09-10）
27. 知乎《芯科普 | 一文了解存储主流配置 eMCP》：https://zhuanlan.zhihu.com/p/14110036059 （访问 2026-09-10）
28. EET-China《DDR、LPDDR、eMMC、UFS - uMCP 存储器的区别》：https://www.eet-china.com/mp/a264852.html （访问 2026-09-10）
29. a&s 安防知识网《全天候监控新选择，实测海康威视 AOV 超低功耗 4G 球机》（2025-02）：https://www.asmag.com.cn/test/202502/70966.html （访问 2026-09-10）
30. TP-LINK 官方产品页 TL-IPC16B-F4GE（600 万 4G 电池网络摄像机，规格参数）：https://www.tp-link.com.cn/m/product_4189.html?v=specification （访问 2026-09-10）
31. 安防资讯网《2025 年安博会，AOV 摄像机的群像时刻》（2025-11-06）：https://www.anfangnews.com/2025/1106/13302.shtml （访问 2026-09-10）
32. 中国安防大数据服务平台《实测乐橙智能电池相机，AOV 低功耗模式》（B7E，2025-03-27）：https://www.afdata.org.cn/CuttingEdge/444bd73e-9166-41a9-a693-e3020332e35d （访问 2026-09-10）
33. EZVIZ HB8 Lite 4G 官方产品页（AOV 2.0、5200mAh、25m/12m 检测）：https://www.ezviz.com/product/hb8+lite+4g/68027 （访问 2026-09-10）
34. 萤石官网新品页（HB90/CB60 AOV 2.0 描述、AOV 2.0 技术说明）：https://www.ezviz.com/cn/news/6412.html （访问 2026-09-10）
35. 萤石官方商城 HB8 室外云台 4G 电池摄像机 800 万（¥499，AOV 模式）：https://m.ys7.com/item/900879.html （访问 2026-09-10）
36. 萤石官方商城 CB2 室内全无线电池摄像机（¥339 起、50 天续航、详细参数）：https://m.ys7.com/item/596276.html （访问 2026-09-10）
37. EZVIZ CB2 全球官网产品页（2000mAh、50 天口径、PIR+人形）：https://www.ezviz.com/product/cb2/47560 （访问 2026-09-10）
38. EZVIZ HB8 全球官网产品页（10400mAh、210 天、32GB eMMC）：https://www.ezviz.com/product/hb8/40825 （访问 2026-09-10）
39. 中国安防大数据服务平台《TP-LINK 推出全新 TL-IPC16B-F4GE 4G 电池网络摄像机》（2025-12-12，AOV 9–10 天/PIR 40–45 天续航、四大低功耗技术）：https://www.afdata.org.cn/CuttingEdge/ac7cf395-7574-4a9d-9fc9-bc538d2167a1 （访问 2026-09-10）
40. TP-LINK 官方产品页 TL-IPC642XL-A4GY-S10C58（400 万 4G 警戒全彩 AOV 太阳能球机）：https://www.tp-link.com.cn/m/product_3875.html （访问 2026-09-10）
41. TP-Link 官方 FAQ《How to Enable 24/7 Capture on Tapo Battery-Powered Cameras》（2025-05-19 发布/2026-07 更新）：https://www.tp-link.com/us/support/faq/4462/ （访问 2026-09-10）
42. Tapo C460 官方产品页（4K、10000mAh、200 天）：https://www.tp-link.com/ph/home-networking/cloud-camera/tapo-c460/ （访问 2026-09-10）
43. IT之家《小米智能太阳能摄像机 4 Pro 4G 双摄版上架：免费流量、免装网线，649 元》（2026-07-17）：https://www.ithome.com/0/978/124.htm （访问 2026-09-10）
44. 小米香港官网 小米室外摄像机（电池版）规格页（90 天续航测试口径、IP65、7m 夜视）：https://www.mi.com/hk/product/mi-wireless-outdoor-security-camera-1080p/ （访问 2026-09-10）
45. 凤凰网《小米室外摄像机电池版开箱评测：90 天长续航，仅 349 元》：https://i.ifeng.com/c/85xBjyAm5ao （访问 2026-09-10）
46. 360 智慧生活官网产品列表：https://jia.360.cn/list.html （访问 2026-09-10）
47. 360 商城 电池摄像机 BC60（4G 双目版）商品页（¥299）：https://m.mall.360.cn/shop/item?item_id=68a41e982859c61962e3b028 （访问 2026-09-10）
48. 什么值得买《155 元的双目摄像机……》（BC60：双 300 万、3200mAh、连录 5h/触发 18 天，2026-01-12）：https://post.smzdm.com/p/avvznlvm （访问 2026-09-10）
49. 中华网科技《0 电费 0 网费还能全时录像！乐橙创新省心科技》（B7E-AOV，2025-04-09）：https://m.tech.china.com/articles/20250409/202504091658367.html （访问 2026-09-10）
50. IMOU AOV Dual 官方产品页：https://new.imoulife.com/en/product/detail/aov-dual （访问 2026-09-10）
51. IMOU AOV PT 4K 官方规格页：https://www.imou.com/en/product/specs/aov-pt4k （访问 2026-09-10）
52. 觅睿官网 Meari Cam V1 产品页（10400mAh、3MP 云台、AI 人形 30m、IP65）：https://www.meari.com/zh/products/V1 （访问 2026-09-10）
53. Meari 官方 Facebook《Meet the Smart 4G AOV Battery Camera V1》：https://www.facebook.com/MEARITechnology/photos/727695936454799/ （访问 2026-09-10）
54. 【软广/低可信】CSDN《AOV 低功耗监控摄像机哪家好？6 大主流安防厂家选型指南》（2026-06-03；海康/大华/TP-LINK/乐橙/中维/Reolink 横评与价格口径）：https://www.csdn.net/article/2026-06-03/161662818 （访问 2026-09-10）
55. Ring 官方支持文档《24/7 Recording》（适用机型限常电、云 14 天、≤10 台、Elite 附加订阅 $6–18/月）：https://ring.com/support/articles/wtr7r/24-7-recording-security-cams （访问 2026-09-10）
56. The Verge《Ring is finally adding 24/7 recording to its security cameras》（2024-10-02，Ring Home Premium 要求、与 Nest/Arlo 对比）：https://www.theverge.com/2024/10/2/24259779/ring-24-7-continuous-recording-smart-security-cameras （访问 2026-09-10）
57. Ring Outdoor Cam Plus 官方产品页（$99.99、多供电形态）：https://ring.com/products/stick-up-cam-pro-battery （访问 2026-09-10）
58. PCMag《Ring Outdoor Cam Plus Review》（2026-06-16）：https://www.pcmag.com/reviews/ring-outdoor-cam-plus （访问 2026-09-10）
59. Arlo 官方 KB《What is Arlo 24/7 Recording and how do I use it?》（必须接 AC 常电、≤3 台/地点、云 30 天、Secure Premium 订阅）：https://kb.arlo.com/000063692/What-is-Arlo-24-7-Recording-and-how-do-I-use-it （访问 2026-09-10）
60. Arlo 美国官网产品线与价格（Pro 6/XL、Essential 3rd Gen/XL、Ultra 3rd Gen、Go 2、太阳能板）：https://us.arlo.com/products/arlo-pro-6 （访问 2026-09-10）
61. T3《Arlo Pro 6 review》（官方估计约 8 个月续航、2560×1440、低功耗模式）：https://www.t3.com/home-living/smart-home/arlo-pro-6 （访问 2026-09-10）
62. Wyze Battery Cam Pro 官方产品页与技术规格（$89.98、6200mAh 可拆电池、最长 6 个月、雷达+PIR、2.5K/15fps、microSD 事件录像）：https://www.wyze.com/products/wyze-battery-cam-pro （访问 2026-09-10）
63. eufyCam S3 Pro 官方产品页（13,000mAh、365 天宣称、100–200mAh/天脚注、SolarPlus 2.0、450–900mAh/天收集）：https://www.eufy.com/products/t81621w1 及 https://www.eufy.com/eufycam-pro （访问 2026-09-10）
64. eufy 官网《Continuous Recording Security Cameras》合集（连续录像机型以常电为主）：https://www.eufy.com/eu-en/collections/continuous-recording-security-camera （访问 2026-09-10）
65. eufy 社区《S3 Pro Camera - Not recording Continously》（S3 Pro 不支持连续录像的用户/官方确认帖）：https://community.eufy.com/t/s3-pro-camera-not-recording-continously/5756412 （访问 2026-09-10）
66. 【软广/低可信】ZOL《AOV 低功耗技术实测：2026 户外监控摄像头续航横评》（格行视精灵 40mW 待机/1/3fps、萤石 CB1 高频触发约 20 天、前瞻产业研究院"AOV 机型续航平均提升 6–8 倍"等旁证数据）：https://m.zol.com.cn/diybbs/d34448_46709.html （访问 2026-09-10）
67. Wikipedia《List of Ambarella products》（芯片谱系与发布年份核对）：https://en.wikipedia.org/wiki/List_of_Ambarella_products （访问 2026-09-10）
