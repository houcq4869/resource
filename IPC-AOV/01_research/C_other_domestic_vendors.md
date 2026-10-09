# 国产 IPC/安防芯片厂商低功耗与 AOV 方案调研（除海思、君正）

> 调研范围：SigmaStar 星宸科技、瑞芯微 Rockchip、全志 Allwinner，以及安凯微、富瀚微、国科微等。
> 调研日期：2026-09-10（所有来源访问日期均为 2026-09-10，除另行注明外）。
> 说明：AOV（Always-On Video）指"休眠唤醒机制下的低帧率全天候持续录像"，事件触发时切回全帧率。本报告所有功耗数值均标注来源；无法从公开渠道获得的数据一律标注"公开渠道不可得"，不做推测。

---

## 0. 行业背景：AOV 技术代际与基准线

| 代际 | 特征 | 关键指标 | 来源 |
|---|---|---|---|
| 传统低功耗（PIR 触发） | 休眠等待 PIR 触发，事件期间才录像 | 休眠功耗 >100mW；唤醒缓冲延迟 2~3s；PIR 有效距离约 10m；触发录像存在断档 | 搜狐《AOV 3.0技术加持！低功耗IPC芯片市场风云再起》，2025-08-01，https://www.sohu.com/a/919901661_121124364 |
| AOV（1.0/2.0） | 1 秒 1 帧（或 2~3 帧）全时录像，AI 检测替代 PIR | 运行态功耗降至 ~40mW 级；全时段录像覆盖；AI 视觉侦测距离 ~30m | 同上 |
| AOV 3.0 | 融入低功耗音频事件唤醒（AOA，狗吠/玻璃破碎/枪声等） | 待机功耗低至 ~1mW；7×24 音视频监测 | 同上 |

- 市场规模：2023 年中国低功耗 IPC 市场 112.5 亿元、出货 2250 万台；2024 年 140 亿元、2800 万台（AIoT 星图研究院数据，转引自《AOV芯片大战升级！低功耗IPC赛道正在"卷"向何方？》，新领创业/物联世界，2025-08，https://www.newtid.com/4709.html）。
- 终端品牌：海康、大华、乔安、觅睿、TP-LINK（普联）等均已推出自有品牌 AOV 低功耗摄像头（同上）。
- "AOV + 4G 摄像头"为当前消费类安防核心趋势赛道（同上）。

---

## 1. SigmaStar 星宸科技（301536）

### 1.1 芯片矩阵（低功耗/电池 IPC 相关）

| 芯片 | 定位/核心 | 低功耗相关特性 | 来源 |
|---|---|---|---|
| SSC303 / SSC306 | 低功耗视觉芯片 | 典型工作功耗 300mW；支持动态降频、模块休眠；PIR 触发唤醒、待机 μA 级；支持哨兵模式/AOV 模式；4K@30fps 内存仅 27.7MB | 知乎·芯智云（代理商技术文），2026-01-30 更新，https://zhuanlan.zhihu.com/p/2000568550117631855 |
| SSC306 系列（新一代，2025-12-26 发布） | 继承 308 系主流地位的下一代低功耗 IPC 芯片 | 功耗较 308/377 系降低 60%；DRAM 消耗优化 20%~40%，800 万像素可在 64MB DDR2 落地；单系统 Linux 快速冷启动首帧 68ms（快 30%）；适配 4G AOV、可穿戴设备 | 物联网世界《800万分辨率仅需64MB内存！星宸科技306系列改写IPC芯片成本规则》，2025-12-29，https://www.iotworld.com.cn/html/News/202512/ad57c1c34687ff3d.shtml |
| SSC308DE | 电池供电 IPC SoC | 双核 Cortex-A32@1GHz（全模块满载每核 ≤75mW）+ 独立 Cortex-M4@200MHz 低功耗 IDLE 模式（面向"永远在线"应用）；内置 1Gb DDR3L；8M ISP、4K@30fps H.265 | 知乎·芯智云《基于Sigmastar SSC308DE的低功耗IP摄像头解决方案》，2025-01，https://zhuanlan.zhihu.com/p/16193465516 |
| SSC308QE | SSC308DE 高配版 | 同架构（A32 双核 + M4 低功耗核），内置 2Gb DDR3L；"独立 Cortex-M4 低功耗内核可支持始终在线的唤醒检测功能，大幅降低设备待机功耗" | 与非网·芯智云《星宸科技（Sigmastar）SSC308QE，赋能高清AI安防场景落地》，2025-08-17，https://m.eefocus.com/article/2068211.html |
| SSC30KD / SSC30KQ | 入门~中端 IPC SoC | 单核 Cortex-A7@1.2GHz（16RD 数据手册摘编口径）；"先进的低功耗、低电压架构和优化设计流程，满足长时间应用需求"；应用场景含"低功耗快启相机" | 16RD《SigmaStar 低耗能系列芯片 AI性能对比大全》，2024-12-17，https://www.16rd.com/writings-864651-1.html ；16RD 数据手册帖，2022-05，https://bbs.16rd.com/thread-587008-1-1.html |
| SSC333/335/336D/Q/338D/Q/339G | 主线 IPC 系列（非电池定位） | 内核 0.9V、IO 1.8/3.3V；低功耗低电压架构（datasheet 口径），无电池/AOV 专项营销 | 16RD《sigmastar SSC333/335/336/338/339G 全面对比》，2025-08-14，https://www.16rd.com/writings-864850-1.html |
| SSC388 | 端侧多模态大模型芯片 | 与 SSC308 低功耗方案并列为星宸 AOV 生态产品 | 《AOV芯片大战升级》，2025-08，https://www.newtid.com/4709.html |

