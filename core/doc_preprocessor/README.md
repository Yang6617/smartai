# 灵析AI - 文档预处理器

## 概述

文档预处理器是灵析AI系统的核心组件之一，负责将各种格式的文档转换为适合向量化和后续处理的标准化格式。该模块采用模块化设计，包含四个主要子系统：格式路由分发、文档解析集群、文本清洗和智能分块引擎。预处理器专为RAG系统优化，确保文档内容的完整性和结构信息的有效保留。

## 架构设计

```
文档预处理器 (Document Preprocessor)
├── 格式路由分发模块 (Format Router)
│   ├── 文件类型识别
│   ├── 解析策略选择
│   ├── 任务队列管理
│   └── 负载均衡
├── 文档解析集群 (Parsing Cluster)  
│   ├── Markdown解析器
│   ├── 纯文本解析器
│   ├── 图像解析器 (OCR)
│   └── Element对象模型
├── 文本清洗模块 (Text Cleaner)
│   ├── 基础清洗器
│   ├── Markdown专用清洗器
│   ├── OCR专用清洗器
│   └── 配置管理
└── 智能分块引擎 (Chunking Engine)
    ├── 语义边界检测
    ├── 自适应分块
    ├── 重叠控制
    └── 结构感知分块
```

## 功能特性

### 1. 格式路由分发模块
- **文件类型识别**：通过扩展名和二进制签名双重验证文件类型
- **策略选择**：根据文件大小和类型自动选择最优解析策略
- **负载均衡**：管理解析任务的优先级队列和负载均衡
- **支持格式**：PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, 图片格式, 文本格式等

### 2. 文档解析集群
- **标准化输出**：将不同格式的文档解析为统一的Element对象列表
- **多格式支持**：Markdown, 纯文本, HTML, 图片(OCR)等
- **元数据保留**：保留格式信息、置信度等元数据
- **插件式架构**：易于扩展新的解析器

### 3. 文本清洗模块
- **多层清洗**：基础清洗 + 专用格式清洗
- **格式标准化**：统一空白字符、标点符号、编码等
- **错误修复**：修复OCR识别错误、乱码等问题
- **配置灵活**：支持多种清洗配置选项

### 4. 智能分块引擎
- **语义边界检测**：识别文档结构边界（标题、列表、代码块等）
- **自适应分块**：根据内容类型调整分块策略
- **重叠控制**：防止上下文切割，保持语义连续性
- **结构感知**：维护文档层次结构信息

## 使用指南

### 基本使用流程

```python
from core.doc_preprocessor.format_router import FormatRouter, Priority
from core.doc_preprocessor.chunking_engine import SmartChunkingEngine

# 1. 使用格式路由器处理文件
router = FormatRouter(max_workers=4)

# 注册解析器（通常在系统初始化时完成）
def text_parser(file_path, user_id, team_id, config):
    # 实现具体的解析逻辑
    pass

router.register_parser(['text/plain'], text_parser)

# 2. 提交文件进行处理
task_id = router.submit_file(
    file_path="example.md",
    user_id="user123",
    team_id="team456",
    priority=Priority.NORMAL
)

# 3. 获取解析结果
result = router.get_task_result(task_id)

# 4. 对解析结果进行分块
engine = SmartChunkingEngine()
chunks = engine.chunk_elements(
    elements=result['elements'],
    document_id="doc_001",
    team_id="team_abc", 
    user_id="user_1234",
    file_name="example.md",
    file_type="markdown"
)
```

### 高级使用 - 完整处理链

```python
from core.doc_preprocessor.parsing_cluster import DocumentProcessor
from core.doc_preprocessor.text_cleaner import BasicTextCleaner
from core.doc_preprocessor.chunking_engine import SmartChunkingEngine

def process_document_complete(file_path, user_id, team_id):
    # 1. 解析文档
    processor = DocumentProcessor()
    
    # 2. 执行解析
    parse_result = processor.process_document(file_path, user_id, team_id)
    
    # 3. 文本清洗
    cleaner = BasicTextCleaner()
    cleaned_elements = cleaner.clean(parse_result['elements'])
    
    # 4. 更新解析结果
    parse_result['elements'] = cleaned_elements
    
    # 5. 智能分块
    chunker = SmartChunkingEngine()
    chunks = chunker.chunk_elements(
        elements=parse_result['elements'],
        document_id=f"doc_{hash(file_path)}",
        team_id=team_id,
        user_id=user_id,
        file_name=parse_result['file_name'],
        file_type="markdown"  # 根据实际情况设置
    )
    
    return chunks
```

