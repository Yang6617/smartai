# 文本清洗模块 (Text Cleaner)

文本清洗模块提供对解析后Element对象的标准化清洗功能，确保文本内容的一致性和质量。模块采用分层清洗架构，包含基础清洗器和特定格式清洗器。

## 功能特性

### 1. 空白字符标准化
- 去除首尾空格、制表符、换行符
- 将连续多个空格/制表符转为单个空格
- 将全角空格(U+3000)转为半角空格(U+0020)

### 2. 基础编码规范化
- 将全角英文字母/数字转为半角
- 修复常见乱码字符（如"Â" -> "A"）
- 统一中文标点为全角，英文标点为半角

### 3. 换行符统一
- 将所有换行符（\r\n, \r）统一为 \n
- 移除连续多个换行符（最多保留2个）

### 4. Markdown专用清洗
- **标题格式规范化**：确保 # 后有一个空格，移除标题末尾多余的 # 号
- **代码块格式保留**：保留代码内部格式，仅清理围栏外部空格
- **链接格式修复**：修复Markdown链接中的多余空格
- **列表标记规范化**：确保列表项标记一致性（"- "或"* "）

### 5. OCR专用清洗
- **OCR空格粘连修复**：修复因字符分割导致的错误空格
- **OCR字符错误纠正**：基于上下文纠正常见OCR识别错误
- **上下文感知处理**：区分数字序列和字母上下文中的字符
- **格式选择性处理**：仅处理source_format为"image"的Element

## 模块结构

```
text_cleaner/
├── interfaces.py                 # 清洗器接口定义
├── basic_cleaner.py              # 通用基础清洗器
├── config.py                     # 基础清洗器配置管理
├── markdown_cleaner/             # Markdown专用清洗器子模块
│   ├── interfaces.py             # Markdown专用清洗器接口
│   ├── specific_cleaner.py       # Markdown专用清洗器实现
│   ├── config.py                 # Markdown专用清洗器配置
│   └── test_markdown_cleaner.py  # Markdown清洗器测试
├── ocr_cleaner/                  # OCR专用清洗器子模块
│   ├── interfaces.py             # OCR专用清洗器接口
│   ├── specific_cleaner.py       # OCR专用清洗器实现
│   ├── config.py                 # OCR专用清洗器配置
│   └── # OCR清洗器测试已移至 test/test_ocr_cleaner.py
├── # 基础清洗器使用示例已移至 test/usage_example_text_cleaner.py
├── # 基础清洗器测试已移至 test/test_basic_cleaner.py
└── README.md                     # 本文档
```

## 快速开始

```python
from core.doc_preprocessor.text_cleaner.basic_cleaner import BasicTextCleaner
from core.doc_preprocessor.text_cleaner.config import TextCleanerConfig
from core.doc_preprocessor.parsing_cluster.processor import Element

# 创建测试Element
elements = [
    Element(
        raw_content="  这是一个　　包含全角空格的文本。  ",
        element_type="paragraph",
        element_index=0,
        source_format="text",
        format_metadata={},
        parser_confidence=0.9
    )
]

# 创建清洗器并执行清洗
cleaner = BasicTextCleaner()
cleaned_elements = cleaner.clean(elements)

print(cleaned_elements[0].raw_content)  # 输出: "这是一个 包含全角空格的文本。"
```

## 配置选项

文本清洗器支持多种配置选项：

- `normalize_whitespace`: 是否标准化空白字符
- `remove_leading_trailing`: 是否去除首尾空白
- `convert_full_width_spaces`: 是否转换全角空格
- `normalize_full_width_chars`: 是否转换全角字符
- `fix_common_mojibake`: 是否修复常见乱码
- `unify_punctuation`: 是否统一标点符号
- `normalize_line_breaks`: 是否统一换行符
- `max_consecutive_newlines`: 最大连续换行符数量

### 预设配置

模块提供了几种预设配置：

