# 手机 SoC 端侧 AI 能力横向对比

> 2026-10-23 初稿。旗舰 SoC 三强的 AI 实力：规格、实测、以及"TOPS 数字之外"的视角。
> 相关：[[NPU架构对比]]、[[异构调度与NPU利用]]、[[量化技术]]

## 0. TL;DR

- 2025 世代旗舰（同为台积电 N3E）：**骁龙 8 Elite（Hexagon ~45 TOPS）/ 天玑 9400（NPU 890 ~50 TOPS）/ Apple A18 Pro（ANE ~35 TOPS）**——标称算力差距 <1.5×，但实测 LLM 推理表现分化明显
- 第三方实测（7B Q4 模型）：骁龙 22 tok/s / 天玑 20 tok/s / A18 Pro 跑 3B 达 45 tok/s——**Apple 用更小模型换流畅体验**，印证其"角色模型"路线（见 [[SLM设计演进]]）
- **内存带宽是被低估的分水岭**：骁龙/天玑 LPDDR5X 85.3 GB/s vs A18 Pro 60 GB/s——decode 是带宽受限的 GEMV，带宽直接决定 token 速度（见 [[异构调度与NPU利用]]）
- 差异化竞争点已转向：端侧 LoRA 训练（天玑）、系统级模型服务（Apple）、工具链成熟度（高通 AI Hub）

## 1. 规格对比（2025 世代旗舰）

| 项目 | 骁龙 8 Elite | 天玑 9400 | Apple A18 Pro |
|---|---|---|---|
| 工艺 | TSMC N3E | TSMC N3E | TSMC N3E |
| CPU | 2×Oryon P@4.32G + 6×Oryon@3.53G | 1×X925@3.63G + 3×X4 + 4×A720（全大核） | 2×P@4.04G + 4×E |
| GPU | Adreno 830（切片式） | Immortalis-G925 MP12 | 6 核自研 |
| NPU | Hexagon（~45 TOPS） | NPU 890（~50 TOPS） | ANE 16 核（~35 TOPS） |
| **内存带宽** | **LPDDR5X 85.3 GB/s** | **LPDDR5X 85.3 GB/s** | **LPDDR5X 60 GB/s** |
| L2/L3 | 24MB L2 | 12MB L3 + 10MB SLC | 16MB L2 + 24MB SLC |

