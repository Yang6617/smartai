# 解析集群输出格式：Element对象设计规范

## 1. 核心概念定义

**Element（格式元素）**：指从源文件中识别出的、具有特定语义的最小逻辑单元，是解析集群的基本输出单位。

## 2. Element对象标准字段

### 2.1 必需字段（必须包含）

| 字段名 | 数据类型 | 描述 | 约束 |
|--------|----------|------|------|
| **raw_content** | 字符串 | 从源文件中提取的、未经任何处理的原始文本内容。 | 非空字符串 |
| **element_type** | 字符串 | 元素的逻辑类型标识，基于格式语义定义。 | 必须为预定义的类型值 |
| **element_index** | 整数 | 元素在原始文档解析流中的全局顺序索引。 | 从0开始，连续递增 |
| **source_format** | 字符串 | 源文件的格式类型。 | "markdown", "plain_text", "image" |

### 2.2 强烈推荐字段（建议包含）

| 字段名 | 数据类型 | 描述 | 约束 |
|--------|----------|------|------|
| **format_metadata** | 字典 | 解析过程中产生的、对该元素后续处理至关重要的专有信息字典。 | 可为空字典，但必须存在 |
| **parser_confidence** | 浮点数 | 解析器对此元素提取准确性的置信度。 | 0.0到1.0之间 |

### 2.3 可选字段（根据需要包含）

| 字段名 | 数据类型 | 描述 |
|--------|----------|------|
| **element_id** | 字符串 | 元素的全局唯一标识符。 |
| **parent_references** | 列表 | 指向父元素的引用列表（用于树形结构）。 |
| **raw_position** | 整数 | 在原始文件中的字节偏移量或行号。 |

## 3. element_type 预定义值

### 3.1 Markdown格式的元素类型
- **heading**: 标题（H1-H6）
- **paragraph**: 段落
- **list_item**: 列表项
- **code_block**: 代码块
- **blockquote**: 引用块
- **table**: 表格
- **horizontal_rule**: 水平分割线
- **html_block**: HTML块
- **link_definition**: 链接定义

### 3.2 纯文本格式的元素类型
- **paragraph**: 段落
- **section_header**: 章节标题（通过启发式规则识别）
- **list_item**: 列表项（通过前缀识别）

### 3.3 图片格式的元素类型
- **text_region**: 文本区域（OCR识别出的连续文本块）
- **table_region**: 表格区域
- **caption**: 图片标题/说明文字
- **diagram_element**: 图表元素（流程图、架构图等）
- **form_field**: 表单字段（如输入框标签）

## 4. format_metadata 字典内容规范

### 4.1 通用元数据（所有格式可共用）
| 字段名 | 数据类型 | 描述 |
|--------|----------|------|
| **detected_language** | 字符串 | 检测到的文本语言代码，如"zh-CN"、"en-US"。 |
| **character_count** | 整数 | 原始内容的字符数。 |
| **is_structural** | 布尔值 | 是否为结构性元素（影响文档布局）。 |

### 4.2 Markdown格式专属元数据
#### heading元素
| 字段名 | 数据类型 | 描述 |
|--------|----------|------|
| **heading_level** | 整数 | 标题级别（1-6）。 |
| **syntax_raw** | 字符串 | 原始标记语法（如"##", "###"）。 |
| **heading_id** | 字符串 | 标题的锚点ID（如自动生成的slug）。 |

#### code_block元素
| 字段名 | 数据类型 | 描述 |
|--------|----------|------|
| **language** | 字符串 | 代码语言标识（如"python", "javascript"）。 |
| **fence_char** | 字符串 | 代码围栏字符（如"```", "~~~"）。 |
| **info_string** | 字符串 | 代码围栏后的信息字符串。 |

#### table元素
| 字段名 | 数据类型 | 描述 |
|--------|----------|------|
| **column_count** | 整数 | 表格列数。 |
| **row_count** | 整数 | 表格行数（包括表头）。 |
| **alignment** | 列表 | 列对齐方式列表，如["left", "center", "right"]。 |

