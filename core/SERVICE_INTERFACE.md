# 灵析AI - 核心服务接口调用指南

本文档介绍了如何使用灵析AI系统的核心服务接口进行文档处理和知识问答操作。

## 目录
1. [概述](#概述)
2. [安装与依赖](#安装与依赖)
3. [接口概览](#接口概览)
4. [文档上传接口](#文档上传接口)
5. [用户提问接口](#用户提问接口)
6. [参数详解](#参数详解)
7. [错误处理](#错误处理)
8. [最佳实践](#最佳实践)

## 概述

灵析AI核心服务接口提供了统一的API来处理文档上传、解析、向量化存储以及基于知识库的问答功能。接口主要包含两个核心功能：
- 文档上传处理 (`upload_file_interface`)
- 用户提问问答 (`ask_question_interface`)

这些接口整合了文档预处理器、RAG推理引擎和向量数据库引擎，为上层应用提供简单易用的服务。

## 安装与依赖

确保已安装以下依赖：
```bash
pip install -r requirements.txt
```

## 接口概览

```python
from core.service_interface import (
    upload_file_interface,
    ask_question_interface
)
```

## 文档上传接口

### 函数定义
```python
def upload_file_interface(
    file_path: str,
    user_id: str,
    knowledge_base_id: str,
    file_name: Optional[str] = None,
    custom_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
```

### 参数说明
- `file_path`: (str) 上传文件的本地路径
- `user_id`: (str) 用户ID，用于用户隔离和权限控制
- `knowledge_base_id`: (str) 知识库ID，用于知识库隔离
- `file_name`: (Optional[str]) 文件名（可选，如果不提供则从file_path提取）
- `custom_metadata`: (Optional[Dict[str, Any]]) 自定义元数据（可选），用于增强检索能力

### 返回值
返回包含以下键的字典：
- `document_id`: 文档唯一标识符
- `file_name`: 文件名
- `user_id`: 用户ID
- `knowledge_base_id`: 知识库ID
- `status`: 处理状态 ('success' 或 'error')
- `message`: 处理消息
- `processed_elements_count`: 处理的元素数量
- `chunk_count`: 分块数量
- `storage_result`: 存储结果详情
- `processing_time`: 处理耗时（秒）

### 使用示例
```python
from core.service_interface import upload_file_interface

result = upload_file_interface(
    file_path="./documents/manual.pdf",
    user_id="user_12345",
    knowledge_base_id="kb_tech_manuals",
    file_name="technical_manual.pdf",
    custom_metadata={
        "category": "technical",
        "version": "1.0",
        "department": "engineering",
        "tags": ["tech", "manual", "guide"]
    }
)

print(result)
# 输出示例:
# {
#     'document_id': 'doc_abc123',
#     'file_name': 'technical_manual.pdf',
#     'user_id': 'user_12345',
#     'knowledge_base_id': 'kb_tech_manuals',
#     'status': 'success',
#     'message': '文档处理和存储成功',
#     'processed_elements_count': 15,
#     'chunk_count': 23,
#     'storage_result': {...},
#     'processing_time': 5.2
# }
```

## 用户提问接口

### 函数定义
```python
def ask_question_interface(
    question: str,
    user_id: str,
    knowledge_base_id: str,
    model_alias: str = "default",
    stream: bool = False,
    top_k: Optional[int] = 5,
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> Dict[str, Any]:
```

### 参数说明
- `question`: (str) 用户提出的问题
- `user_id`: (str) 用户ID，用于用户隔离
- `knowledge_base_id`: (str) 知识库ID，指定查询的知识库
- `model_alias`: (str) 使用的模型别名，默认为 "default"
- `stream`: (bool) 是否使用流式输出，默认为 False
- `top_k`: (Optional[int]) 检索的top-k数量，默认为 5
- `temperature`: (float) 生成温度，控制创造性，默认为 0.7
- `max_tokens`: (int) 最大生成token数，默认为 1024

### 返回值
返回包含以下键的字典：
- `status`: 状态 ('success' 或 'error')
- `answer`: AI生成的答案
- `citations`: 引用来源列表
- `debug`: 调试信息（仅在调试模式下）
- `processing_time`: 处理耗时（秒）
- `retrieved_chunks`: 检索到的文档片段列表
- `confidence_score`: 回答置信度分数

### 使用示例
```python
from core.service_interface import ask_question_interface

result = ask_question_interface(
    question="人工智能的主要应用领域有哪些？",
    user_id="user_12345",
    knowledge_base_id="kb_ai_research",
    model_alias="deepseek-chat",
    top_k=5,
    temperature=0.6
)

print(result)
# 输出示例:
# {
#     'status': 'success',
#     'answer': '根据提供的资料，人工智能的主要应用领域包括...',
#     'citations': [
#         {
#             'content': '原始文档中的相关段落...',
#             'score': 0.87,
#             'metadata': {...}
#         },
#         ...
#     ],
#     'retrieved_chunks': [...],
#     'confidence_score': 0.85,
#     'processing_time': 3.2,
#     'debug': {...}
# }
```

## 参数详解

### 通用参数
- `user_id`: 用于区分不同用户的请求，建议使用UUID或其他唯一标识符
- `knowledge_base_id`: 用于指定特定的知识库，实现多租户隔离
- `model_alias`: 指定使用的语言模型，例如 "deepseek-chat", "default"

### 文档上传特有参数
- `file_path`: 必须是有效的本地文件路径，支持的格式包括 PDF, DOCX, TXT, MD 等
- `custom_metadata`: 可以包含任何自定义的键值对，用于后续检索和过滤

### 问答特有参数
- `stream`: 当设置为 True 时，返回生成器对象用于流式接收答案
- `top_k`: 控制从向量数据库中检索的最相似文档数量
- `temperature`: 控制生成内容的创造性，0.0-1.0之间
- `max_tokens`: 限制生成答案的最大长度

## 错误处理

### 常见错误及解决方案

1. **模型目录不存在**
   ```
   错误: 模型目录不存在: D:\homework\model
   解决方案: 确保模型目录存在并包含所需的模型文件
   ```

2. **向量数据库连接失败**
   ```
   错误: Could not connect to a Chroma server
   解决方案: 启动向量数据库服务或检查连接参数
   ```

3. **不支持的文件格式**
   ```
   错误: 不支持的文件格式: .xyz
   解决方案: 使用支持的文件格式（PDF, DOCX, TXT, MD 等）
   ```

4. **知识库为空**
   ```
   错误: 知识库中没有可用的文档
   解决方案: 先上传文档到指定知识库
   ```

### 错误响应格式
```python
{
    'status': 'error',
    'message': '错误描述信息',
    'answer': '友好错误消息',
    'citations': [],
    'retrieved_chunks': [],
    'debug': {
        'original_error': '原始错误信息',
        'timestamp': '错误发生时间戳'
    }
}
```

## 最佳实践

### 1. 文档命名规范
使用有意义的文件名和知识库ID，便于后续管理和检索：
```python
# 好的做法
upload_file_interface(
    file_path="./docs/tech_manual_v2.pdf",
    user_id="user_12345",
    knowledge_base_id="kb_company_tech_docs"
)

# 避免的做法
upload_file_interface(
    file_path="./file1.pdf",
    user_id="123",
    knowledge_base_id="kb1"
)
```

### 2. 元数据使用
充分利用自定义元数据来增强文档的可检索性：
```python
upload_file_interface(
    file_path="./report.pdf",
    user_id="user_12345",
    knowledge_base_id="kb_financial_reports",
    custom_metadata={
        "year": 2023,
        "quarter": "Q4",
        "department": "finance",
        "region": "north_america",
        "tags": ["financial", "report", "q4", "2023"]
    }
)
```

### 3. 问答优化
针对不同类型的问题选择合适的参数：
```python
# 对于需要详细解释的问题
ask_question_interface(
    question="请详细解释机器学习的工作原理",
    user_id="user_123",
    knowledge_base_id="kb_ml_docs",
    top_k=8,  # 获取更多相关文档
    temperature=0.5  # 更确定性的回答
)

# 对于事实性问题
ask_question_interface(
    question="公司的成立日期是什么时候？",
    user_id="user_123",
    knowledge_base_id="kb_company_docs",
    top_k=3,  # 较少的相关文档
    temperature=0.2  # 更精确的回答
)

# 对于创意性问题
ask_question_interface(
    question="如何改进现有的工作流程？",
    user_id="user_123",
    knowledge_base_id="kb_company_docs",
    top_k=5,
    temperature=0.8  # 更有创造性的回答
)
```

### 4. 性能优化
- 对于大量文档上传，考虑分批处理
- 合理设置top_k参数，平衡准确性和性能
- 使用适当的temperature值，避免过高导致不准确的回答

### 5. 错误处理
始终检查返回的状态并适当处理错误：
```python
result = ask_question_interface(
    question="问题",
    user_id="user",
    knowledge_base_id="kb"
)

if result['status'] == 'error':
    print(f"错误: {result['message']}")
else:
    print(f"答案: {result['answer']}")
```
    question="请详细解释量子计算的原理",
    user_id="user_12345",
    knowledge_base_id="kb_quantum_physics",
    top_k=8  # 获取更多上下文
)

# 对于事实性问题
ask_question_interface(
    question="公司成立日期是什么时候？",
    user_id="user_12345",
    knowledge_base_id="kb_company_info",
    top_k=3  # 较少的上下文就足够了
)
```

### 4. 异常处理
始终对API调用进行异常处理：
```python
try:
    result = ask_question_interface(
        question="您的问题",
        user_id="user_12345",
        knowledge_base_id="kb_example"
    )
    
    if result['status'] == 'success':
        print(f"答案: {result['answer']}")
        print(f"引用: {len(result['citations'])} 条")
    else:
        print(f"请求失败: {result['message']}")
        
except Exception as e:
    print(f"系统错误: {str(e)}")
```

### 5. 资源管理
合理管理资源，避免不必要的重复上传：
```python
# 检查文件是否已经处理过
def is_document_processed(file_hash, knowledge_base_id):
    # 实现检查逻辑
    pass

# 在上传前进行检查
if not is_document_processed(get_file_hash(file_path), knowledge_base_id):
    result = upload_file_interface(file_path, user_id, knowledge_base_id)
```

## 性能优化建议

1. **批量处理**: 对于大量文档，考虑使用批量上传策略
2. **缓存机制**: 对频繁查询的问题实现缓存
3. **异步处理**: 对于大文件上传，使用异步处理机制
4. **连接复用**: 复用数据库连接以提高性能

## 故障排除

如果遇到问题，请按以下步骤排查：

1. 检查依赖项是否正确安装
2. 确认模型目录和文件权限
3. 验证向量数据库服务是否运行
4. 查看日志文件获取详细错误信息
5. 联系技术支持团队

## 更新日志

- v1.0.0: 初始版本，包含文档上传和问答接口
- v1.0.1: 增加了错误处理和参数验证
- v1.0.2: 添加了流式响应支持