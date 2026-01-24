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
├── scripts/                          # 初始化数据库的脚本
│   ├── db_design.md
│   ├── init_chromadb_local.py        # 完整初始化脚本（创建结构+示例数据）
│   ├── init_chromadb_structure_only.py # 仅结构初始化脚本（仅创建数据库结构，不含示例数据）
│   └── reset_chromadb.py             # 重置数据库脚本（清空数据，保留结构）
└── test/                             # 该模块的所有测试脚本
    ├── test_vector_db.py             # 单元测试脚本
    ├── test_db_operations.py         # 功能测试脚本
    ├── test_complete_interface.py    # 完整接口功能验证脚本
    └── verify_persistence.py         # 数据持久性验证脚本
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

### 2. 脚本 (scripts/)
- `init_chromadb_local.py`: 完整初始化脚本（创建数据库结构+添加示例数据，用于开发/演示）
- `init_chromadb_structure_only.py`: 仅结构初始化脚本（仅创建数据库结构，不添加任何示例数据，用于生产环境）
- `reset_chromadb.py`: 重置数据库脚本（清空所有数据，保留数据库结构）

### 3. 测试 (test/)
- `test_vector_db.py`: 单元测试脚本
- `test_db_operations.py`: 功能测试脚本
- `test_complete_interface.py`: 完整接口功能验证脚本
- `verify_persistence.py`: 数据持久性验证脚本

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