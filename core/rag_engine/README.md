# rag_engine

> **RAG 推理引擎（Retrieval-Augmented Generation, M3）**  
> 面向知识库问答 / 智能检索 / 微信小程序场景的工程级 RAG 推理模块

---
```angular2html
pip install sentence-transformers
pip install torch
pip install chromadb

```
## 一、模块定位与设计目标

`rag_engine` 是整个系统中的 **RAG 推理核心层**，负责完成从「用户问题」到「最终回答」的完整推理流程，核心目标包括：

- ✅ **检索增强生成（RAG）**：结合向量检索结果进行回答生成
- ✅ **工程可扩展性**：模块解耦，支持替换向量库 / LLM
- ✅ **可解释性**：支持引用（citation）与来源追踪
- ✅ **稳定性与可评估性**：内置评估器、降级与调试信息
- ✅ **前端友好**：适配微信小程序（HTTP + WebSocket）

---

## 二、整体目录结构说明

```text
rag_engine/                                # RAG推理引擎（M3）
├── __init__.py                            # 模块初始化导出
├── config.py                              # 推理配置（top_k、阈值、超时、模板选择等）
├── types.py                               # 标准数据结构（Query/Hit/Answer/Citation等）
├── orchestrator.py                       # 总编排：查询理解 → 混合检索 → Prompt → LLM
├── evaluator.py                          # 置信度 / 覆盖率 / 引用完整性评估（可选）
├── citations.py                          # 引用与来源格式化与校验
│
├── api/                                  # 对外接口层（推荐）
│   ├── __init__.py
│   ├── http_api.py                       # FastAPI HTTP + WebSocket 接口
│   └── rag_service.py                   # ask() 统一服务接口
│
├── query_understanding/                 # 查询理解模块
│   ├── __init__.py
│   ├── intent_classifier.py             # 意图分类（事实 / 总结 / 对比 / 步骤等）
│   ├── query_rewrite.py                 # 查询重写（扩展、纠错、补全）
│   └── context_state.py                 # 多轮上下文与会话状态管理
│
├── retrieval/                            # 混合检索层
│   ├── __init__.py
│   ├── vector_retriever.py              # 向量检索（VectorDBProxy）
│   ├── keyword_retriever.py             # 关键词检索（BM25，可选）
│   ├── fusion.py                        # 结果融合（去重 / 归一 / 排序）
│   ├── filters.py                       # 过滤条件构造（knowledge_base_id 等）
│   └── rerank.py                        # 重排（Cross-Encoder / LLM，可选）
│
├── prompt_builder/                      # Prompt 工程
│   ├── __init__.py
│   ├── templates.py                     # Prompt 模板库（按意图 / 任务类型）
│   ├── assembler.py                     # 上下文拼装（检索片段 + 引用编号）
│   └── safety.py                        # 安全约束 / 防幻觉 / 引用要求
│
└── llm_client/                          # 大模型调用层
    ├── __init__.py
    ├── base.py                          # LLM Client 抽象接口
    ├── deepseek_client.py               # DeepSeek API 实现
    ├── fallback.py                      # 降级策略（失败返回检索片段等）
    └── streaming.py                     # 流式响应封装
```
## 三、核心执行流程（ask 调用链）
```
用户问题
↓
RAGService.ask()
↓
Orchestrator（总编排）
├─ 1) Query Understanding（理解问题）
│   ├─ 意图分类（可选：事实/总结/对比/步骤）
│   ├─ Query Rewrite（可选：扩展/纠错/补全）
│   └─ 上下文注入（多轮对话：history / user_context）
│
├─ 2) Retrieval（找资料）
│   ├─ 构建过滤条件（必做：knowledge_base_id / doc_id / tags）
│   ├─ 向量检索（必做：top_k + 相似度阈值）
│   ├─ 关键词检索（可选：BM25）
│   └─ 融合/重排（可选：去重 + 归一化 + rerank）
│
├─ 3) Prompt Builder（组织上下文）
│   ├─ 模板选择（按意图/场景：QA/总结/对比）
│   ├─ 上下文裁剪（chunk 数/长度上限）
│   ├─ 引用编号生成（[1][2][3]）
│   └─ 安全约束（无资料→拒答/降级策略）
│
├─ 4) LLM Client（DeepSeek）
│   ├─ generate（HTTP 一次性返回）
│   └─ stream（WebSocket 流式返回）
│
└─ 5) Postprocess（后处理）
    ├─ 引用校验（回答中的 [n] 是否合法）
    ├─ 质量评估（可选：grounded/覆盖率/完整度）
    └─ 返回结果（answer + citations + debug）
```
## 四. 核心模块说明