### 1.2 低功耗技术机制

- **独立低功耗 MCU 保活**：SSC308DE/QE 内置 Cortex-M4（200MHz）支持低功耗 IDLE/始终在线唤醒检测，主核 A32 休眠时由 M4 值守（eefocus，2025-08-17）。
- **PIR 触发 + μA 级待机**：SSC303/306 支持 PIR 触发唤醒，待机功耗 μA 级（知乎·芯智云）。
- **AOV/哨兵模式**：SSC303/306 面向"低功耗+持续检测+智能唤醒"的哨兵/AOV 模式（同上）；行业综述称"星宸科技依托成熟 SDK，推出支持 AOV 等极致低功耗的芯片产品（SSC308 低功耗方案、SSC388）"（《AOV芯片大战升级》，2025-08）。
- **快启**：306 系列单系统 Linux 冷启动首帧 68ms（物联网世界，2025-12-29）。
- **电源域/动态降频/模块休眠**：SSC303/306 支持动态降频与模块休眠（知乎·芯智云）。

### 1.3 功耗指标数据表

| 指标 | 数值 | 条件/口径 | 来源 |
|---|---|---|---|
| SSC303/306 典型工作功耗 | 300mW | 典型值 | 知乎·芯智云，2026-01-30 |
| SSC303/306 待机功耗 | μA 级 | PIR 触发唤醒待机 | 同上 |
| 306 系列相对功耗 | 较 308/377 系 -60% | 官方发布会口径 | 物联网世界，2025-12-29 |
| 306 系列冷启动首帧 | 68ms | 单系统 Linux 快速冷启动 | 同上 |
| SSC308DE 单核功耗 | ≤75mW/核 | 1GHz、各模块完整状态 | 知乎·芯智云，2025-01 |
| SSC308DE/QE AOV 模式功耗（mW@fps） | 公开渠道不可得 | — | — |
| SSC30KQ 具体功耗数值 | 公开渠道不可得 | 仅"低功耗低电压架构"定性描述 | 16RD，2024-12 |

### 1.4 终端/方案案例

- 产品形态（代理商方案资料）：可视门铃/可视门锁/电子猫眼、4G 太阳能电池机/Wi-Fi 电池相机、打猎相机/执法仪/伴宠机器人、智能枪机/球机/海螺机（知乎·芯智云 SSC303/306 文）。
- SSC308DE 应用：智能门锁、门铃、猫眼、相机、动物保护相机、穿戴相机（知乎·芯智云 SSC308DE 文）。
- SSC308QE 应用：高端家用 4K 云台摄像机、低功耗电池式 4K 看护摄像头、低功耗工业安防摄像头（eefocus，2025-08-17）。

### 1.5 信息缺口

- 星宸官网（sigmastar.com.cn）产品/场景页未公开任何功耗数值与 AOV 模式参数（页面为图片+选型咨询入口，无文字规格），2026-09-10 实测确认。
- SSC30KQ 规格存在来源冲突：16RD 数据手册摘编为"单核 A7@1.2GHz、最高 3072x1728"，而 CSDN DAMO 矩阵文（2025-12-24，https://blog.csdn.net/qq_68783176/article/details/156197614）称"双核 A35@1.5GHz、1.2TOPS NPU、4K@30fps"。两者不可调和，**以官方 datasheet 为准前均不可采信**，标注为冲突待核实。
- 星宸 AOV 模式的整机功耗（mW@1fps）、唤醒时间、录像占空比策略：公开渠道不可得。
- SSC339G 官方 datasheet 全文（gitcode 镜像被反爬拦截，418）：公开渠道仅得摘编。

---

## 2. 瑞芯微 Rockchip

### 2.1 芯片矩阵