### 配置选项

#### 智能分块引擎配置
```python
from core.doc_preprocessor.chunking_engine.adaptive_chunker.chunker import ChunkConfig

config = ChunkConfig(
    default_chunk_size=200,           # 默认分块大小
    preserve_code_blocks=True,        # 保持代码块完整
    table_chunk_strategy="whole",     # 表格分块策略
    paragraph_chunk_size=500,         # 段落分块大小
    overlap_size=30                   # 重叠大小
)

engine = SmartChunkingEngine(config=config)
```

#### 文本清洗配置
```python
from core.doc_preprocessor.text_cleaner.config import TextCleanerConfig

# 使用预设配置
from core.doc_preprocessor.text_cleaner.config import get_aggressive_config

config = get_aggressive_config()
cleaner = BasicTextCleaner(config=config)
```

## 输出格式

### Element对象结构
```python
{
    "raw_content": "原始文本内容",
    "element_type": "元素类型(heading, paragraph, list_item等)",
    "element_index": 0,               # 元素索引
    "source_format": "源格式",        # 如markdown, text等
    "format_metadata": {              # 格式相关的元数据
        "detected_language": "语言",
        "character_count": 100,
        "is_structural": False
    },
    "parser_confidence": 0.95,        # 解析置信度
    "element_id": "元素唯一ID"        # 自动生成
}
```

### Chunk对象结构
```python
{
    "document_id": "文档ID",
    "team_id": "团队ID", 
    "user_id": "用户ID",
    "file_name": "文件名",
    "file_type": "文件类型",
    "chunks": [
        {
            "text": "分块文本内容",
            "chunk_index": 0,          # 分块索引
            "structure_path": [        # 文档结构路径
                "# 主标题",
                "## 子标题"
            ],
            "element_type": "元素类型",
            "chunk_type": "分块类型",
            "metadata": {              # 分块元数据
                "length": 100,
                "word_count": 20,
                "sentence_count": 2
            },
            "overlap_info": {          # 重叠信息
                "prefix": "前缀内容",
                "suffix": "后缀内容"
            },
            "confidence": 0.90         # 处理置信度
        }
    ]
}
```

## 扩展开发

### 添加新的解析器
```python
from core.doc_preprocessor.parsing_cluster.processor import DocumentParser, ParseResult, Element

class NewFormatParser(DocumentParser):
    def parse(self, file_path, user_id, knowledge_base_id):
        # 实现解析逻辑
        elements = []
        
        # 读取并解析文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 创建Element对象
        element = Element(
            raw_content=content,
            element_type="paragraph",
            element_index=0,
            source_format="new_format",
            format_metadata={"custom_field": "value"},
            parser_confidence=0.9
        )
        elements.append(element)
        
        # 返回解析结果
        result = ParseResult(
            user_id=user_id,
            file_name=os.path.basename(file_path),
            knowledge_base_id=knowledge_base_id,
            elements=elements
        )
        return result.to_dict()
    
    def get_supported_formats(self):
        return ['.newformat']
```

### 添加新的清洗器
```python
from core.doc_preprocessor.text_cleaner.interfaces import TextCleaner

class CustomTextCleaner(TextCleaner):
    def clean(self, elements):
        for element in elements:
            # 实现自定义清洗逻辑
            element.raw_content = self.custom_clean_logic(element.raw_content)
        return elements
    
    def custom_clean_logic(self, text):
        # 自定义清洗逻辑
        return text
```

## 性能优化

- **异步处理**：使用任务队列和负载均衡提高并发处理能力
- **内存管理**：流式处理大文件，避免内存溢出
- **缓存机制**：对常用处理结果进行缓存
- **批处理**：支持批量处理多个文档

## 错误处理

- **解析失败**：自动降级到备用解析策略
- **格式不支持**：提供友好的错误提示
- **资源不足**：动态调整处理策略
- **超时处理**：设置合理的超时限制

## 最佳实践

1. **合理配置**：根据文档类型和大小选择合适的配置
2. **渐进处理**：对于大型文档，考虑分阶段处理
3. **监控日志**：记录处理过程中的关键指标
4. **测试验证**：在生产环境部署前充分测试