---

### 4.1 config.py —— 推理配置中心（RAG 行为控制面板）

#### 📌 模块职责

`config.py` 定义 **RAG 推理阶段的全部可配置行为参数**，是系统的“策略中枢”。

它不做任何推理逻辑，只回答一个问题：

> **“这一次 RAG 推理应该如何运行？”**

---

#### 📦 典型配置项分类

**1️⃣ 检索相关**

- `collection_name`：向量集合名
- `vector_top_k`：向量检索数量
- `enable_rerank`：是否启用重排

**2️⃣ Prompt 相关**

- `max_context_chunks`：最多使用多少个 chunk
- `max_context_chars`：上下文字符上限
- `require_citation`：是否强制引用

**3️⃣ LLM 调用**

- `temperature`
- `max_tokens`
- `stream_default`

**4️⃣ 稳定性 / 降级**

- `allow_empty_context`
- `fallback_on_llm_error`

**5️⃣ 调试与评估**

- `enable_debug`
- `enable_evaluator`

---

#### 🧠 设计动机

- **避免“魔法常量”散落在代码中**
- 方便：
  - API 层覆盖参数（如 top_k）
  - 多环境（dev / prod）切换
- 为后续：
  - YAML / ENV / 控制台配置
  - A/B Test
  打好基础

---

### 4.2 types.py —— 标准数据结构（RAG 的“协议层”）

#### 📌 模块职责

`types.py` 定义 **跨模块、跨层级的稳定数据结构**，是整个 RAG 系统的“语言规范”。

---

#### 📦 核心数据结构

- `RetrievalChunk`  
  - 检索阶段输出的最小知识单元
- `Citation`  
  - 回答引用的来源信息
- `AskRequest / AskResponse`  
  - ask 接口的逻辑输入 / 输出
- `RAGDebugInfo`  
  - 调试与分析信息
- `AnswerQuality`  
  - 回答质量评估结果

---

#### 🧠 为什么 types.py 非常重要

- **解耦内部实现**
  - Retrieval 内部可以随意改
  - LLM 返回格式可以换
- **API / 前端 / 评估逻辑不受影响**
- 后续可以：
  - 自动生成 OpenAPI Schema
  - 对接前端类型系统
  - 做日志、分析、回放

> types.py = RAG 的“公共协议”，必须稳定、清晰

---

### 4.3 orchestrator.py —— RAG 推理总编排器（中枢大脑）

#### 📌 模块职责

`orchestrator.py` 是 **RAG 推理的核心控制器**，负责“把所有模块串起来”。

它的职责不是做细节，而是 **调度流程**。

---

#### 🔁 推理流程（逻辑顺序）

1. 接收标准化 Query
2. 调用 Query Understanding
3. 构建检索过滤条件
4. 调用 Retrieval（向量 / 混合）
5. 构建 Prompt
6. 调用 LLM（流式 / 非流式）
7. 整理 Answer / Citations / Debug

---





### 4.4 evaluator.py —— 回答质量评估模块（可选但关键）

#### 📌 模块职责

`evaluator.py` 用于评估一次 RAG 回答的质量，回答的问题是：

> **“这个回答值不值得信？”**

---

#### 📦 当前评估维度

- `grounded_score`  
  - 是否基于检索资料
- `citation_coverage`  
  - 使用了多少引用
- `completeness`  
  - 回答是否足够完整





---


### 4.5 citations.py —— 引用与来源系统（可解释性的核心）

#### 📌 模块职责

`citations.py` 解决 RAG 系统中最核心的问题之一：

> **“这个答案是从哪来的？”**

---

#### 📦 核心能力

- 将检索结果映射为 Citation
- 统一引用编号（[1][2][3]）
- 校验回答中引用是否合法
- 提供前端可展示的来源信息