| 芯片 | 核心/算力 | 低功耗与 AOV 相关 | 来源 |
|---|---|---|---|
| RV1103 / RV1106（2022-02 发布） | Cortex-A7 + RISC-V MCU；第 4 代 NPU 0.5TOPS(int8)/1.0TOPS(int4)；ISP3.2 | "高集成度、高性价比、低待机功耗"；RISC-V MCU 支持低功耗快速启动，250ms 快速抓图并加载 AI 模型，"1 秒内"完成人脸识别；RV1103 内置 64MB DDR2（QFN88），RV1106G2 内置 128~256MB DDR3L | 官网发布稿，2022-02-17，https://www.rock-chips.com/a/cn/news/rockchip/2022/0217/1541.html ；官网产品页 https://www.rock-chips.com/a/cn/product/RV11xilie/2022/0926/1661.html 、.../1662.html |
| RV1103B / RV1106B | 单核 A7 + MCU；0.5TOPS；内置 512Mb~2Gb DDR；4K H.264/H.265 25fps；QFN88 | 官网卖点："4K 超低功耗 AI 图像处理器""高性能低内存超低功耗""支持常电、快起" | 官网产品页（2025-12-08 更新），https://www.rock-chips.com/a/cn/product/RV11xilie/2025/1208/2121.html 、.../2119.html |
| RV1126B（2025 发布） | 四核 A53 + MCU；3TOPS NPU（支持 2B 内大模型）；12M ISP / 8M AI-ISP；4K@45fps 编码 | AOV 3.0：融入低功耗音频事件唤醒（AOA），待机功耗低至 ~1mW，7×24 音视频监测；专用 AI-ISP 硬件不占 NPU | 官网产品页 https://www.rock-chips.com/a/cn/product/RV11xilie/2025/1208/2117.html ；我爱方案网，2025-11-04，https://www.52solution.com/news/80061070/ ；搜狐，2025-08-01 |

### 2.2 低功耗技术机制

- **芯片内多级功耗控制**：AOV IPC 方案"基于芯片内部多级功耗控制，使产品待机和运行功耗更低"（瑞芯微官方口径，转引自 icanic，2024-03-27，https://www.icanic.cn/news/2841.html）。
- **AOV 子系统**：深度休眠下仅 AOV 子系统+PMU 工作，摄像头 1~3fps 采集，NPU 轻量人形检测，命中后唤醒主系统；目标消失延时返回休眠（开发者实测文，CSDN·眺望电子，2026-08-07，https://blog.csdn.net/qq_33753562/article/details/163560220 ）。三档模式：正常帧率（~1280mW）/ AOV 低帧率（SOC 低帧率录像+WiFi/4G 保活，~180mW）/ 低功耗保活（SOC 下电仅 WiFi/4G 保活）；AOV 定时休眠最大支持 37 小时。
- **AI 检测替代 PIR**：自研算法同时识别人形/人脸/车辆/宠物/火焰，白天 30m、夜晚 20m 侦测唤醒（瑞芯微官方口径，icanic，2024-03-27）。
- **AOA 音频唤醒（AOV 3.0）**：RV1126B 实时检测狗吠、玻璃破碎、枪声等异常声源，待机 ~1mW（52solution，2025-11-04）。
- **休眠模式与唤醒源（开发者实践口径，非官方 datasheet）**：mem（60-80mW，GPIO/定时器/AOV 唤醒，100-300ms 恢复）/ standby（80-100mW，<100ms）/ poweroff（<10mW，仅 PMIC 唤醒，3-5s 恢复）；唤醒源限 GPIO0_A 组（CSDN《RV1106 项目实战-05》，2026-05-03，https://blog.csdn.net/lin280340404/article/details/160601716 ；该文含 AI 辅助生成标记，数值仅供参考）。
- **快启**：RISC-V MCU 快速启动，250ms 快速抓图、1s 内人脸识别（官网发布稿，2022-02-17）。

### 2.3 功耗指标数据表

| 指标 | 数值 | 条件/口径 | 来源 |
|---|---|---|---|
| RV1106G2 AOV IPC 整机功耗 | ~40mW | 一秒一帧工作状态 | 我爱方案网（瑞芯微方案口径），2025-11-13，https://news.52solution.com/news/80061168/ |
| 同方案续航 | 5200mAh 电池、无太阳天气约 14 天 | 同上 | 同上 |
| TP-LINK TL-IPC544EL-WB4GY | AOV 模式较全功耗模式功耗下降约 90% | 较少移动场景实测 | TP-LINK 安防服务公众号，转引自 52solution，2025-11-13 |
| RV1126B AOV 3.0 待机 | ~1mW | 音频事件唤醒（AOA）待机 | 52solution，2025-11-04；搜狐，2025-08-01 |
| RV1126B 整板实测 | 正常推流 1280mW / 空闲 580mW / AOV 低帧率 180mW（-86%） | 眺望电子 IPC 套件+SC450AI 摄像头，固件 260714 | CSDN·眺望电子，2026-08-07 |
| RV1126B AOV 低帧率（另一实测） | ~122mW，较正常帧率节能 90%+ | 创龙/Tronlong 实测口径 | CSDN·Tronlong，2026-06-22，https://blog.csdn.net/Tronlong/article/details/162196385 |
| RV1106 各级休眠（开发者文，参考） | 运行 200-300mW；轻休眠 80-100mW；深休眠 40-80mW；掉电 <10mW | 非官方 datasheet，AI 辅助文章 | CSDN，2026-05-03 |