- `get_default_config()`: 默认配置
- `get_aggressive_config()`: 激进清洗配置（更严格的清洗）
- `get_light_config()`: 轻量清洗配置（较少的清洗）

## 扩展新清洗器

要添加新的清洗器，只需继承`TextCleaner`类并实现相应方法：

```python
from .interfaces import TextCleaner

class MyCustomCleaner(TextCleaner):
    def clean(self, elements):
        # 实现自定义清洗逻辑
        return elements
    
    def get_cleaner_info(self):
        return {
            "name": "MyCustomCleaner",
            "description": "自定义清洗器"
        }
```

## 分层清洗架构

本模块采用分层清洗架构，支持多层级清洗：

1. **第一层 - 基础清洗器** (`BasicTextCleaner`)：处理通用文本格式问题
2. **第二层 - 专用清洗器** (`MarkdownSpecificCleaner`, `OCRSpecificCleaner`)：处理特定格式的专有问题

这种架构允许按需组合不同层级的清洗器，提高模块化程度和可维护性。

## 使用示例

运行基础清洗器使用示例：

```bash
python -m core.doc_preprocessor.test.usage_example_text_cleaner
```

运行Markdown专用清洗器使用示例：

```bash
python -m core.doc_preprocessor.test.usage_example_markdown_cleaner
```

运行OCR专用清洗器使用示例：

```bash
python -m core.doc_preprocessor.test.usage_example_ocr_cleaner
```

运行测试：

```bash
python -m core.doc_preprocessor.test.test_basic_cleaner
python -m core.doc_preprocessor.test.test_markdown_cleaner
python -m core.doc_preprocessor.test.test_ocr_cleaner
```

## 集成使用

文本清洗模块可以轻松集成到文档预处理流程中：

### 单级清洗（仅基础清洗）
```python
# 在文档处理流程中集成基础清洗
from core.doc_preprocessor.parsing_cluster import DocumentProcessor
from core.doc_preprocessor.text_cleaner import BasicTextCleaner

# 处理文档
processor = DocumentProcessor()
result = processor.process_document(file_path, user_id, knowledge_base_id)

# 清洗解析结果
cleaner = BasicTextCleaner()
cleaned_elements = cleaner.clean(result['elements'])

# 更新结果
result['elements'] = cleaned_elements
```

### 两级清洗（基础清洗 + 专用清洗）
```python
# 对于Markdown文档，可以使用两级清洗
from core.doc_preprocessor.parsing_cluster import DocumentProcessor
from core.doc_preprocessor.text_cleaner import BasicTextCleaner
from core.doc_preprocessor.text_cleaner.markdown_cleaner import MarkdownSpecificCleaner

# 处理文档
processor = DocumentProcessor()
result = processor.process_document(file_path, user_id, knowledge_base_id)

# 第一级清洗：基础清洗
basic_cleaner = BasicTextCleaner()
intermediate_elements = basic_cleaner.clean(result['elements'])

# 第二级清洗：Markdown专用清洗
markdown_cleaner = MarkdownSpecificCleaner()
final_elements = markdown_cleaner.clean(intermediate_elements)

# 更新结果
result['elements'] = final_elements
```

### 三级清洗（基础清洗 + OCR清洗/Markdown清洗）
```python
# 对于图像OCR结果，可以使用三级清洗
from core.doc_preprocessor.parsing_cluster import DocumentProcessor
from core.doc_preprocessor.text_cleaner import BasicTextCleaner
from core.doc_preprocessor.text_cleaner.ocr_cleaner import OCRSpecificCleaner

# 处理文档
processor = DocumentProcessor()
result = processor.process_document(file_path, user_id, knowledge_base_id)

# 第一级清洗：基础清洗
basic_cleaner = BasicTextCleaner()
intermediate_elements = basic_cleaner.clean(result['elements'])

# 第二级清洗：OCR专用清洗（仅处理image格式元素）
ocr_cleaner = OCRSpecificCleaner()
final_elements = ocr_cleaner.clean(intermediate_elements)

# 更新结果
result['elements'] = final_elements
```