来源：[BeastCompare 规格矩阵](https://www.beastcompare.com/articles/snapdragon-8-elite-vs-dimensity-9400-vs-apple-a18-pro-architecture-benchmarks)（注：TOPS 为厂商口径，测试条件不一，仅供量级参考）

后继世代：**8 Elite Gen 5**（12 标量+8 向量+1 张量配置、INT2、生成式模型加密）、**天玑 9400+**（端侧 DeepSeek-R1-Distill 1.5B/7B/8B、MoE/MLA 支持、推理 +20%）、**A19 Pro**（N3P，单核 GB6 ~3900-4000 领先安卓 ~24%，首次本地 7B）。

## 2. 实测数据

### 2.1 第三方整机实测（7B Q4，MLC-LLM，25°C 室温）

来自[个人博主实测](https://www.298.name/post/212.html)（工程机 16GB RAM，量级可信、非权威）：

| 指标 | 骁龙 8 Elite + 7B | 天玑 9400 + 7B | A18 Pro + 3B（系统模型） |
|---|---|---|---|
| 首 token 延迟 | 0.8s | 0.9s | 0.3s |
| 生成速度 | 22 tok/s | 20 tok/s | 45 tok/s |
| 功耗 | 3.2W | 2.9W | 1.8W |
| 连续 10 分钟温度 | 44°C | 42°C | 38°C |

### 2.2 聚合基准（BeastCompare 汇总，方法未公开，谨慎参考）

| 负载 | 骁龙 8 Elite | 天玑 9400 | A18 Pro |
|---|---|---|---|
| Llama 3.2 3B 量化 | 68.5 tok/s | 64.2 tok/s | 42.0 tok/s |
| Mistral 7B INT4 | 32.4 tok/s | 30.1 tok/s | 21.5 tok/s |
| SD 1.5（512²，20 步） | 1.45s | 1.18s | 2.10s |

两套数据的共识：**安卓旗舰跑 7B 级模型已到"可用"阈值（20+ tok/s、~3W、40°C 出头）**；Apple 选择 3B 换来 45 tok/s + 38°C 的从容，代价是能力上限。

## 3. TOPS 之外：三个真正的分水岭

### 3.1 内存带宽

decode 阶段每 token 读全部激活权重，7B INT4 ≈ 3.5GB/token-pass：85 GB/s 带宽的理论上限 ≈ 24 tok/s——**实测 22 tok/s 已经贴近带宽天花板**。这意味着：
- 继续堆 NPU TOPS 对 decode 无益（算力过剩，见 [[异构调度与NPU利用]]）
- 下一步收益来自：更低 bit（[[量化技术]]）、更小激活参数（[[MoE端侧化]]）、投机解码（[[投机解码与加速]]）
- LPDDR6/定制封装内存将是下一代 SoC 的 AI 卖点

### 3.2 端侧训练能力

- **天玑 9400/9400+：宣称首个支持端侧 LoRA 训练的手机 NPU**——个性化不再只是 RAG，还能微调（与 [[隐私与端侧学习]] 直接相关）
- 高通路线：AI Hub 上云真机调试 + AIMET 量化工具链
- Apple：端云分工明确，端侧 3B + LoRA 适配器热切换（系统内建），训练类能力主要留在云/联邦

### 3.3 生态位差异

| 维度 | 高通 | 联发科 | Apple |
|---|---|---|---|
| 强项 | 工具链最成熟（QNN/AI Hub/AIMET）、真机云调试 | 性价比 + 跟进速度快（DeepSeek 端侧、MoE/MLA） | 系统级整合（Foundation Models 框架全 App 可用） |
| 开发者可达性 | 高（SDK 完整但底层闭） | 中（NeuroPilot "一次编写"） | 高（Swift API）但模型不可替换 |
| 自研深度 | CPU/GPU/NPU 全自研 | Arm 公版 CPU + 自研 NPU/ISP | 全栈垂直整合 |

## 4. 关键洞察

1. **"跑得动 7B"已成共识，竞争转向"跑得久、跑得省、跑得个性化"**——功耗（3W 级）、热（<45°C 连续）、端侧微调是新的胜负手
2. **带宽是新的 TOPS**：当 NPU 算力普遍过剩，内存子系统（带宽+容量）成为模型规模的上界；这是"唯 TOPS 论"被抛弃的物理学解释
3. **Apple 的错位竞争**：不参与"谁跑 7B 更快"，用系统模型 + 3B + ANE/统一内存的从容体验定义"端侧 AI 该有的样子"——评测者与用户的评分标准正在分裂
4. **中国力量入场**：小米玄戒 O1（自研 6 核 NPU）、华为麒麟（自研 NPU + 昇腾生态）把"自研深度"变成竞争维度（见 [智东西分析](https://zhidx.com/p/487563.html)）

## 5. 开放问题

- [ ] 统一端侧 LLM 基准缺失：ETH AI Benchmark、Geekbench AI 与真实 App 体验的相关性存疑；GSMA 正推 chipset benchmark（[报告](https://www.gsmaintelligence.com/research/on-device-ai-mobile-network-filler-or-saviour)）
- [ ] 端侧 LoRA 训练的实际体验（天玑）：训练一个适配器要多久、多少电
- [ ] LPDDR6 / 封装内存对端侧模型的解锁幅度
- [ ] A19 Pro 端侧 7B 的公开实测（对比上表）

## 6. 来源

- [BeastCompare: 8 Elite vs Dimensity 9400 vs A18 Pro](https://www.beastcompare.com/articles/snapdragon-8-elite-vs-dimensity-9400-vs-apple-a18-pro-architecture-benchmarks)
- [手机本地 AI 实测（298.name）](https://www.298.name/post/212.html)
- [天玑9400+/A19 Pro/骁龙8e 对比（搜狐）](https://www.sohu.com/a/972002453_120457927)
- [Snapdragon 8 Elite Gen 5 Product Brief](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Snapdragon-8-Elite-Gen-5-product-brief.pdf)
- [智东西：芯片六巨头，决战手机AI芯片](https://zhidx.com/p/487563.html)
- [Futuresource: AI is Trading the Cloud for Your Pocket](https://www.futuresource-consulting.com/the-source/industry-pulse/ai-is-trading-the-cloud-for-your-pocket-starting-with-15-billion-smartphones/)