### 2.4 录像占空比策略

- 无异常时 1 秒 1 帧或 1 秒 2~3 帧低帧率全时录像（"保证每一秒都有数据"，对比市面多秒一帧方案漏报率更低）；检测到人/车后进入正常录像模式（瑞芯微官方口径，icanic 2024-03-27；52solution 2025-11-13）。
- RV1126B 实测策略：检测到人形切正常帧率（60fps），连续 5 帧无人形重新进入 AOV 低帧率（Tronlong，2026-06-22）。

### 2.5 终端/方案案例

- TP-LINK TL-IPC544EL-WB4GY（RV1106G2，AOV，已上市实测，52solution 2025-11-13）。
- "RV1106G2 多款 AOV IPC 已上市、在多个知名品牌和方案商产品中量产商用"；AOV 产品系列含单目/双目 WiFi/4G 形态，"实现电池 IPC 常电化、节省 PIR 外围成本"（瑞芯微第八届开发者大会口径，ScenSmart，2024-04-08，https://www.scensmart.com/solutions/aov-ipc-solution-based-on-rv1106/ ；icanic，2024-03-27）。

### 2.6 信息缺口

- 芯片级待机电流/休眠电流官方数值：官网产品页仅有"超低功耗/支持常电、快起"定性描述，无数字（2026-09-10 实测官网 RV1106B/RV1103B/RV1126B 页）。
- RV1106 AOV 模式唤醒切换时间（低帧率→全帧率）官方数值：公开渠道不可得。
- RV1126B 的 1mW 为 AOA 音频待机口径，其视频 AOV 模式芯片级功耗：公开渠道不可得（仅有方案商整板实测 122~180mW）。
- 官网 www.rock-chip.com（无 s）域名已失效/DNS 不可解析，正确域名为 www.rock-chips.com。

---

## 3. 全志 Allwinner

### 3.1 芯片矩阵

| 芯片 | 核心/算力 | 低功耗与快启特性 | 来源 |
|---|---|---|---|
| V853 | A7@1.2GHz + RISC-V 玄铁 E907@600MHz + 1TOPS NPU；4K@15fps/5M@25fps H.265 | "可实现低功耗待机和毫秒级快速冷启动"；疾风系统：100ms 启动视觉传感器、200ms 首帧抓拍、700ms 内完成冷启动+记录+AI 检测 | 官网产品页，https://www.allwinnertech.com/index.php?c=product&a=index&id=117&solveid=40 ；官网新闻 id=344，https://www.allwinnertech.com/index.php?c=news&a=index&id=344 |
| V851s | A7@900MHz + E907@600MHz + 0.5TOPS；4M@30fps；内置 64MB DDR | "低功耗待机和毫秒级快速冷启动" | 官网产品页，https://www.allwinnertech.com/index.php?c=product&a=index&id=118 |
| V821 系列 | 双 RISC-V 异构（CPU 1~1.2GHz + MCU 600MHz）；4MP H.264；内置 64MB DDR；集成 Wi-Fi4+BLE、LDO、IRCUT、Audio Codec | Wi-Fi DTIM10 保活 180μA@4.2V；支持 AOV 低功耗方案；Tina Linux SDK 支持常电与低功耗快启模式；功耗档位：全速工作/低速 AOV 工作/WiFi 保活休眠/冬眠级待机，毫秒级冷启动抓拍 | 官网产品页，https://www.allwinnertech.com/index.php?c=product&a=index&id=136&solveid=40 ；官方社区文档，https://docs.aw-ol.com/docs/soc/v821/ ；官方发布稿（aw-ol news/162，2025-06-11；电子发烧友，2025-03-19） |
| V831 / V833 | 单核 A7@1.2GHz + 0.4TOPS NPU（官方英文 brief 口径）；5M@30fps H.265 | 2020 代 IPC SoC，无电池/AOV 专项营销；官方 brief 给出典型编码功耗 | 官方 brief PDF（2020），https://www.allwinnertech.com/uploads/pdf/20211016162024b6.pdf |