---
## 五、 rag_engine/api
`rag_engine/api` 是 **对外接口层**，负责把推理能力以 **HTTP / WebSocket** 的形式提供给上层（微信小程序/后台管理端/其他服务）。  


### 1. 模块职责

- 提供统一的 `ask()` 服务接口（`RAGService`）
- 暴露 HTTP API：一次性返回（适配微信小程序 `wx.request`）
- 暴露 WebSocket API：流式输出（适配微信小程序实时“打字机”效果）
- 构建会话状态 `ConversationState`，注入 `knowledge_base_id` / `conversation_id` 等上下文信息



### 2. 文件说明

##### 2.1 `rag_service.py`
**定位：** 推理服务封装层（Service Layer）  
**职责：**
- 参数校验、默认值补齐
- 调用 orchestrator 执行完整 RAG 流程
- 输出标准结构：`answer + citations + debug`（非流式）或 `stream + citations + debug`（流式）

**对外核心接口：**
- `RAGService.ask(...)`

**输入要点：**
- `question: str`：用户问题
- `conversation_state: ConversationState`：会话上下文（包含 `knowledge_base_id`）
- `model_alias: str`：embedding 模型别名（或默认）
- `stream: bool`：是否流式（小程序推荐 WebSocket + stream=True）
- `top_k: Optional[int]`：可覆盖默认召回数量

**输出结构（典型）：**
- 非流式：
  ```json
  {"answer": "...", "citations": [...], "debug": {...}}
- 流式：
  ```json
  {"stream": <generator>, "citations": [...], "debug": {...}}
#### 2.2 http_api.py

**定位：** FastAPI 对外接口（HTTP + WebSocket）

`http_api.py` 负责将 RAG 推理能力以 **HTTP 接口与 WebSocket 接口** 的形式对外暴露，  
用于对接微信小程序、Web 前端或其他服务。  
该文件只处理 **请求接入、参数解析、响应封装**，不包含任何推理业务逻辑。

---

##### 提供的端点

- **GET `/healthz`**  
  健康检查接口，用于部署检测与负载均衡探活。

- **POST `/rag/ask`**  
  非流式问答接口，一次性返回完整回答，  
  适用于微信小程序 `wx.request` 等普通 HTTP 请求。

- **WebSocket `/ws/rag/ask`**  
  流式问答接口，服务端按 chunk 推送生成内容，  
  **推荐用于微信小程序，实现“打字机”效果。**

---

##### 请求字段（HTTP / WebSocket 一致）

- `question: str`  
  用户输入的问题，**必填**。

- `knowledge_base_id: Optional[str]`  
  知识库 ID，**强烈建议必填**，用于多租户与数据隔离。

- `conversation_id: Optional[str]`  
  会话 ID，用于多轮对话上下文管理。

- `user_id: Optional[str]`  
  用户标识，可用于日志、限流或审计。


## 六、rag_engine/query_understanding README

`query_understanding` 是 **查询理解层**：在进入检索前，让系统“更懂用户问了什么”。  
该层对外输出结构化的理解结果，用于驱动检索策略与 Prompt 模板选择。


### 1. 模块职责

- 意图分类（问题类型识别）：事实问答 / 总结 / 对比 / 步骤等
- 查询重写：扩展同义词、纠错、补全省略信息，提高召回质量
- 会话状态：多轮对话上下文（history / user_context）注入
---
### 2. 文件说明与接口

#### 2.1 `intent_classifier.py`
**功能：** 对用户问题进行意图分类（可选启用）  
**典型输出：**
- `intent: str`：意图标签（例如 `fact_qa` / `summarize` / `compare` / `how_to`）
- `confidence: float`：置信度
- `signals: dict`：触发信号（规则得分等）
- `language: str`：语言（可选）

**建议接口形态：**
- `class IntentClassifier:`
  - `classify(query: str) -> IntentInfo`

> 若你当前实现为函数式，也可保持函数式，只要输出符合 `types.IntentInfo` 即可。

---

#### 2.2 `query_rewrite.py`
**功能：** 将用户 query 改写为更适合检索的形式（可选启用）  
常见改写策略：
- 同义词扩展（例如“初始化/创建/建表”）
- 纠错（拼写、缩写）
- 补全（将省略主语/对象补全）
- 多候选 expansions（用于检索召回增强）

