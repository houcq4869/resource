# 端侧 RAG 与个性化记忆

> 2026-10-23 初稿。让小模型"知道你的事"：检索增强是端侧个性化的主力路径（对比微调）。
> 相关：[[Hybrid AI架构]]、[[端侧Agent与工具调用]]、[[SLM设计演进]]

## 0. TL;DR

- 端侧 RAG 的技术栈已齐备：**EmbeddingGemma 2（多模态嵌入，文本 270M）+ 端侧向量库（SQLite/sqlite-vec/Qdrant）+ LLM Inference API**——Google AI Edge 提供全链路官方库
- 端侧 RAG 与云 RAG 的本质差异是**语料性质**：不是公开网页，而是**个人数据**（相册、笔记、聊天记录、文档）——隐私是特性而非合规负担
- 嵌入模型是新的轻量级赢家：多模态统一向量空间（文本/图像/音频共 740M omnimodal）使"用自然语言搜相册"成为端侧杀手级场景
- 与端侧微调的分工：**RAG 管"事实/证据"（可溯源、即时更新），LoRA/记忆管"风格/偏好"**——两者互补而非竞争

## 1. 为什么 RAG 是端侧个性化的主力

| 方案 | 更新成本 | 可溯源 | 端侧可行性 |
|---|---|---|---|
| 云端微调 | 高 | ✗ | ✗（数据出域） |
| 端侧 LoRA | 中 | ✗ | 🟡（天玑 NPU 890 已支持，见 [[手机SoC端侧AI能力横向对比]]） |
| **端侧 RAG** | **低（增删文档即可）** | **✓（引用来源抑制幻觉）** | **✓ 全链路已产品化** |

小模型世界知识弱（见 [[SLM设计演进]]），RAG 恰好补的是"知识/证据"而非"能力"——缺陷与方案精确对齐。

## 2. 技术栈拆解（以 Google AI Edge 为参照）

### 2.1 嵌入层

（[Embedding Models 文档](https://developers.google.com/edge/litert-lm/embedding_models)）

- **EmbeddingGemma 2**：文本 270M / 文本+视觉 440M / **omnimodal 740M**（文本/图像/音频投进同一向量空间）；768 维输出；CPU/GPU/NPU 均可跑
- 上一代 **Gecko**（tflite，256/1024 序列，float/量化版）仍广泛使用
- 亮点设计：**不对称任务指令前缀**（`task: search result | text:` vs `task: search query | text:`）——同一模型区分索引与检索角色
- 云端备选：Gemini Embedder（API）——端云嵌入可混合

### 2.2 存储与检索层

（[AI Edge RAG 指南](https://developers.google.com/edge/mediapipe/solutions/genai/rag/android) / [Semantic Retriever](https://developers.google.com/edge/mediapipe/solutions/retrieval/semantic_retriever)）

- 官方默认 **SQLite 向量库**（768 维余弦相似度，exact KNN）；生态备选 sqlite-vec、Qdrant Lite（HNSW 近似）、FAISS
- 自动分块：默认 512 字符、100 重叠，保留父子关系（命中 chunk、返回父记录）
- 多模态摄取：文本/图片/音频统一入库

### 2.3 生成层

- 任意 LiteRT-LM 支持的 SLM（Gemma 3 1B/3n 等）+ RAG 管线组装（PromptBuilder + SemanticTextMemory，各环节可替换）

### 2.4 产品化样本

- **AI Edge Gallery**（Android/iOS demo App）：即时媒体搜索、视频时刻定位
- **AI Edge Foresight**：个人知识库检索的产品形态
- Apple 对应物：Spotlight 语义索引 + App Intents Entity schemas（内容层向系统索引贡献实体，见 [[端侧Agent与工具调用]]）——**Apple 走"系统级索引+意图"，Google 走"App 内 RAG 库"**

## 3. 个性化记忆（Memory）的谱系

端侧"记住用户"有三个层次，RAG 只是其一：

| 层次 | 机制 | 代表 |
|---|---|---|
| **事实记忆** | 向量库 + 检索 | AI Edge RAG、Foresight |
| **会话记忆** | KV cache 持久化 / 会话转录（transcript） | Apple Foundation Models 的 stateful session |
| **偏好记忆** | LoRA 适配器 / 用户画像注入 | Apple 端侧 LoRA 热切换；天玑端侧训练 |

值得注意的交叉点：**KV cache 持久化跨会话复用**（云端 prefix caching 的端侧化）在学术系统调研中已列为方向（[LLM 推理系统综述 arXiv:2506.21901](https://arxiv.org/html/2506.21901) §4.4 cache persistence）——系统 prompt/个人上下文的 KV 只算一次，是端侧长上下文的省算力关键（见 [[KV cache与长上下文]]）。

## 4. 关键洞察

1. **嵌入模型是端侧的"隐形基础设施工"**：比生成模型小一个量级（270M vs 3B）、跑得飞快、多模态统一空间解锁跨模态搜索——它决定了端侧 RAG 的能力上限
2. **"个人语料"改变 RAG 的设计约束**：规模小（千页级而非十亿页）、更新频繁、隐私绝对优先——云端 RAG 的 ANN 索引优化、大规模分片在这里全是过度设计，exact KNN + SQLite 反而够用
3. **可溯源在端侧有额外价值**：小模型幻觉率高，引用来源（"根据你的 XX 文档"）既是信任机制也是纠错接口
4. **记忆的隐私责任主体是 OS 而非 App**：Apple 把语义索引/实体放进系统层（Spotlight + App Intents），App 只贡献不拥有——这个边界划分将成 为端侧记忆的主流治理模式

## 5. 开放问题

- [ ] 个人记忆的遗忘机制（被遗忘权在向量库里的实现：删除文档 ≠ 删除嵌入影响）
- [ ] 跨 App 记忆共享的权限模型（哪个 App 能读哪个 App 贡献的记忆）
- [ ] 长期记忆的整理/压缩（记忆蒸馏：把检索库压缩成稳定摘要）
- [ ] 端云 RAG 混合（个人数据端侧检索 + 公共知识云侧检索的合并排序）

## 6. 来源

- [Google AI Edge RAG 指南（Android）](https://developers.google.com/edge/mediapipe/solutions/genai/rag/android)
- [LiteRT-LM Embedding Models（EmbeddingGemma 2）](https://developers.google.com/edge/litert-lm/embedding_models)
- [MediaPipe Semantic Retriever](https://developers.google.com/edge/mediapipe/solutions/retrieval/semantic_retriever)
- [Google 开发者博客：端侧 SLM + RAG + Function Calling](https://developers.googleblog.com/en/google-ai-edge-small-language-models-multimodality-rag-function-calling/)
- [AI Edge Gallery 向量库需求讨论（issue #290）](https://github.com/google-ai-edge/gallery/issues/290)
- [Flutter Edge AI: Embeddings & RAG（生态侧文档）](https://flutteredge.ai/docs/embeddings-and-rag)
- [A Survey of LLM Inference Systems（cache persistence）](https://arxiv.org/html/2506.21901)
