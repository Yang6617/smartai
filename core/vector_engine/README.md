# 向量数据库代理

## 目录结构

```
vector_engine/
├── db_design.md                       # 数据库设计规范
├── README.md                         # 本文件
├── vector_db_proxy/                  # 向量数据库代理核心组件
│   ├── adapters.py                   # 其他向量数据库适配器（Pinecone, Weaviate, FAISS等）
│   ├── chromadb_adapter.py           # ChromaDB 适配器实现
│   ├── config.py                     # 配置类定义
│   ├── interfaces.py                 # 抽象接口定义
│   ├── pool_manager.py               # 连接池管理器
│   ├── proxy.py                      # 主代理类
│   ├── stability.py                  # 稳定性功能
│   └── __init__.py                   # 包初始化
├── embedding_loader/                 # 嵌入模型加载模块
│   ├── __init__.py                   # 包初始化
│   ├── loader.py                     # 嵌入模型加载器
│   ├── model_manager.py              # 嵌入模型管理器
│   ├── config.py                     # 模型配置
│   └── utils.py                      # 辅助工具函数
├── batch_processor/                  # 批量向量化处理模块
│   ├── __init__.py                   # 包初始化
│   ├── processor.py                  # 批量处理器
│   ├── config.py                     # 处理器配置
│   └── example.py                    # 使用示例
├── scripts/                          # 初始化数据库的脚本
│   ├── db_design.md
│   ├── init_chromadb_local.py        # 完整初始化脚本（创建结构+示例数据）
│   ├── init_chromadb_structure_only.py # 仅结构初始化脚本（仅创建数据库结构，不含示例数据）
│   └── reset_chromadb.py             # 重置数据库脚本（清空数据，保留结构）
└── test/                             # 该模块的所有测试脚本
    ├── test_vector_db.py             # 向量数据库代理单元测试脚本
    ├── test_db_operations.py         # 向量数据库代理功能测试脚本
    ├── test_complete_interface.py    # 向量数据库代理完整接口功能验证脚本
    ├── verify_persistence.py         # 数据持久性验证脚本
    ├── test_embedding_loader.py      # 嵌入模型加载模块测试脚本
    └── test_batch_processor.py       # 批量向量化处理模块测试脚本
```

## 相关模块

本模块与以下模块协同工作：

- `core/embedding_loader/` - 嵌入模型加载模块：提供动态加载和管理预训练嵌入模型的功能，支持BGE-M3等模型，用于生成向量嵌入。

### 嵌入模型加载模块 (embedding_loader/)

嵌入模型加载模块提供了动态加载、管理和使用预训练嵌入模型的能力，特别针对BGE-M3等先进模型进行了优化。

**核心组件：**
- `loader.py`: 嵌入模型加载器，负责实际的模型加载和设备管理
- `model_manager.py`: 嵌入模型管理器，提供高级模型管理功能（加载、卸载、别名管理等）
- `config.py`: 模型配置管理，定义模型配置参数
- `utils.py`: 辅助工具函数，提供路径处理、模型验证等功能

**主要特性：**
- **动态加载/卸载**: 支持在运行时动态加载和卸载模型，节省内存资源
- **设备自适应**: 自动检测并使用GPU（CUDA）或CPU进行推理
- **模型别名**: 支持为模型设置别名，便于管理多个模型实例
- **批量编码**: 支持单文本和批量文本的嵌入编码
- **配置管理**: 支持自定义模型配置参数
- **GPU加速**: 自动利用GPU进行模型推理，显著提升性能

**使用示例：**
```python
from core.vector_engine.embedding_loader import EmbeddingModelManager

# 创建模型管理器
manager = EmbeddingModelManager("../../model")

# 自动选择设备（GPU优先）加载模型
success = manager.load_model("bge-m3", alias="my_bge_m3")
if success:
    # 使用模型进行编码
    embeddings = manager.encode("my_bge_m3", "这是一个示例文本")
    
    # 或者批量编码
    texts = ["文本1", "文本2", "文本3"]
    embeddings = manager.encode("my_bge_m3", texts)
    
    # 使用完毕后卸载模型
    manager.unload_model("my_bge_m3")
```

### 批量向量化处理模块 (batch_processor/)

批量向量化处理模块负责将文本块列表转换为向量并存储到向量数据库中，实现了从原始文本到向量存储的完整流程。

**核心组件：**
- `processor.py`: 批量向量处理器，实现文本向量化和数据库存储的核心逻辑
- `config.py`: 处理器配置，定义批量处理的配置参数