**建议接口形态：**
- `class QueryRewriter:`
  - `rewrite(query: str, intent: Optional[IntentInfo], state: ConversationState) -> RewriteInfo`

---

#### 2.3 `context_state.py`
**功能：** 多轮对话的上下文状态容器  
用于在推理中携带：
- `knowledge_base_id`（多租户）
- `conversation_id`
- 历史消息（history）
- 用户信息（user_context）

**典型用法：**
- API 层创建 `ConversationState`
- 注入 `knowledge_base_id`
- 交给 `RAGService` / `Orchestrator`

---

### 3. 与下游的连接点

- 输出意图 → `prompt_builder.templates` 选择模板
- 输出 rewrite → `retrieval` 用 rewritten query 做召回
- state.user_context.knowledge_base_id → `retrieval.filters` 构造 where 条件（强隔离）

---

## 七、rag_engine/retrieval 

`retrieval` 是 **检索层**：负责从知识库中找出与问题最相关的证据片段（chunks）。该层是 RAG 效果的“上限决定因素”。

---

### 1. 模块职责

- 向量检索（必做）：调用向量数据库相似度搜索
- 关键词检索（可选）：BM25 等，增强召回多样性
- 过滤条件构造（必做）：多租户隔离（knowledge_base_id）
- 结果融合（可选）：去重 / 归一化 / 合并排序
- 重排 rerank（可选）：cross-encoder / LLM rerank，提升精排质量

---

### 2. 文件说明与接口

#### 2.1 `vector_retriever.py`
**功能：** 向量检索器（主路径）

**输入：**
- `query_text` 或 `query_embedding`（取决于你的实现）
- `knowledge_base_id`（来自 state）
- `top_k`（召回数量）
- 可选阈值（相似度/距离阈值）

**依赖：**
- `VectorDBProxy`：调用 `query_vectors(...)`
- `EmbeddingModelManager`：把 query 编码为向量（如果 retriever 内部做 encoding）

**输出：**
- `List[RetrievalHit]`（内部结构）
- 或转换为 `List[RetrievalChunk]`（对外结构，建议对齐 `types.py`）

---

#### 2.2 `filters.py`
**功能：** 构建向量库 where / where_document 过滤条件（非常关键）

**典型过滤字段：**
- `knowledge_base_id`（必做：隔离不同团队/知识库）
- `document_id`（按文档过滤）
- `source_type / tags / version`（可扩展）

**输出：**
- `where: dict`（metadata 级过滤）
- `where_document: dict`（文档内容过滤，按你向量库能力支持）

---

#### 2.3 `keyword_retriever.py`（可选）
**功能：** 关键词检索（BM25/倒排索引）
- 如果当前没有实现，可先留空或 stub
- 后续接入 elasticsearch / whoosh / 自建倒排均可

---

#### 2.4 `fusion.py`（可选）
**功能：** 融合向量检索与关键词检索结果

典型策略：
- 去重（按 chunk_id 或 document_id+chunk_index）
- 分数归一化
- 加权融合
- 排序截断（top_k）

---

#### 2.5 `rerank.py`（可选）
**功能：** 重排精排
- cross-encoder（更准但慢）
- LLM rerank（更灵活但成本高）

---

### 3. 典型调用方式（上游视角）

Orchestrator 调用检索层通常是：

1) 用 state 构造 filters  
2) 向量检索召回 top_k  
3) （可选）关键词检索补充  
4) （可选）fusion 合并  
5) （可选）rerank 重排  
6) 输出 `RetrievalChunk` 列表给 prompt_builder

---

### 4. 多租户隔离强约束（务必遵守）

- `knowledge_base_id` 必须参与检索过滤（where）
- 否则会出现“跨团队召回数据”的严重问题

---

## 八、rag_engine/prompt_builder 

`prompt_builder` 是 **提示工程层**：把“检索到的 chunks + 用户问题 + 任务要求”组织为模型最容易遵守的 Prompt，决定了系统是否“可控”、是否“能引用”、是否“少幻觉”。

---

### 1. 模块职责