### 3.2 低功耗技术机制

- **三核异构分工**：A7 主核跑应用、RISC-V 协核负责传感器实时响应、NPU 负责视觉检测（官网新闻 id=344）。
- **疾风系统快启**（V853 平台）：软硬协同多核异构，100ms 启动 sensor / 200ms 首帧抓拍 / 700ms 完成冷启动+记录+AI 检测（官网新闻 id=344）。
- **Wi-Fi 保活休眠**：V821 集成 Wi-Fi，DTIM10 保活 180μA@4.2V；V853 方案搭配全志 μA 级保活待机 Wi-Fi 芯片 XR806（官网新闻 id=344）。
- **AOV 档位**：V821 系列明确支持"低速 AOV 工作"档位与 AOV 低功耗方案（官方社区文档 docs.aw-ol.com）。
- **内存/带宽优化**：V853 增强在线通路技术减少 40%~50% 视频处理内存占用，3K 通路带宽 <0.9GB/s（官网新闻 id=344）。

### 3.3 功耗指标数据表

| 指标 | 数值 | 条件/口径 | 来源 |
|---|---|---|---|
| V853 能效 | 每百 Gflops 算力 20mW | 官方新闻 | 官网新闻 id=344 |
| V853 3K AI 视觉典型方案整机 | <500mW | 官方新闻 | 同上 |
| V853 + XR806 可视门铃 | 2500mAh 半年以上免充电 | 官方新闻 | 同上 |
| V821 Wi-Fi 保活 | 180μA@4.2V（DTIM10） | 官网产品页/社区文档 | 官网 id=136；docs.aw-ol.com |
| V833 典型编码功耗 | 800mW | 5M30 编码典型值（官方 brief） | 官方 brief PDF |
| V851/V853/V821 AOV 模式整机功耗（mW@1fps） | 公开渠道不可得 | — | — |
| V831/V833 待机/休眠功耗 | 公开渠道不可得 | — | — |

### 3.4 终端/方案案例

- V853：智能门锁、考勤门禁、网络摄像机、行车记录仪、智能台灯（官网产品页）；2500mAh 可视门铃半年续航（官网新闻）；低功耗摄像机+太阳能"无感运维"（官网新闻）。
- V821：多目网络摄像头、低功耗门铃、智能门锁（官网产品页/社区文档）；电池供电设备（智能门锁、AI 拍学机、萌宠机器人、智能手表）为官方发布稿目标场景（aw-ol news/162）。
- 社区实践：户外野生动物监测器（电池供电、待机半年、触发录像 30s）选用 V853（CSDN 实践文，2026-08-13，https://blog.csdn.net/zzfmlxs/article/details/163724107 ，仅佐证场景，非官方数据）。

### 3.5 信息缺口

- V851/V853/V821 的 AOV 模式整机功耗、休眠电流、唤醒时间官方数值：公开渠道不可得（官方仅给出 Wi-Fi 保活电流与门铃续航结论）。
- V831/V833 已退出官网主推与社区文档（docs.aw-ol.com V833 页 404，2026-09-10 实测），低功耗资料仅存 2020 年 brief。
- "冬眠级待机"的具体电流值：公开渠道不可得。

---

## 4. 其他厂商

### 4.1 安凯微 Anyka（688620）

**芯片矩阵**

| 芯片 | 核心/规格 | 低功耗相关 | 来源 |
|---|---|---|---|
| AK3918EV200 | 32 位 RISC@400MHz；内置 512Mbit DDR2；H.264；集成 Wi-Fi+BLE5.0；QFN88 | "可在低功耗条件下实现高质量图像处理与高压缩率视频编码" | 官网，http://www.anyka.com/article/16/6.html |
| AK3918EV300L | RISC@900MHz；H.265 2304x1296；内置 512Mbit DDR2；Wi-Fi+BLE | 同上 | 官网，http://www.anyka.com/article/16/17.html |
| AK3918AV100 | ARM926EJ-S@900MHz + NPU；22nm 工艺；内置 512Mbit/1Gbit DDR2；H.265 3072x2048 | 低功耗运行条件；ICDIA 2024 强芯中国优秀产品奖 | 官网，http://anyka.com/article/17/9.html ；界面新闻，2023-09-15，https://www.jiemian.com/article/10108495.html |
| AK3918AV130 | 双核 CPU + ISP + NPU；多目低功耗协同 | **AOV 模式 2MP/1FPS 整机平均功耗仅 30mW**；上市不到一年千万颗级出货；ICDIA 2026 市场先锋奖 | 官网新闻，2026-08-20，http://anyka.com.cn/article/22/115.html |
| KM01A / KM01W | 低功耗智能视觉芯片（2025 发布） | AOV 模式整机运行功耗 <30mW（1 秒 1 帧）；应用：低功耗 AOV 摄像机、4G 太阳能低功耗物联网球机 | 《AOV芯片大战升级》，2025-08，https://www.newtid.com/4709.html |
| KM01N | — | ICDIA 2025 强芯领航奖 | 官网新闻，2026-08-20 |