**主要特性：**
- **JSON数据处理**: 接收符合规范的JSON格式文本块列表
- **智能元数据映射**: 自动将输入数据映射到向量数据库所需的元数据格式
- **ID生成策略**: 自动生成唯一且有意义的文本块ID
- **批量处理**: 高效处理大量文本块，减少数据库交互次数
- **错误处理**: 完善的异常处理和错误报告机制

**数据格式映射：**
- 输入数据的 `team_id` → 数据库中的 `knowledge_base_id`
- 输入数据的 `structure_path` → 数据库中的 `source_info`
- 输入数据的 `user_id` → 数据库中的 `uploader_id`
- 输入数据的 `document_id` → 数据库中的 `document_id`

**使用示例：**
```python
from core.vector_engine.batch_processor import BatchVectorProcessor
from core.vector_engine.batch_processor.config import BatchProcessorConfig

# 创建配置
config = BatchProcessorConfig(
    model_path="../../model",
    db_path="../../data/chroma_persistent_data"
)

# 创建批量处理器
processor = BatchVectorProcessor(config)

# 准备输入数据
delivery_data = {
    "document_id": "doc_001", 
    "team_id": "team_abc", 
    "user_id": "user_1234",
    "file_name": "产品介绍.md", 
    "file_type": "markdown", 
    "chunks": [
        {
            "text": "我们的产品支持实时协作...",
            "chunk_index": 0, 
            "structure_path": ["# 功能特色", "## 核心优势"], 
        }
    ] 
}

# 加载模型
processor.load_model("bge-m3", alias="main_model")

# 处理批量数据
result = processor.process_batch(delivery_data, model_alias="main_model")
print(result)

# 卸载模型
processor.unload_model("main_model")
```

## 核心组件

### 1. 核心模块 (vector_db_proxy/)
- `interfaces.py`: 定义了所有向量数据库必须实现的抽象接口
- `config.py`: 数据库配置类
- `chromadb_adapter.py`: ChromaDB 具体实现
- `pool_manager.py`: 连接池管理，确保高效资源利用
- `stability.py`: 稳定性功能，包括重试、健康检查等
- `proxy.py`: 主代理类，整合所有功能组件
- `adapters.py`: 其他向量数据库适配器模板

### 2. 嵌入模型加载模块 (embedding_loader/)
- `loader.py`: 嵌入模型加载器，负责实际的模型加载和设备管理
- `model_manager.py`: 嵌入模型管理器，提供高级模型管理功能（加载、卸载、别名管理等）
- `config.py`: 模型配置管理，定义模型配置参数
- `utils.py`: 辅助工具函数，提供路径处理、模型验证等功能

### 3. 批量向量化处理模块 (batch_processor/)
- `processor.py`: 批量向量处理器，负责将文本块转换为向量并存储到向量数据库
- `config.py`: 处理器配置，定义批量处理的配置参数
- `example.py`: 使用示例，展示如何使用批量处理器
- `test_import.py`: 导入测试，验证模块导入功能
- `test_functionality.py`: 功能测试，验证批量处理器的各项功能

### 3. 脚本 (scripts/)
- `init_chromadb_local.py`: 完整初始化脚本（创建数据库结构+添加示例数据，用于开发/演示）
- `init_chromadb_structure_only.py`: 仅结构初始化脚本（仅创建数据库结构，不添加任何示例数据，用于生产环境）
- `reset_chromadb.py`: 重置数据库脚本（清空所有数据，保留数据库结构）

### 4. 测试 (test/)
- `test_vector_db.py`: 向量数据库代理单元测试脚本
- `test_db_operations.py`: 向量数据库代理功能测试脚本
- `test_complete_interface.py`: 向量数据库代理完整接口功能验证脚本
- `verify_persistence.py`: 数据持久性验证脚本
- `test_embedding_loader.py`: 嵌入模型加载模块测试脚本

## 数据库设计

根据 `db_design.md` 文件，数据库遵循以下结构：

| 字段类别 | 字段名 | 类型 | 说明 |
|---------|--------|------|------|
| 核心向量 | `embedding` | `List[float]` | 由BGE-M3模型生成的768维向量 |
| 原始文本 | `document` | `string` | 原始文本片段内容 |
| 来源元数据 | `metadata` | `dict` | 包含document_id、knowledge_base_id等信息 |
| 唯一标识 | `id` | `string` | 全局唯一ID |

## 使用方法

### 初始化数据库
```bash
cd scripts
python init_chromadb_local.py
```

### 运行测试
```bash
cd test
python test_db_operations.py
```

