# Transformer 架构详解

> 面向想真正理解 Transformer（而非只会调用 API）的开发者。
> 从"为什么需要它"讲起，逐层拆解核心机制，最后串联主流变体。
> 原论文：*Attention Is All You Need*（Vaswani et al., 2017, Google）。

---

## 1. 背景：为什么需要 Transformer

Transformer 之前的序列建模主力是 RNN / LSTM：

| 模型 | 瓶颈 |
|---|---|
| RNN | 逐步递归，长距离依赖衰减，无法并行训练 |
| LSTM / GRU | 缓解了梯度消失，但仍是串行计算，路径长度 O(n) |
| CNN 序列模型 | 可并行，但捕获远距离依赖需要堆叠很多层 |

Transformer 的两个关键突破：

1. **彻底丢弃递归结构**：整个模型只由注意力 + 前馈网络组成，训练时可全序列并行，路径长度 O(1)；
2. **自注意力机制**：序列中任意两个位置直接建立联系，无论相距多远。

一句话概括：

> **Transformer = 自注意力（建模 token 间关系）+ 前馈网络（逐位置变换特征）+ 残差与归一化（让深层可训练），堆叠 N 层。**

---

## 2. 总体结构

原始 Transformer 是 **编码器–解码器（Encoder–Decoder）** 结构，用于机器翻译：

```
输入 tokens
   │
   ▼
Embedding + 位置编码
   │
┌─────────────────┐
│  编码器 × N=6    │   每层：多头自注意力 → Add & Norm → FFN → Add & Norm
└─────────────────┘
   │（编码器输出 K、V 送给解码器）
   ▼
┌─────────────────┐
│  解码器 × N=6    │   每层：掩码多头自注意力 → 交叉注意力 → Add & Norm → FFN → Add & Norm
└─────────────────┘
   │
   ▼
Linear + Softmax → 输出概率
```

三个要点：

- **编码器**：双向看到整个输入序列，负责"理解"；
- **解码器**：自回归生成，当前 token 只能看到之前的 token（掩码保证），通过**交叉注意力**读取编码器输出；
- 后来的演化：**BERT 只取编码器**（理解类任务），**GPT 只取解码器**（生成类任务），原始编码器–解码器结构在 T5、翻译模型中延续。

---

## 3. 输入表示：Embedding 与位置编码

### 3.1 Token Embedding

文本先被切分为 token（词 / 子词 / 字节），每个 token 映射为一个 d 维稠密向量（原论文 d_model = 512）。

### 3.2 为什么需要位置编码

自注意力本身是**置换不变**的——把输入序列打乱顺序，注意力的输出也只是跟着打乱，模型无法区分"猫咬狗"和"狗咬猫"。因此必须把位置信息显式注入。

### 3.3 正弦位置编码（原始方案）

$$PE_{(pos, 2i)} = \sin\left(\frac{pos}{10000^{2i/d}}\right), \quad PE_{(pos, 2i+1)} = \cos\left(\frac{pos}{10000^{2i/d}}\right)$$

- 不同维度使用不同频率的sin/cos，从快变振荡到近乎恒定，类似二进制计数的多尺度表达；
- 相对位置可由线性变换表示，使模型容易学到相对位置关系；
- 直接加到 token embedding 上：`输入向量 = Embedding(token) + PE(pos)`。

### 3.4 后续演化

| 方案 | 思路 | 代表模型 |
|---|---|---|
| 可学习绝对位置编码 | 当作可训练参数 | GPT-2 / BERT |
| RoPE 旋转位置编码 | 把位置做成向量的旋转角，注意力内积自然包含相对位置 | LLaMA、Qwen、DeepSeek 等主流开源模型 |
| ALiBi | 直接在注意力分数上加线性距离惩罚 | BLOOM、MPT |

---

## 4. 核心：缩放点积注意力（Scaled Dot-Product Attention）

### 4.1 三个角色：Q、K、V

对每个 token 的表示 x，通过三个可学习矩阵生成三个向量：

- **Query（Q）**：我在找什么信息？
- **Key（K）**：我能提供什么信息（的索引）？
- **Value（V）**：我实际携带的内容。

