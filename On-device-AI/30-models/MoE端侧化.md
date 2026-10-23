# MoE 端侧化

> 2026-10-23 初稿。Mixture-of-Experts 用"稀疏激活"换取容量，但端侧的瓶颈恰恰是内存而非算力——这个错配催生了一整条研究线。
> 相关：[[SLM设计演进]]、[[量化技术]]、[[投机解码与加速]]

## 0. TL;DR

- MoE 的核心矛盾在端侧被反转：云端 MoE 省的是**算力**（激活 5–10% 参数），端侧缺的是**内存**（全部专家都要驻留）——Qwen1.5-MoE（14.3B）推理需 ~30GB 内存
- 核心观察（EdgeMoE）：专家权重**大而冷**（ST-base-16 中占 86.5% 内存、仅 26.4% 计算量），非专家权重**小而热**——天然适配存储层级（RAM + 外存）
- 技术收敛为三板斧：**专家卸载 + 激活预测预取 + 专家级混合精度**
- gpt-oss-20b（原生 MXFP4 + 5–10% 激活）代表另一条路：**训练时就为端侧定形**，不靠部署期补救

## 1. 为什么 MoE 对端侧有吸引力

| MoE 特性 | 端侧价值 |
|---|---|
| 每 token 仅激活 top-k 专家（5–10% 参数） | 计算量≈小模型，容量≈大模型 |
| 专家分工带来容量扩展 | 端侧"一个模型多任务"（每个 App 场景命中的专家不同） |
| 推理时算力需求低 | 匹配手机 GEMV 带宽受限的现实（见 [[异构调度与NPU利用]]） |

代价：**总参数全量驻留内存**。手机 8–12GB 内存预算下，>10B 的 MoE 无法整体装载——这就是"内存-算力错配"。

## 2. 系统研究主线：专家卸载

### 2.1 EdgeMoE（奠基工作，[arXiv:2308.14352](https://arxiv.org/abs/2308.14352) / IEEE TMC 2025）

- **存储分层**：非专家权重常驻内存；专家放外存，激活时按需加载，内存占用 = 非专家 + 单层专家
- **专家级 bitwidth 自适应**：离线逐步压低"对量化最鲁棒"的专家的位宽，直到精度损失达阈值——最小化专家体积即最小化加载时间
- **专家预取**：观察到专家激活路径高度倾斜且跨层相关——用统计模型从前几层激活预测下层专家，I/O 与计算流水化
- 实测：Jetson TX2 加速 1.19–2.77×；小米 14（骁龙 8 Gen 3）**内存省 63%**、提速 25%——手机上 I/O 是更大瓶颈（计算强、IO 弱）

### 2.2 后续演进

| 工作 | 核心创新 | 效果 |
|---|---|---|
| [SwapMoE (ACL 2024)](https://aclanthology.org/2024.acl-long.363.pdf) | Virtual Experts（动态专家子集）+ profiling 引导规划 + 重要性感知调度 | 紧内存预算下达到剪枝小模型的延迟、大得多的精度 |
| [Fate (2025)](https://arxiv.org/html/2502.12224) | **跨层 gate 输入**做专家预取（高精度、零额外 GPU 开销）+ 浅层偏爱缓存（命中率 99%） | prefill 最高 4.5×、decode 4.1× 加速 |
| [PC-MoE (IEEE TC 2025)](https://doi.org/10.1109/tc.2025.3575905) | Parameter Committee；利用专家激活的时间局部性、可交换性、可跳过计算 | Swin-MoE 检测任务：内存 -42%、延迟 -19%，精度仅 -0.1% |
| [CoMoE (2025)](https://arxiv.org/html/2508.09208) | 聚合（合并/蒸馏/共享）与卸载的**联合**优化，响应移动性和网络变化 | 内存 -70%；Switch-Base-128 从 15.6GB 降到 4.7GB |

共同洞察：**专家激活不是随机的**——时间局部性（连续 token 复用专家）、跨层相关性（上层激活预示下层）、路径倾斜（少数路径高频出现）三者叠加，使预取/缓存可行。

## 3. 另一条路：训练时就为端侧定形

部署期卸载是补救；更根本的是让 MoE 生来端侧友好：

- **gpt-oss-20b**：原生 MXFP4 训练 + 每 token 仅激活 ~5–10% 参数 → 内存占用被格式和稀疏性同时压住，无需外存交换
- **Apple 服务器模型 PT-MoE**（并行轨道 MoE）：虽然跑在云端 Private Cloud Compute，但其"多小 transformer 轨道、仅在输入输出边界同步"的设计思路（降低同步开销）对端侧多核 NPU 映射有参考价值
- **学术前沿**（ABI Research 综述）：CoEL（边缘集群专家交换）、FloE（单卡内存不足时即时 MoE 推理）——把"卸载"从本机外存扩展到**边缘集群/多设备**

## 4. 与其他技术的组合

| 组合 | 关系 |
|---|---|
| MoE × 量化 | 正交可叠加（EdgeMoE 的专家级 bitwidth 自适应本质是量化感知的卸载） |
| MoE × 投机解码 | MatFormer 的嵌套子模型行为一致 → 天然 draft-target 对（见 [[模型-硬件协同设计]]） |
| MoE × 端边协同 | 专家放在哪一层存储（RAM/外存/边缘服务器）是连续谱——CoMoE/SLED 是两端 |
| MoE × NPU | 专家路由的动态性 vs NPU 静态图偏好，是新的错配（路由器分支难以 NPU 化） |

## 5. 关键洞察

1. **端侧 MoE 的本质是存储层级调度问题**，不是模型问题：全部创新都在"何时把哪个专家放在哪"
2. **激活预测是胜负手**：Fate 的跨层 gate 预取、EdgeMoE 的路径统计——预测准了 I/O 就能被计算掩盖
3. **手机比嵌入式设备更难**：手机计算强、I/O 相对弱，卸载收益打折（EdgeMoE 手机端仅 25% vs Jetson 2.7×）；UFS 顺序带宽决定了专家粒度下限
4. **冷热分层思想普适**：非专家(热)/专家(冷)的二分与 PowerInfer 的热点神经元、CPU cache 分层是同构问题

## 6. 开放问题

- [ ] 路由器的端侧实现：top-k 分支在 NPU 静态图上的表达（可能要 CPU 承担路由）
- [ ] 专家粒度与 UFS/存储带宽的匹配：多大/多小的专家是换入换出的最优单元
- [ ] 端侧 MoE 的个性化：用户数据能否重塑专家分工（联邦 + MoE）
- [ ] gpt-oss 类"原生端侧 MoE"与卸载式部署的帕累托对比缺乏公开基准

## 7. 来源

- [EdgeMoE (arXiv:2308.14352)](https://arxiv.org/abs/2308.14352)（[代码在 mllm](https://github.com/UbiquitousLearning/mllm)）
- [Fate: Fast Edge Inference of MoE (arXiv:2502.12224)](https://arxiv.org/html/2502.12224)
- [SwapMoE (ACL 2024)](https://aclanthology.org/2024.acl-long.363.pdf)
- [PC-MoE (IEEE TC 2025)](https://doi.org/10.1109/tc.2025.3575905)
- [CoMoE (arXiv:2508.09208)](https://arxiv.org/html/2508.09208)
- [ABI Research: Compact AI Models](https://www.abiresearch.com/market-research/insight/7786804-smaller-and-leaner-how-compact-ai-m)（CoEL/FloE 综述）
- [Apple FM 2025](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates)（PT-MoE 设计）