### 在应用中使用
```python
from core.vector_engine.vector_db_proxy.config import VectorDBConfig
from core.vector_engine.vector_db_proxy.proxy import VectorDBProxy

# 方式1: 手动配置
config = VectorDBConfig(
    db_type="chromadb",
    path="../../data/chroma_persistent_data",  # 根据实际项目结构调整路径
    host="",  # 留空以使用持久化模式
    port=0    # 留空以使用持久化模式
)

proxy = VectorDBProxy(config)
proxy.connect()

# 使用数据库...

# 方式2: 使用便捷函数（推荐）
from core.vector_engine.vector_db_proxy.proxy import create_vector_db_proxy

proxy = create_vector_db_proxy(
    db_type="chromadb",
    path="../../data/chroma_persistent_data",  # 根据实际项目结构调整路径
    host="",  # 使用持久化模式
    port=0    # 使用持久化模式
)
proxy.connect()

# 使用数据库...
```

### 使用嵌入模型
```python
from core.vector_engine.embedding_loader import EmbeddingModelManager

# 创建模型管理器
model_manager = EmbeddingModelManager("../../model")

# 自动选择设备（GPU优先）加载模型
success = model_manager.load_model("bge-m3", alias="my_bge_m3")
if success:
    # 使用模型进行编码
    embeddings = model_manager.encode("my_bge_m3", "这是一个示例文本")
    
    # 或者批量编码
    texts = ["文本1", "文本2", "文本3"]
    embeddings = model_manager.encode("my_bge_m3", texts)
    
    # 使用完毕后卸载模型以释放资源
    model_manager.unload_model("my_bge_m3")
```

### 使用批量向量化处理
```python
from core.vector_engine.batch_processor import BatchVectorProcessor
from core.vector_engine.batch_processor.config import BatchProcessorConfig

# 创建配置
config = BatchProcessorConfig(
    model_path="../../model",
    db_path="../../data/chroma_persistent_data"
)

# 创建批量处理器
processor = BatchVectorProcessor(config)

# 准备输入数据
delivery_data = {
    "document_id": "doc_001", 
    "team_id": "team_abc", 
    "user_id": "user_1234",
    "file_name": "产品介绍.md", 
    "file_type": "markdown", 
    "chunks": [
        {
            "text": "我们的产品支持实时协作...",
            "chunk_index": 0, 
            "structure_path": ["# 功能特色", "## 核心优势"], 
        }
    ] 
}

# 加载模型
processor.load_model("bge-m3", alias="main_model")

# 处理批量数据
result = processor.process_batch(delivery_data, model_alias="main_model")
print(result)

# 卸载模型
processor.unload_model("main_model")
```

## VectorDBProxy 模块接口说明

### VectorDBConfig 配置类
用于配置向量数据库连接参数。

**属性：**
- `db_type`: 数据库类型（如 "chromadb"）
- `host`: 服务器地址（HTTP模式时使用）
- `port`: 服务器端口（HTTP模式时使用）
- `path`: 本地存储路径（持久化模式时使用）
- `pool_size`: 连接池大小
- `max_overflow`: 最大溢出连接数

### VectorDBProxy 主代理类
统一的向量数据库操作接口。

**主要方法：**

#### 连接管理
- `connect() -> bool`: 建立数据库连接
- `disconnect() -> bool`: 断开数据库连接

#### 集合管理
- `create_collection(collection_name: str, metadata: Optional[Dict] = None) -> bool`: 创建集合
- `delete_collection(collection_name: str) -> bool`: 删除集合
- `get_collection(collection_name: str)`: 获取集合对象
- `get_vector_count(collection_name: str) -> int`: 获取集合中的向量数量

#### 向量操作
- `add_vectors(collection_name: str, vectors: List[List[float]], ids: List[str], metadatas: Optional[List[Dict]] = None, documents: Optional[List[str]] = None) -> bool`: 添加向量
- `query_vectors(collection_name: str, query_vector: List[float], n_results: int = 10, where: Optional[Dict] = None, where_document: Optional[Dict] = None) -> List[Dict[str, Any]]`: 查询向量
- `delete_vectors(collection_name: str, ids: List[str], where: Optional[Dict] = None, where_document: Optional[Dict] = None) -> bool`: 删除向量

#### 其他功能
- `reset_database() -> bool`: 重置数据库
- `get_stats() -> Dict[str, Any]`: 获取代理统计信息（包括连接池状态、性能指标和健康状况）
- `create_vector_db_proxy(...)`: 便捷函数，创建带有默认配置的代理实例

## 特性

1. **连接池管理**: 高效管理多个数据库连接
2. **稳定性保障**: 自动重试、健康检查、连接恢复
3. **多数据库支持**: 易于扩展支持其他向量数据库
4. **线程安全**: 支持并发访问
5. **性能监控**: 连接使用统计和性能指标