类比检索：Q 是搜索词，K 是每条结果的标题，V 是结果正文。用 Q 和所有 K 算相似度，按相似度加权求和所有 V。

### 4.2 公式

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right)V$$

分四步理解：

1. **打分**：$QK^\top$ —— 每个 query 对每个 key 做点积，得到原始注意力分数（n × n 矩阵）；
2. **缩放**：除以 $\sqrt{d_k}$ —— 点积的方差随维度增长（约 d_k 倍），过大分数会让 softmax 饱和、梯度趋近于零。除以 $\sqrt{d_k}$ 把方差拉回 1，稳定训练；
3. **归一化**：softmax 把分数变成非负、和为 1 的权重分布；
4. **加权**：用权重对 V 加权求和——每个 token 的新表示是全序列信息的按需混合。

### 4.3 计算复杂度

- 时间：O(n²·d)，n 为序列长度——**长序列的主要瓶颈**；
- 空间：O(n²)（存注意力矩阵）。

这是后续各种"高效注意力"（FlashAttention、稀疏注意力、线性注意力）针对的目标。

---

## 5. 多头注意力（Multi-Head Attention）

把 Q、K、V 分成 h 个头（原论文 h=8，每头 $d_k = d_v = 512/8 = 64$），**每个头独立做注意力，再拼接输出**：

$$\text{MultiHead}(Q,K,V) = \text{Concat}(\text{head}_1, \dots, \text{head}_h)W^O$$

为什么需要多头：

- **单头的局限**：一次注意力只能按一种模式分配权重，平均意义上信息被"压扁"；
- **多头 = 多个子空间并行学习不同关系**：实践中可观察到某些头专攻句法依赖、某些头关注相邻 token、某些头追踪长距离指代；
- 每头维度降低（d/h），总计算量与单头 full attention 基本持平。

---

## 6. 三种注意力的用法

| 名称              | Q 来自 | K、V 来自         | 作用             |
| --------------- | ---- | -------------- | -------------- |
| **自注意力**（编码器）   | 输入序列 | 输入序列（自身）       | 输入内部两两交互，双向    |
| **掩码自注意力**（解码器） | 目标序列 | 目标序列（自身，仅过去位置） | 自回归生成，防止"偷看未来" |
| **交叉注意力**（解码器）  | 目标序列 | 编码器输出          | 生成时读取源序列信息     |

掩码的实现：在 softmax 之前，把位置 j > i 的分数置为 −∞，softmax 后这些位置权重为 0。

---

## 7. 逐位置前馈网络（FFN）

每层注意力之后接一个两层 MLP（中间维度通常是 4×d_model，原论文 512 → 2048 → 512）：

$$\text{FFN}(x) = \max(0,\ xW_1 + b_1)W_2 + b_2$$

要点：

- **逐位置独立**：对每个 token 的向量分别做相同的变换，token 之间不交互（交互全靠注意力）；
- 通常占模型约 **2/3 的参数量**，近年研究（如 Geva 等的工作）认为 FFN 承担了**键值记忆**式的知识存储功能；
- 现代 LLM 中间层激活从 ReLU 演进为 GeLU / SwiGLU。

---

## 8. 残差连接与层归一化

每个子层（注意力、FFN）都包裹在：

$$\text{output} = \text{LayerNorm}(x + \text{Sublayer}(x))$$

- **残差连接**：梯度可以直通底层，是堆到几十上百层仍能训练的关键；同时隐式保留原始信息，子层只需学习"增量修正"；
- **LayerNorm**：对每个 token 的特征向量做归一化，稳定各层分布。

### Post-Norm 与 Pre-Norm

| 结构 | 公式 | 特点 |
|---|---|---|
| Post-Norm（原论文） | $\text{LN}(x + \text{Sublayer}(x))$ | 理论收敛点更优，但深层训练不稳定，需 warmup |
| Pre-Norm（现代主流） | $x + \text{Sublayer}(\text{LN}(x))$ | 残差主干"干净"，深层训练稳定，GPT-2 之后的标准做法 |
| RMSNorm | 只做缩放、不减均值，比 LN 省一半统计量 | LLaMA 系主流 |

另有 **RoPE + QK-Norm** 等组合，用于稳定大模型深层训练。

