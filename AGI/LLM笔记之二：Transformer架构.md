## 1. Transformer架构

### 1.1. Attention
**——当模型处理某个 token 时，不是平均看所有信息，而是自动判断哪些 token 更重要，然后重点参考它们**

|**名称**|**英文**|**直觉理解**|
|---|---|---|
|Query|Q|当前 token 想找什么信息|
|Key|K|每个 token 可以被匹配的标签|
|Value|V|每个 token 真正携带的信息内容|

![[Pasted image 20261104161729.png]]

### 1.2. Self-Attention
**——一句话内部的 token 之间，互相计算注意力**

![[Pasted image 20261104162054.png]]

经过 Self-Attention 之后，`学习` 的表示已经融合了上下文，知道它前面有 `机器`，所以这里更可能指`机器学习`这个技术概念，而不是普通意义上的学习行为

Self-Attention 可以理解为给句子内部建立了一张关系网，在真实模型里，这张关系网不是人工指定的，而是通过训练学出来的。
- 哪些词之间经常有关联
- 哪些词决定语义
- 哪些词影响情感
- 哪些词表示指代关系
- 哪些词对预测下一个token更重要

不过，一个 Attention 视角可能还不够。语言关系很复杂，同一句话可以从不同角度理解。模型可能需要同时关注语法结构、实体关系、位置关系、语义合理性。

所以 Transformer 引入了 Multi-Head Attention，也就是**多头注意力**（让模型用多个视角同时观察同一句话）

![[Pasted image 20261104162539.png]]

 Transformer 表达能力强的重要原因之一：它不是只用一种方式理解文本，而是可以在多个语义空间里同时建模 token 之间的关系

### 1.3. Transformer Block
**——Transformer 里可以反复堆叠的一层“语言理解单元”**

每经过一个 Transformer Block，token 的表示都会被更新一次：先通过 Self-Attention 和上下文建立关系，再通过前馈网络进一步加工，最后输出给下一层

一个完整的 Transformer Block 通常包含几部分：

|**组件**|**作用**|**直觉理解**|
|---|---|---|
|Multi-Head Self-Attention|建模 token 之间的关系|让每个 token 知道该看谁|
|Feed Forward Network|进一步加工 token 表示|对上下文信息做消化和提炼|
|Residual Connection|保留原始信息|避免层数太深时信息丢失|
|LayerNorm|稳定每层计算|让训练过程更平稳|

![[Pasted image 20261104163141.png]]

（1）Transformer 需要位置编码

- 告诉模型每个 token 在句子中的位置，让模型能够区分不同顺序带来的语义差异
- 常见做法是在 token embedding 的基础上加入位置编码，或者在 Attention 计算过程中引入相对位置信息

（2）Feed Forward Network 加工信息

- 对每个 token 的表示做一次非线性加工，让模型有能力表达更复杂的模式
- Attention复杂汇总上下文，Feed Forward负责消化和加工上下文

（3）残差连接和LayerNorm稳定训练

- 现代LLM存在很多层Transformer Block，如果每一层都直接覆盖上一层信息，训练会很不稳定，也容易出现梯度消失、信息丢失等问题
	- 残差连接：不要让每一层从零开始重写信息，而是在原有信息基础上做增量修改
	- LayerNorm：把每一层的数值范围整理得更稳定，避免训练过程中数值忽大忽小


### 1.4. Transformer如何跑起来
**——Transformer 的工作过程，就是不断更新每个 token 的表示，让它从一个孤立的词，逐渐变成融合上下文信息的语义表示**

![[Pasted image 20261104164016.png]]

Transformer 本身并不等同于 GPT，也不只用于生成式大语言模型。它更像是一套基础架构，可以根据任务目标，组合成不同类型的模型。常见的 Transformer 架构大致有三类：

|**架构**|**代表模型**|**适合任务**|**特点**|
|---|---|---|---|
|Encoder-only|BERT|理解、分类、标注|可以看完整上下文|
|Decoder-only|GPT|文本生成、对话、代码生成|只能看前文，预测后文|
|Encoder-Decoder|T5、早期翻译模型|翻译、摘要|一边理解输入，一边生成输出|

## 2. Dense Transformer & MoE

Dense Transformer 和 MoE 到底差在哪里，MoE 解决了什么问题，以及为什么它正在成为很多头部基模的重要架构选择？
### 2.1. Scaling Law
**——继续扩大模型、数据和计算，通常可以换来更强的能力**

在 LLM 中，我们常说的“参数”，主要指模型训练过程中学出来的权重，而不是人工配置项。以 Transformer 为例，参数主要分布在几个位置：

|**参数位置**|**主要内容**|**作用**|
|---|---|---|
|Embedding|token embedding|把 token 转成向量表示|
|Attention|Q/K/V/O 投影矩阵|建模 token 之间的上下文关系|
|FFN|Up / Gate / Down 等线性变换矩阵|对每个 token 的表示做非线性特征变换|
|LayerNorm/RMSNorm|归一化缩放参数，用于稳定训练|稳定训练过程中的数值分布|
|Output Head|输出词表投影矩阵|把 hidden state 转成下一个 token 的概率分布|

一般来说模型变大，通常不是简单地“多存了一些数字”，而是意味着模型结构里的几个关键维度一起变大：

|**扩展方式**|**对计算量的影响**|
|---|---|
|层数更多|每个 token 要经过更多 Transformer Block|
|FFN 中间维度更大|FFN 参数量和计算量显著增加|
|Attention head / hidden size 配套扩大|投影矩阵和注意力计算都会增加|
|上下文更长|Attention 和 KV Cache 压力上升|
尤其是 hidden size 的扩大，会显著放大计算量。因为 Transformer 里的核心计算大多是矩阵乘法，矩阵规模变大时，计算量不是线性增加，而是接近按平方级增长。

以 FFN 为例， hidden size 是 `d`，FFN 中间维度是 `4d`，其计算量如下所示：

![[Pasted image 20261104165753.png]]

**如果 FFN 主要是对每个 token 独立做特征变换，那么能不能不要让所有 token 都经过同一个巨大的 FFN，而是为不同 token 选择不同的 FFN 子网络？**——MoE核心思路


### 2.2. Dense Transformer



### 2.3. MoE