**功耗指标**

| 指标 | 数值 | 口径 | 来源 |
|---|---|---|---|
| AK3918AV130 AOV 整机 | 30mW | 2MP/1FPS 平均 | 官网新闻，2026-08-20 |
| KM01A/KM01W AOV 整机 | <30mW | 1 秒 1 帧 | 行业综述，2025-08 |
| AK3918E 典型/待机 | 600mW（含 DDR2）/ 6mA@5V 待机 | 安凯方案介绍 PPT 摘编（二手） | 百度文库摘编，https://wenku.baidu.com/view/1a199fe7a2c7aa00b52acfc789eb172ded6399de.html |
| AK3918EV300 编码典型 | 300mW | H.265 1080P@15FPS 芯片本身（分销商页） | 安防展览网，2021-07-30，https://www.afzhan.com/st190735/product_12442796.html |

**案例**：卡片物联网摄像机、单目摇头机、扫码枪、智能宠物玩具（官网应用场景图）；多目摄像机/智能云台/可视门铃/USB 摄像头/监控摄像机/智能玩具（AV130 官方新闻）。

**信息缺口**：官网产品页无待机/AOV 功耗数字（仅 AV130 新闻给出 30mW）；KM01 系列官网产品页未检索到（仅新闻提及）；快启时间、唤醒源细节：公开渠道不可得。

### 4.2 富瀚微 Fullhan（300613）

**芯片矩阵**

| 芯片 | 规格 | 低功耗相关 | 来源 |
|---|---|---|---|
| MC6321 / MC6322 / MC6321L | 2-Sensor 输入，H.264&H.265 最高 5Mp30，0.5T NPU，集成 EPHY；64MB 实现双目 4Mp/三目 2Mp/单目 5Mp | MC6322：快启；MC6321L：快启+AOV；已大规模出货 | 富瀚微官方微信公众号（转电子发烧友），2025-04-19，https://www.elecfans.com/d/6548855.html |
| MC6357 | 4K 网络摄像机 SoC | 支持 AOV、Pre-rolling（预录）、UVC、快起 | 电子发烧友（富瀚微公众号转载），2025-08-28 |
| FH8626V300 / FH8626V300L | 2M/3M IPC SoC，H.264/JPEG，内置 64MB DDR2，0.5T NPU | FH8626V300L 定位"2M/3M AOV 网络摄像机 SOC"；AOV 2.0 + 新一代 ISP | 官网新闻，2025-11，https://www.fullhan.com/index.php?c=article&id=475 |
| MC3302 | — | 双屏异显+超低功耗 | RT-Thread 社区新闻，2025-09-12 |

**功耗指标**

| 指标 | 数值 | 口径 | 来源 |
|---|---|---|---|
| FH8626V300 AOV 模式 | 4.5mW | 1fps、无人环境（方案宣传图表） | eet-china/RT-Thread《高性价比AOV2.0双摄方案》，2025-07-31，https://www.eet-china.com/mp/a425460.html |
| FH8626V300 事件触发 | 220mW | 25fps，人/车/宠物 | 同上 |

**机制**：AOV 2.0 = 无事件时芯片进入低帧率、低内存休眠状态，内置 AI 算法持续高频定点抓拍检测；事件触发快速切全帧率录像+报警（eet-china，2025-07-31）。

**案例**：电池摄像机、户外太阳能摄像机、视频门锁/门铃/猫眼、带屏摄像头、多目/枪球摄像机（MC632X 官方典型应用）。

**信息缺口**：官网产品/新闻页无功耗数字；4.5mW 出自方案商宣传图，测试条件（是否含 sensor/WiFi、整板还是芯片）未说明；快启时间：公开渠道不可得。

### 4.3 国科微 Goke（300672）

**芯片矩阵**