### 4.3 图片格式专属元数据
#### text_region元素
| 字段名 | 数据类型 | 描述 |
|--------|----------|------|
| **bbox** | 列表[整数] | 文本区域在原图中的坐标[x1, y1, x2, y2]。 |
| **ocr_confidence** | 浮点数 | OCR引擎对该区域的识别置信度。 |
| **font_attributes** | 字典 | 字体属性，如{"size": 12, "bold": true, "italic": false}。 |
| **text_direction** | 字符串 | 文本方向，如"horizontal", "vertical"。 |

#### table_region元素
| 字段名 | 数据类型 | 描述 |
|--------|----------|------|
| **bbox** | 列表[整数] | 表格区域在原图中的坐标。 |
| **cell_count** | 字典 | 单元格数量，如{"rows": 5, "cols": 3}。 |
| **has_border** | 布尔值 | 是否有可见边框。 |

## 5. 完整Element对象示例

### 示例1：Markdown标题元素
```json
{
  "element_id": "md_elem_001",
  "raw_content": "# 产品功能介绍",
  "element_type": "heading",
  "element_index": 0,
  "source_format": "markdown",
  "format_metadata": {
    "heading_level": 1,
    "syntax_raw": "#",
    "heading_id": "产品功能介绍",
    "detected_language": "zh-CN",
    "character_count": 7,
    "is_structural": true
  },
  "parser_confidence": 1.0,
  "raw_position": 0
}
```

### 示例2：Markdown代码块元素
```json
{
  "element_id": "md_elem_005",
  "raw_content": "```python\ndef hello():\n    print(\"Hello World\")\n```",
  "element_type": "code_block",
  "element_index": 4,
  "source_format": "markdown",
  "format_metadata": {
    "language": "python",
    "fence_char": "```",
    "info_string": "python",
    "detected_language": "en-US",
    "character_count": 45,
    "is_structural": true
  },
  "parser_confidence": 0.95,
  "raw_position": 125
}
```

### 示例3：图片文本区域元素
```json
{
  "element_id": "img_elem_002",
  "raw_content": "系统响应时间 < 100ms",
  "element_type": "text_region",
  "element_index": 1,
  "source_format": "image",
  "format_metadata": {
    "bbox": [120, 250, 380, 280],
    "ocr_confidence": 0.92,
    "font_attributes": {
      "size": 14,
      "bold": false,
      "italic": false
    },
    "text_direction": "horizontal",
    "detected_language": "zh-CN",
    "character_count": 11,
    "is_structural": false
  },
  "parser_confidence": 0.92,
  "raw_position": null
}
```

### 示例4：纯文本段落元素
```json
{
  "element_id": "txt_elem_003",
  "raw_content": "  项目于2023年第一季度启动。主要目标是提升团队协作效率。  ",
  "element_type": "paragraph",
  "element_index": 2,
  "source_format": "plain_text",
  "format_metadata": {
    "detected_language": "zh-CN",
    "character_count": 30,
    "is_structural": false,
    "line_number_start": 15
  },
  "parser_confidence": 1.0,
  "raw_position": 156
}
```

## 6. 解析集群输出格式

解析集群的整体输出是一个包含多个Element对象的列表，通常包装在一个容器对象中：

```json
{
  "parse_id": "parse_20240510123000_001",
  "document_id": "doc_001",
  "source_file": "product_intro.md",
  "source_format": "markdown",
  "timestamp": "2024-05-10T12:30:00Z",
  "elements": [
    { /* Element对象1 */ },
    { /* Element对象2 */ },
    { /* Element对象3 */ }
  ],
  "summary": {
    "total_elements": 15,
    "element_type_distribution": {
      "heading": 3,
      "paragraph": 8,
      "code_block": 2,
      "table": 1,
      "list_item": 1
    },
    "processing_time_ms": 245
  }
}
```

## 7. 设计原则与注意事项

1. **保持原始性**：`raw_content`字段必须保持从源文件中提取时的原始状态，不做任何修改。
2. **信息完整性**：`format_metadata`应包含所有对后续处理有价值的信息。
3. **类型安全性**：`element_type`必须使用预定义的值，便于下游模块进行模式匹配。
4. **顺序保持**：`element_index`必须准确反映元素在原始文档中的出现顺序。
5. **可扩展性**：设计允许通过扩展`format_metadata`来支持新的格式或元素类型，而无需修改整体结构。

此设计确保了解析集群输出的一致性、可解释性和可处理性，为下游的清洗、分块和向量化模块提供了清晰、丰富的数据基础。