- 模板库管理：按意图/任务类型选模板
- 上下文拼装：把 chunks 按格式组织，并编号引用 [1][2][3]
- 安全约束：明确禁止编造、要求引用、无资料则拒答/降级
- 上下文裁剪：控制 token/字符上限，避免提示过长导致截断

---

### 2. 文件说明与接口

#### 2.1 `templates.py`
**功能：** Prompt 模板库

通常至少包含：
- System Prompt（角色/行为约束）
- User Prompt（问题 + 上下文占位）

模板可以按：
- intent（事实/总结/对比/步骤）
- 场景（客服/内部文档/代码问答）

**对外接口建议：**
- `get_template(intent: str) -> PromptTemplate`
- 或导出 `DEFAULT_TEMPLATES`

> 注意：如果 orchestrator 依赖 `from rag_engine.prompt_builder import DEFAULT_TEMPLATES`  
> 建议在 `prompt_builder/__init__.py` 中显式导出，避免导入问题。

---

#### 2.2 `assembler.py`
**功能：** Prompt 拼装器（核心）

输入：
- `question`
- `retrieved_chunks`（列表）
- `template`
- `max_context_chunks / max_context_chars`

输出：
- `messages: List[{"role": "...", "content": "..."}]`

关键行为：
- 为每个 chunk 编号：`[1] ...`、`[2] ...`
- 将编号与 sources 对应，供 citations 后处理
- 控制上下文长度：
  - 先截断 chunk 数
  - 再裁剪字符

---

#### 2.3 `safety.py`
**功能：** 安全约束策略

典型策略：
- 强制模型只基于提供的资料回答
- 无资料时拒答（或返回“未找到相关资料”）
- 处理注入攻击（提示用户/忽略恶意指令）

输出：
- 约束性的 system 规则（或在模板中体现）
- 以及在极端情况下触发拒答/降级

---

### 3. 输出与下游接口

Prompt Builder 的输出应与 `llm_client` 的输入对齐：

- `messages: List[Dict[str, str]]`
  - role: system/user/assistant
  - content: 文本内容

---

## 九、rag_engine/llm_client 

`llm_client` 是 **大模型调用层**：对接 DeepSeek 等 LLM，并提供统一抽象接口，支持非流式与流式两种调用方式。  


---

### 1. 模块职责

- 定义 LLM Client 抽象接口（可替换不同模型）
- DeepSeek API 具体实现（OpenAI 风格 chat completions）
- 提供流式输出能力（用于 WebSocket）
- 提供降级/失败策略（可选：重试/熔断/兜底）

---

### 2. 文件说明与接口

#### 2.1 `base.py`
**功能：** 抽象接口定义

建议约定最小接口：

- `generate(messages, temperature, max_tokens, **kwargs) -> dict/response`
- `stream(messages, temperature, max_tokens, **kwargs) -> Iterable[str]`

这样上层（orchestrator）只依赖抽象，不绑定 DeepSeek。

---

#### 2.2 `deepseek_client.py`
**功能：** DeepSeek API 调用实现（核心）

配置方式（强制）：
- 环境变量：`DEEPSEEK_API_KEY`
- 初始化时读取 `os.getenv("DEEPSEEK_API_KEY")`
- Base URL 常用：`https://api.deepseek.com`
- Endpoint：`/v1/chat/completions`

接口：
- `generate(...)`：非流式（HTTP 场景）
- `stream(...)`：流式（WebSocket 场景）

输出约定建议：
- `generate` 返回：
  - `{"text": "...", "raw": {...}}`
- `stream` yield：
  - `"token or chunk"`

---

#### 2.3 `streaming.py`
**功能：** 流式响应封装（可选）
- 用于统一 chunk 处理
- 统一将不同 provider 的流式格式转为纯文本 chunk

---

#### 2.4 `fallback.py`
**功能：** 降级策略（可选）
- 请求失败自动重试（指数退避）
- 429/5xx 熔断保护
- 失败时返回友好错误或兜底回答

---

### 3. 与上游的接口契约

Orchestrator/Service 层只依赖：

- `messages: List[Dict[str,str]]`
- `llm_client.generate(...)` 或 `llm_client.stream(...)`


---