| 芯片 | 规格 | 低功耗相关 | 来源 |
|---|---|---|---|
| GK7203V1 系列（2025-07 发布） | ARM Cortex-A7 + RISC-V 双核；0.2T NPU；内置 64/128MB DDR（支持 DDR 自刷新）；H.264 1296P；MIPI 双目可扩展 4 目 | STR 低功耗待机；AOV 模式 2MP@1fps 功耗近 40mW；内置 MCU+快启 Linux 降低首帧稳定图像耗时；NPU 精准检测避免误检频繁启动；AOV 采集与补光灯同步联动 | 官网新闻，2025-07-28，http://www.gokemicro.com/News/info.aspx?itemid=433 |
| GK7206V1 系列（2025-07 发布、2025-09 量产） | 1.0T@INT8 NPU；圆鸮 AI ISP；双 3DNR | STR 待机实现 AOV；**AOV 模式单板（含图像传感器）2MP@1fps 42mW、4MP@1fps 50mW**；夜间 AI NR 免补光；低延时 3ms（首行显示）/≤7ms（编码发出） | 官网新闻，2025-09-24，http://www.gokemicro.com/News/info.aspx?itemid=436 |
| GK7205V200/V300 等 | A7 + ISP，H.265 低功耗多媒体 SoC | 低功耗定位（datasheet 口径） | GK7205V300 datasheet，https://file.elecfans.com/web2/M00/27/47/poYBAGHBpgiAAurBABfQX9W_Bf0227.pdf |

**机制**：STR（Suspend-To-RAM）待机技术为 AOV 关键——国科微深耕机顶盒 17 年的成熟技术移植到 IPC（官网新闻 itemid=436）；DDR 自刷新保活；MCU+快启 Linux 快启。

**案例**：消费级摄像头、低功耗电池摄像头、行车记录仪、可视门铃门锁、无人机图传、扫码器、人脸识别终端（GK7203V1 官方新闻）；GK7206V1 "进入传统安防与消费类电子头部企业供应链"（客户名未披露）。

**信息缺口**：非 AOV 状态（纯待机/关机）功耗、快启具体时间数值、终端客户名称：公开渠道不可得。

---

## 5. 横向对比要点

| 厂商 | AOV 对标程度 | 最低公开 AOV/待机功耗 | 快启公开指标 | 保活/唤醒机制 |
|---|---|---|---|---|
| SigmaStar | 中（SDK 级 AOV/哨兵模式，无官方 AOV 功耗数字） | 待机 μA 级（SSC303/306，PIR 口径）；工作 300mW | 306 系列冷启动首帧 68ms | M4 低功耗核 always-on；PIR 唤醒 |
| 瑞芯微 | 高（官方 AOV 产品系列 + AOV 3.0/AOA） | AOV 整机 ~40mW@1fps（RV1106G2）；AOA 待机 ~1mW（RV1126B） | 250ms 抓图、1s 人脸识别（RV1106） | AI 多目标检测（日 30m/夜 20m）+ 音频事件唤醒 |
| 全志 | 中高（V821 明确 AOV 档位 + μA 级 Wi-Fi 保活） | Wi-Fi DTIM10 保活 180μA@4.2V | 疾风系统 100/200/700ms（V853） | 双 RISC-V 异构 + XR806 μA 保活 |
| 安凯微 | 中高（AOV 整机 30mW 官方数字） | AOV 整机 30mW@1fps（AV130/KM01） | 公开渠道不可得 | 公开渠道不可得 |
| 富瀚微 | 中（AOV 2.0，型号带 AOV 后缀） | AOV 4.5mW@1fps（FH8626V300，方案口径） | 公开渠道不可得 | AI 高频定点抓拍检测 |
| 国科微 | 高（STR 待机 + AOV 单板功耗官方数字） | AOV 单板 42mW@1fps（GK7206V1，含 sensor） | "大幅降低首帧耗时"（无数值） | STR + DDR 自刷新 + NPU 防误检 |

注：各厂商功耗口径不一致（芯片/单板/整机、含否 sensor 与 WiFi），横向比较仅作量级参考。

---

## 6. 参考资料列表（访问日期均为 2026-09-10）

