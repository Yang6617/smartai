# Core 目录模型端设计文档

## 概述

`core` 目录实现了基于 RAG (Retrieval-Augmented Generation) 技术的知识库问答系统，包含文档预处理、向量处理和 RAG 推理三大核心引擎。

## 核心架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Service Layer (服务层)                              │
│  • core/service_interface.py - 核心服务接口                                 │
│    - upload_file_interface() - 文件上传接口                                 │
│    - ask_question_interface() - 问答接口                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Core Engine (核心引擎)                                 │
│  • doc_preprocessor - 文档预处理引擎                                        │
│  • vector_engine - 向量引擎                                                 │
│  • rag_engine - RAG 引擎                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Data Layer (数据层)                                  │
│  • SQLite - 关系型数据库 (用户、群组、文件记录等)                           │
│  • ChromaDB - 向量数据库 (向量、元数据)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 核心引擎

### 1. 文档预处理引擎 (doc_preprocessor)

**功能**: 处理上传的文件，将其转换为适合向量化的文本块

**主要组件**:
- `format_router`: 格式路由分发器
- `parsing_cluster`: 解析器集群 (Markdown/文本/图像)
- `text_cleaner`: 文本清洗器
- `chunking_engine`: 分块引擎

**处理流程**:
```
用户上传文件
    ↓
格式路由分发 (识别文件类型)
    ↓
文件解析 (Markdown/文本/图像)
    ↓
文本清洗 (去除噪声)
    ↓
内容分块 (智能分块)
```

**配置**:
```python
{
    "default_chunk_size": 500,  # 默认块大小
    "overlap_size": 50,         # 重叠大小
    "min_chunk_size": 50,       # 最小块大小
    "max_chunk_size": 1000      # 最大块大小
}
```

### 2. 向量引擎 (vector_engine)

**功能**: 将文本块转换为向量并存储到向量数据库

**主要组件**:
- `batch_processor`: 批量向量化处理器
- `embedding_loader`: 嵌入模型加载器
- `vector_db_proxy`: 向量数据库代理

**处理流程**:
```
文本块列表
    ↓
加载嵌入模型 (bge-m3)
    ↓
批量向量化 (生成 1024 维向量)
    ↓
存储到 ChromaDB
```

**配置**:
```python
{
    "model_path": "../../model",        # 模型路径
    "db_type": "chromadb",              # 数据库类型
    "db_path": "../../chroma_data",     # 数据库路径
    "default_model": "bge-m3",          # 默认模型
    "embedding_dimension": 1024         # 向量维度
}
```

### 3. RAG 引擎 (rag_engine)

**功能**: 基于用户提问，从知识库中检索相关信息并生成答案

**主要组件**:
- `orchestrator`: RAG 编排器
- `query_understanding`: 查询理解 (扩展/分类/重写)
- `retrieval`: 检索模块 (向量检索/重排)
- `prompt_builder`: Prompt 构建器
- `llm_client`: LLM 客户端 (DeepSeek)

**处理流程**:
```
用户提问
    ↓
查询理解 (扩展/分类/重写)
    ↓
生成查询向量
    ↓
向量检索 (搜索相似向量)
    ↓
结果重排 (提高相关性)
    ↓
Prompt 组装 (构建提示)
    ↓
LLM 生成 (生成答案)
    ↓
返回答案和引用
```

**配置**:
```python
{
    "collection_name": "knowledge_base_chunks",  # 向量库集合名
    "temperature": 0.2,                          # LLM 采样温度
    "max_tokens": 1024,                          # 最大生成长度
    "top_k": 8                                   # 向量检索 top_k
}
```

## 核心接口

### CoreServiceInterface

**文件**: `core/service_interface.py`

**主要方法**:

#### `upload_file()`
```python
def upload_file(
    file_path: str,
    user_id: str,
    knowledge_base_id: str,
    file_name: Optional[str] = None,
    custom_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**功能**: 文件上传和处理接口

**返回**:
```python
{
    "document_id": "doc_12345678",
    "file_name": "document.md",
    "user_id": "user_123",
    "knowledge_base_id": "kb_456",
    "status": "success",
    "message": "文档处理和存储成功",
    "processed_elements_count": 5,
    "chunk_count": 10,
    "storage_result": {...}
}
```

#### `ask_question()`
```python
def ask_question(
    question: str,
    user_id: str,
    knowledge_base_id: Union[str, int],
    model_alias: str = "default",
    stream: bool = False,
    top_k: Optional[int] = None
) -> Dict[str, Any]
```

**功能**: 问答接口

**返回**:
```python
{
    "status": "success",
    "question": "你的问题",
    "answer": "答案",
    "citations": ["引用列表"],
    "debug": {...}
}
```

### 全局接口函数

```python
from core.service_interface import upload_file_interface, ask_question_interface