---

## 9. 完整数据流（前向传播）

以一个 token 走过一层编码器为例：

1. Embedding + 位置编码 → 向量 x（512 维）；
2. 经 W_Q、W_K、W_V 投影，分成 8 个头；
3. 每头计算 $\text{softmax}(QK^\top/\sqrt{d_k})V$；
4. 拼接 8 头，经输出投影 W^O；
5. 残差相加 + LayerNorm → x'；
6. FFN（512→2048→512）；
7. 残差相加 + LayerNorm → 本层输出。

解码器多一步掩码自注意力与交叉注意力。输出端最后经一层 Linear（映射到词表大小）+ softmax，得到下一个 token 的概率分布。

**生成时是逐 token 自回归**：每步用已生成内容预测下一个 token，直至结束符。KV Cache 是推理优化的核心（缓存历史的 K、V，避免重复计算）。

---

## 10. 训练要点（简述）

- **损失**：交叉熵（对每个位置的下一个 token 分类）；
- **教师强制**：训练时解码器输入用真实目标序列（整体并行计算），推理时才是自回归；
- **关键技巧**：学习率 warmup + decay、标签平滑（0.1）、dropout（0.1）、BPE 分词；
- **扩展律**：Kaplan et al. (2020) 与 Chinchilla (2022) 表明模型性能随参数量、数据量、算力按幂律提升——这正是"堆 Transformer 层 + 堆数据"路线的理论依据。

---

## 11. 变体与演化谱系

| 谱系 | 结构 | 代表 | 典型用途 |
|---|---|---|---|
| 仅编码器 | 双向注意力 | BERT、RoBERTa | 分类、检索、理解 |
| 仅解码器 | 单向（掩码）注意力 | GPT 系列、LLaMA、Qwen、DeepSeek | 文本生成、对话 |
| 编码器–解码器 | 完整结构 | T5、BART、翻译模型 | 序列到序列 |
| 多模态 | 视觉编码器 + LLM | CLIP、ViT 系、视觉语言模型 | 图文理解 |

结构上值得知道的演化：

- **稀疏/高效注意力**：Longformer（滑窗）、FlashAttention（IO 感知的精确加速，不改数学只改访存）、线性注意力近似；
- **混合架构回潮**：Jamba、现代 Mamba 等探索"注意力 + 状态空间模型"混合以降低长序列成本；
- **MoE**：把 FFN 替换为多个专家网络按 token 路由（Mixtral、DeepSeek-V3 等），大幅提升参数量而控制计算量。

---

## 12. 直觉总结

把整篇压缩成几句话：

1. **自注意力是全局信息路由**：每个 token 按相关性从全序列"取材"，距离不再是障碍；
2. **多头是并行的多视角**：不同子空间学习不同关系类型；
3. **FFN 是逐 token 的知识加工**：混合好的信息经过"深加工"存入/取出知识；
4. **残差 + 归一化是深层化的地基**：没有它们，几十层的网络根本训不动；
5. **位置编码补上了注意力缺失的顺序感**：从 sin/cos 演化到 RoPE；
6. **并行训练 + 自回归生成**：训练时一次看全句，推理时一个 token 一个 token 吐——KV Cache 决定了推理效率。

---

## 参考

- Vaswani et al., *Attention Is All You Need*, NeurIPS 2017 — [arXiv:1706.03762](https://arxiv.org/abs/1706.03762)
- The Illustrated Transformer（Jay Alammar）— [jalammar.github.io](https://jalammar.github.io/illustrated-transformer/)
- Su et al., *RoFormer: RoPE*, 2021 — [arXiv:2104.09864](https://arxiv.org/abs/2104.09864)
- Kaplan et al., *Scaling Laws for Neural Language Models*, 2020 — [arXiv:2001.08361](https://arxiv.org/abs/2001.08361)
- Hoffmann et al., *Training Compute-Optimal LLMs (Chinchilla)*, 2022 — [arXiv:2203.15556](https://arxiv.org/abs/2203.15556)
- Dao et al., *FlashAttention*, 2022 — [arxiv.org/abs/2205.14135](https://arxiv.org/abs/2205.14135)