1. 星宸科技官网（场景页/新闻）：https://www.sigmastar.com.cn/ 、https://www.sigmastar.com.cn/market/1
2. 知乎·芯智云《代理商 | Sigmastar SSC303&306 低功耗视觉芯片产品介绍与应用》：https://zhuanlan.zhihu.com/p/2000568550117631855
3. 知乎·芯智云《基于Sigmastar SSC308DE的低功耗IP摄像头解决方案》：https://zhuanlan.zhihu.com/p/16193465516
4. 与非网·芯智云《星宸科技（Sigmastar）SSC308QE，赋能高清AI安防场景落地》：https://m.eefocus.com/article/2068211.html
5. 物联网世界《800万分辨率仅需64MB内存！星宸科技306系列改写IPC芯片成本规则》：https://www.iotworld.com.cn/html/News/202512/ad57c1c34687ff3d.shtml
6. 16RD《SigmaStar 低耗能系列芯片 AI性能对比大全》：https://www.16rd.com/writings-864651-1.html
7. 16RD《sigmastar SSC333/335/336/338/339G 全面对比》：https://www.16rd.com/writings-864850-1.html
8. 16RD《SSC30KD/SSC30KQ IP Camera SoC处理器datasheet》：https://bbs.16rd.com/thread-587008-1-1.html
9. CSDN《星宸SigmaStar主控芯片SSC30KQ》（规格存在冲突，慎用）：https://blog.csdn.net/qq_68783176/article/details/156197614
10. 瑞芯微官网《瑞芯微发布新一代机器视觉方案RV1106及RV1103》：https://www.rock-chips.com/a/cn/news/rockchip/2022/0217/1541.html
11. 瑞芯微官网 RV1106/RV1103 产品页：https://www.rock-chips.com/a/cn/product/RV11xilie/2022/0926/1661.html 、https://www.rock-chips.com/a/cn/product/RV11xilie/2022/0926/1662.html
12. 瑞芯微官网 RV1106B/RV1103B/RV1126B 产品页：https://www.rock-chips.com/a/cn/product/RV11xilie/2025/1208/2121.html 、.../2119.html 、.../2117.html
13. 中芯网（转瑞芯微官网）《瑞芯微推出的AOV IPC方案：低功耗技术引领新潮流》：https://www.icanic.cn/news/2841.html
14. ScenSmart《基于瑞芯微RV1106芯片的AOV IPC解决方案》：https://www.scensmart.com/solutions/aov-ipc-solution-based-on-rv1106/
15. 我爱方案网《瑞芯微RV1106B 4K摄像头方案：AOV模式功耗降90%》：https://news.52solution.com/news/80061168/
16. 我爱方案网《功耗低至1mW！瑞芯微RV1126B AOV 3.0摄像头方案》：https://www.52solution.com/news/80061070/
17. CSDN·眺望电子《【RV1126B 实战连载 09】AOV低功耗持续录像实测解析》：https://blog.csdn.net/qq_33753562/article/details/163560220
18. CSDN·Tronlong《瑞芯微"低功耗录像技术"，AI节能90%+》：https://blog.csdn.net/Tronlong/article/details/162196385
19. CSDN《【RV1106 项目实战-05】系统低功耗深度优化：从250mW到40mW》（AI 辅助，参考）：https://blog.csdn.net/lin280340404/article/details/160601716
20. 全志官网 V853/V851s/V821 产品页：https://www.allwinnertech.com/index.php?c=product&a=index&id=117&solveid=40 、...&id=118 、...&id=136&solveid=40
21. 全志官网新闻《V853 疾风系统/低功耗》：https://www.allwinnertech.com/index.php?c=news&a=index&id=344
22. 全志在线社区文档《V821 芯片介绍》：https://docs.aw-ol.com/docs/soc/v821/
23. 全志官方 V833 brief PDF（2020）：https://www.allwinnertech.com/uploads/pdf/20211016162024b6.pdf
24. 安凯微官网 AK3918EV200/EV300L/AV100 产品页：http://www.anyka.com/article/16/6.html 、http://www.anyka.com/article/16/17.html 、http://anyka.com/article/17/9.html
25. 安凯微官网新闻《AK3918AV130 获 ICDIA 2026 市场先锋奖》：http://anyka.com.cn/article/22/115.html
26. 界面新闻《安凯微：AK3918Av100系列芯片采用22nm工艺制程》：https://www.jiemian.com/article/10108495.html
27. 富瀚微官网《富瀚微发布FH8626V300》：https://www.fullhan.com/index.php?c=article&id=475
28. 电子发烧友（富瀚微公众号）《富瀚微新一代双摄MC632X系列概述》：https://www.elecfans.com/d/6548855.html
29. eet-china/RT-Thread《高性价比AOV2.0双摄方案：富瀚微FH8626V300》：https://www.eet-china.com/mp/a425460.html
30. 国科微官网《国科微发布轻算力多目AOV视觉芯片 GK7203V1》：http://www.gokemicro.com/News/info.aspx?itemid=433
31. 国科微官网《普惠型黑光AOV视觉处理芯片GK7206V1系列量产上市》：http://www.gokemicro.com/News/info.aspx?itemid=436
32. 新领创业/物联世界《AOV芯片大战升级！低功耗IPC赛道正在"卷"向何方？》：https://www.newtid.com/4709.html
33. 搜狐《AOV 3.0技术加持！低功耗IPC芯片市场风云再起》：https://www.sohu.com/a/919901661_121124364
34. 安防展览网《AK3918EV200 摄像机芯片》（EV300 功耗口径）：https://www.afzhan.com/st190735/product_12442796.html
35. 百度文库《安凯AK3918E&AK3916E芯片产品及方案介绍》（二手 PPT 摘编）：https://wenku.baidu.com/view/1a199fe7a2c7aa00b52acfc789eb172ded6399de.html
