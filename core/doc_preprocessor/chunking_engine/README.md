# 智能分块引擎

智能分块引擎是一个用于将长文本分割为适合向量化片段的模块。它采用三层架构设计，能够根据内容类型智能调整分块策略，并保持上下文连续性。

## 功能特点

1. **语义边界检测**
   - 自动识别Markdown标题、列表、代码块等结构边界
   - 识别通用文本中的段落、项目符号、缩进等边界
   - 利用现有结构标记作为强语义边界

2. **自适应分块**
   - 根据内容类型调整块大小和策略
   - 代码块：整块保留，避免分割
   - 表格：可选择整块保留或按行分割
   - 段落：按固定token数分割

3. **重叠控制**
   - 防止分割切断上下文连接
   - 在相邻块之间添加重叠内容
   - 支持简单重叠和语义重叠两种模式

## 架构设计

```
智能分块引擎
├── 语义边界检测模块 (boundary_detector)
│   ├── Markdown边界检测器
│   └── 通用文本边界检测器
├── 自适应分块模块 (adaptive_chunker)
│   ├── 代码块分块器
│   ├── 表格分块器
│   ├── 段落分块器
│   └── 固定大小分块器
├── 重叠控制模块 (overlap_controller)
│   ├── 简单重叠控制器
│   └── 语义重叠控制器
└── 主引擎 (engine.py)
    └── 整合所有功能
```

## 使用示例

### 基本用法

```python
from core.doc_preprocessor.chunking_engine.engine import SmartChunkingEngine
from core.doc_preprocessor.parsing_cluster.processor import Element

# 创建分块引擎
engine = SmartChunkingEngine()

# 准备Element列表
elements = [
    Element(
        raw_content="这是待分块的文本内容...",
        element_type="paragraph",
        element_index=0,
        source_format="text",
        format_metadata={},
        parser_confidence=0.85
    )
]

# 执行分块
result = engine.chunk_elements(
    elements=elements,
    document_id="doc_001",
    team_id="team_abc",
    user_id="user_1234",
    file_name="示例文档.md",
    file_type="markdown"
)

# 输出结果
print(result)
```

### 高级用法 - 结构感知分块

```python
# 使用结构感知分块，自动检测文档结构
result = engine.chunk_text_with_structure_detection(
    text=markdown_text,
    file_type="markdown",
    document_id="doc_002",
    team_id="team_xyz",
    user_id="user_5678",
    file_name="结构测试.md",
    overlap_size=30  # 设置重叠大小
)
```

### 自定义配置

```python
from core.doc_preprocessor.chunking_engine.adaptive_chunker.chunker import ChunkConfig

# 自定义配置
config = ChunkConfig(
    default_chunk_size=200,        # 默认分块大小
    preserve_code_blocks=True,     # 保持代码块完整
    table_chunk_strategy="row_split",  # 表格按行分割
    include_headers_in_chunks=True     # 在块中包含标题信息
)

engine = SmartChunkingEngine(config=config)
```

## 输出格式

分块结果遵循以下JSON格式：

```json
{
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
            "element_type": "paragraph",
            "chunk_type": "text",
            "metadata": {...},
            "overlap_info": {...},
            "confidence": 0.85
        }
    ]
}
```

## 模块说明

- `boundary_detector`: 负责检测文本中的语义边界
- `adaptive_chunker`: 根据内容类型执行自适应分块
- `overlap_controller`: 控制相邻块之间的重叠
- `chunk.py`: 定义分块对象和输出格式
- `engine.py`: 主引擎，整合所有功能
- `test/test_chunking_engine.py`: 单元测试
- `test/usage_example_chunking.py`: 使用示例

## 测试

运行测试套件：

```bash
python -m core.doc_preprocessor.chunking_engine.test_chunking_engine
```

## 设计原则

1. **可扩展性**: 通过工厂模式支持不同类型的检测器、分块器和控制器
2. **灵活性**: 支持多种配置选项，适应不同场景需求
3. **结构性**: 维护文档的层次结构信息
4. **连续性**: 通过重叠控制保持上下文连续性
5. **高效性**: 针对不同内容类型优化分块策略