# 文件上传
result = upload_file_interface(
    file_path="./document.md",
    user_id="user_123",
    knowledge_base_id="kb_456"
)

# 问答
result = ask_question_interface(
    question="你的问题",
    user_id="user_123",
    knowledge_base_id="kb_456"
)
```

## 快速开始

### 1. 文件上传

```python
from core.service_interface import upload_file_interface

result = upload_file_interface(
    file_path="./document.md",
    user_id="user_123",
    knowledge_base_id="kb_456"
)

if result["status"] == "success":
    print(f"文档ID: {result['document_id']}")
    print(f"分块数量: {result['chunk_count']}")
```

### 2. 问答

```python
from core.service_interface import ask_question_interface

result = ask_question_interface(
    question="你的问题",
    user_id="user_123",
    knowledge_base_id="kb_456"
)

if result["status"] == "success":
    print(f"答案: {result['answer']}")
    print(f"引用: {result['citations']}")
```

## 数据库设计

### SQLite 数据库

**文件**: `backend/fastapi_project/knowledge_system.db`

**主要表**:
- `users`: 用户表
- `knowledge_bases`: 知识库表
- `files`: 文件表
- `groups`: 群组表
- `group_members`: 群组成员表
- `favorites`: 收藏表

### ChromaDB 向量数据库

**目录**: `chroma_data/`

**集合**: `kb_{knowledge_base_id}`

**存储内容**:
- 向量数据 (1024 维)
- 元数据 (文档ID、分块索引、知识库ID等)
- 原始文本内容

## 目录结构

```
core/
├── service_interface.py              # 核心服务接口
├── doc_preprocessor/                 # 文档预处理引擎
│   ├── format_router/               # 格式路由分发器
│   ├── parsing_cluster/             # 解析器集群
│   ├── text_cleaner/                # 文本清洗器
│   └── chunking_engine/             # 分块引擎
├── vector_engine/                    # 向量引擎
│   ├── batch_processor/             # 批量向量化处理器
│   ├── embedding_loader/            # 嵌入模型加载器
│   └── vector_db_proxy/             # 向量数据库代理
└── rag_engine/                       # RAG 引擎
    ├── api/                          # RAG API
    ├── orchestrator.py               # RAG 编排器
    ├── query_understanding/          # 查询理解
    ├── retrieval/                    # 检索模块
    ├── prompt_builder/               # Prompt 构建器
    └── llm_client/                   # LLM 客户端
```

## 关键配置

### VectorDBConfig
```python
{
    "db_type": "chromadb",
    "path": "./chroma_data",  # 数据库路径
    "host": "",  # 主机地址（空字符串表示持久化模式）
    "port": 0,  # 端口
    "pool_size": 10,  # 连接池大小
    "max_overflow": 20  # 最大溢出连接数
}
```

### BatchProcessorConfig
```python
{
    "model_path": "../../model",  # 模型路径
    "db_type": "chromadb",  # 数据库类型
    "db_path": "../../chroma_data",  # 数据库路径
    "default_model": "bge-m3",  # 默认模型
    "default_collection_prefix": "kb_"  # 默认集合前缀
}
```

## 扩展性

### 添加新的解析器
1. 创建新的解析器类
2. 实现 `parse()` 方法
3. 使用 `FormatRouter.register_parser()` 注册

### 添加新的分块策略
1. 实现新的分块算法
2. 在 `SmartChunkingEngine` 中注册
3. 配置分块参数

### 添加新的嵌入模型
1. 在 `EmbeddingModelManager` 中注册
2. 配置模型路径
3. 加载模型

### 添加新的数据库
1. 实现 `VectorDBAdapter` 接口
2. 在 `VectorDBProxy` 中注册
3. 配置数据库连接

## 性能优化

1. **批量处理**: 一次处理多个文本块
2. **模型缓存**: 缓存加载的模型
3. **连接池**: 复用数据库连接
4. **后台任务**: 异步处理文件解析
5. **数据持久化**: 定期保存数据库状态

## 错误处理

所有接口都有完善的错误处理：
- 捕获异常
- 记录错误日志
- 返回错误结果

## 相关文档

- `backend/fastapi_project/README.md` - 后端使用说明
- `backend/fastapi_project/database_design.md` - 数据库设计
- `DOCKER_README.md` - Docker 部署说明

## 总结

`core` 目录实现了完整的文档处理和问答系统，采用分层架构设计，具有良好的扩展性和可维护性。核心服务接口提供了统一的文件上传和问答接口，底层引擎负责具体的处理逻辑。
