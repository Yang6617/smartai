# 文本解析集群 (Parsing Cluster)

## 概述

文本解析集群是文档预处理器模块的核心组件，负责将各种格式的文档解析为标准化的Element对象列表。该集群采用插件式架构，支持多种文档格式的解析。

## 目录结构

```
parsing_cluster/
├── __init__.py           # 模块初始化，导出公共接口
├── processor.py          # 核心框架定义（DocumentParser, Element等）
├── config.py             # 配置定义
├── utils.py              # 工具函数
├── markdown_parser.py    # Markdown格式解析器
├── plain_text_parser.py  # 纯文本格式解析器
├── element.md            # Element对象设计规范
test/                 # 测试文件目录
├── example_parsing_cluster.py    # 使用示例
├── usage_example_parsing.py      # 使用示例
├── test_doc_preprocessor.py      # 基础功能测试
└── test_parsing_cluster.py       # 解析集群功能测试
```

## 核心组件

### Element对象
Element是解析集群的基本输出单位，包含以下字段：

- **必需字段**：
  - `raw_content`: 原始文本内容
  - `element_type`: 元素类型（heading, paragraph, list_item等）
  - `element_index`: 全局顺序索引
  - `source_format`: 源文件格式

- **强烈推荐字段**：
  - `format_metadata`: 解析元数据字典
  - `parser_confidence`: 解析置信度

- **内部生成字段**：
  - `element_id`: 元素唯一标识符

### 解析器接口 (DocumentParser)
所有解析器都必须实现此接口，包含以下方法：
- `parse(file_path, user_id, knowledge_base_id)`: 解析文档并返回Element列表
- `get_supported_formats()`: 返回支持的文件格式列表

## 支持的格式

- Markdown (.md, .markdown)
- 纯文本 (.txt)
- HTML (.html)
- 图片格式 (.jpg, .jpeg, .png, .bmp, .tiff, .webp) - 通过PaddleOCR支持

## 扩展新格式

要添加对新文档格式的支持，只需继承`DocumentParser`类并实现相应的方法：

```python
from .processor import DocumentParser, ParseResult, Element

class NewFormatParser(DocumentParser):
    def parse(self, file_path, user_id, knowledge_base_id):
        # 实现解析逻辑
        elements = []
        # ... 解析文档内容为Element对象列表
        return ParseResult(user_id, file_name, knowledge_base_id, elements).to_dict()
    
    def get_supported_formats(self):
        return ['.newformat']
```

## 图片解析器 (ImageParser)

图片解析器使用PaddleOCR库来识别图片中的文本内容。目前实现了以下功能：

- 支持多种图片格式 (.jpg, .jpeg, .png, .bmp, .tiff, .webp)
- 使用PaddleOCR进行文字识别和角度分类
- 输出标准化的Element对象，包含文本内容、坐标位置和置信度
- 自动检测表格相关内容

注意：在某些环境中可能存在PaddlePaddle版本兼容性问题，导致OCR功能无法正常使用。如遇此问题，建议：

1. **环境变量设置**：在启动应用程序前设置环境变量禁用PIR执行器
   ```bash
   # Windows
   set ENABLE_PIR=0
   python your_script.py
   
   # 或者在Linux/Mac
   export ENABLE_PIR=0
   python your_script.py
   ```

2. **降级PaddlePaddle版本**：
   ```bash
   pip uninstall paddlepaddle
   pip install paddlepaddle==2.4.2
   ```

3. **更新到最新版本**：
   ```bash
   pip install --upgrade paddlepaddle paddleocr
   ```

4. **检查兼容性**：确认你的系统环境与PaddlePaddle兼容

## 使用示例

```python
from core.doc_preprocessor.parsing_cluster import DocumentProcessor, MarkdownParser, PlainTextParser

# 创建文档处理器
processor = DocumentProcessor()

# 注册解析器
processor.register_parser(MarkdownParser())
processor.register_parser(PlainTextParser())

# 处理文档
result = processor.process_document("example.md", "user123", "team456")
# result格式: {"user_id": str, "file_name": str, "knowledge_base_id": str, "elements": List[Element]}
```

## 设计原则

1. **一致性**：所有解析器输出统一的Element格式
2. **可扩展性**：易于添加新格式的解析器
3. **可维护性**：模块化设计，职责分离
4. **可靠性**：包含完整的错误处理和测试覆盖