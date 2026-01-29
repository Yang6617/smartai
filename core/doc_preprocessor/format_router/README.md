# 格式路由分发模块 (Format Router)

## 概述

格式路由分发模块是文档预处理器的重要组成部分，负责识别文件类型并分发到对应的解析通道。该模块通过多重验证机制确保文件类型识别的准确性，并根据文件大小和类型自动选择最优的解析策略，同时提供任务队列管理和负载均衡功能。

## 目录结构

```
format_router/
├── __init__.py              # 模块初始化，导出公共接口
├── file_type_identifier.py  # 文件类型识别（扩展名和二进制签名）
├── strategy_selector.py     # 解析策略选择（基于文件大小和类型）
├── task_queue.py           # 任务队列和负载均衡管理
├── format_router.py        # 格式路由器主类（整合所有功能）
├── test/test_format_router.py   # 单元测试
└── test/usage_example_format_router.py        # 使用示例
```

## 核心功能

### 1. 文件类型识别

通过扩展名和二进制签名双重验证文件类型，提高识别准确性：

- **扩展名识别**：使用标准MIME类型检测
- **二进制签名识别**：基于文件头魔数（Magic Numbers）进行验证
- **置信度评分**：双重验证成功为1.0，单一验证为0.8

支持的文件类型包括：
- 文档格式：PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
- 图片格式：JPEG, PNG, GIF, BMP, WEBP
- 文本格式：TXT, MD, HTML, XML
- 压缩格式：ZIP, RAR, 7Z, GZ

### 2. 解析策略选择

根据文件大小和类型自动选择最优解析策略：

| 策略 | 适用场景 | 特点 |
|------|----------|------|
| QUICK_PARSE | 小文件（<100KB） | 快速处理，低资源消耗 |
| BALANCED_PARSE | 中等文件（<10MB） | 平衡性能和资源 |
| DEEP_PARSE | 大文件或复杂格式（<100MB） | 深度解析，高准确性 |
| OCR_PARSE | 图片文件 | OCR文字识别 |
| STREAM_PARSE | 超大文件（>100MB） | 流式处理，内存友好 |

### 3. 任务队列和负载均衡

- **优先级队列**：支持紧急、高、普通、低四种优先级
- **负载均衡**：动态分配任务到可用工作线程
- **状态监控**：实时跟踪任务和工作线程状态

## 主要组件

### FileTypeIdentifier
文件类型识别器，提供 `identify_file_type(file_path)` 方法返回 `(mime_type, extension, confidence_score)`。

### StrategySelector
策略选择器，提供 `select_strategy(file_path, mime_type)` 方法返回 `ParseConfig` 对象。

### TaskQueue
任务队列管理器，支持优先级调度和负载均衡。

### FormatRouter
格式路由器主类，整合所有功能，提供统一的API。

## 使用示例

```python
from core.doc_preprocessor.format_router import FormatRouter, Priority

# 创建格式路由器
router = FormatRouter(max_workers=4)

# 注册解析器
def text_parser(file_path, user_id, team_id, config):
    # 实现文本解析逻辑
    return {"result": "parsed"}

router.register_parser(['text/plain', 'text/markdown'], text_parser)

# 提交文件解析任务
task_id = router.submit_file(
    file_path="example.txt",
    user_id="user123",
    team_id="team456",
    priority=Priority.NORMAL
)

# 获取结果
result = router.get_task_result(task_id)
```

## 设计原则

1. **准确性**：双重验证确保文件类型识别准确
2. **效率性**：根据文件特征选择最优解析策略
3. **可扩展性**：易于添加新的文件类型和解析器
4. **稳定性**：任务队列和负载均衡保证系统稳定运行