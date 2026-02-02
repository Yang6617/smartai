# 灵析AI - 后端服务文档

## 项目概述

灵析AI后端服务是一个基于FastAPI构建的企业级AI知识库问答系统，支持文档预处理、向量化存储、智能问答等功能。项目集成了用户认证、群组管理、微信小程序登录、文件上传管理、收藏分享等完整功能。

## 系统架构

```
灵析AI后端服务架构
├── fastapi_project/              # FastAPI主项目目录
│   ├── main.py                   # 主应用入口文件，路由注册
│   ├── run_backend.py            # 后端启动脚本
│   ├── requirements.txt          # 项目依赖
│   ├── database_design.md        # 数据库设计文档
│   ├── README.md                 # 项目说明文档
│   ├── uploads/                  # 文件上传目录
│   ├── chroma_data/              # Chroma向量数据库存储目录
│   ├── core/                     # 核心AI服务（文档预处理、RAG引擎、向量存储）
│   ├── routes/                   # API路由模块
│   │   ├── auth.py               # 用户认证相关路由
│   │   ├── files.py              # 文件上传管理路由
│   │   ├── groups.py             # 群组管理路由
│   │   ├── favorites.py          # 收藏功能路由
│   │   ├── qa.py                 # 问答功能路由
│   │   ├── qa_api.py             # 问答API路由（外部调用）
│   │   └── misc.py               # 其他功能路由（微信登录等）
│   ├── utils/                    # 工具函数
│   │   ├── security.py           # 安全认证工具
│   │   └── ai_client.py          # AI服务客户端
│   ├── models/                   # 数据模型
│   │   └── database_models.py    # 数据库模型定义
│   ├── schemas/                  # Pydantic模型
│   │   └── index.py              # 请求/响应模型定义
│   ├── database/                 # 数据库配置
│   │   └── db_config.py          # 数据库连接配置
│   └── tests/                    # 测试文件
```

## 核心功能模块

### 1. 用户认证模块
- 用户注册与登录（JWT认证）
- 会话管理
- 权限控制
- 微信小程序登录集成

### 2. 文件管理模块
- 多格式文档上传（PDF、DOCX、MD、TXT等）
- 文件元数据管理
- 文档预处理（解析、清洗、分块）
- 向量化存储

### 3. 群组管理模块
- 群组创建与管理
- 成员邀请与权限控制
- 群组内知识库共享
- 协作问答功能

### 4. 智能问答模块
- 基于知识库的问答
- RAG检索增强生成
- 引用标注与来源追踪
- 问答历史记录

### 5. 收藏与分享模块
- 问答收藏功能
- 群组内分享
- 问答导出功能

## 环境配置

### 依赖安装

```bash
pip install -r requirements.txt
```

### 环境变量配置

在项目根目录创建 `.env` 文件：

```env
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./knowledge_system.db
MODEL_SERVICE_URL=http://localhost:8000
MODEL_TIMEOUT=30.0
WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-app-secret
```

## API接口文档

### 1. 认证相关接口

#### 用户注册
- **POST** `/auth/register`
- **描述**: 注册新用户
- **请求体**:
  ```json
  {
    "username": "string",
    "email": "string",
    "password": "string"
  }
  ```
- **响应**:
  ```json
  {
    "id": 1,
    "username": "string",
    "email": "string",
    "created_at": "2023-01-01T00:00:00"
  }
  ```

#### 用户登录
- **POST** `/auth/login`
- **描述**: 用户登录获取JWT令牌
- **请求体**:
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **响应**:
  ```json
  {
    "access_token": "string",
    "token_type": "bearer"
  }
  ```

#### 获取用户信息
- **GET** `/auth/profile`
- **描述**: 获取当前登录用户信息（需认证）
- **响应**:
  ```json
  {
    "id": 1,
    "username": "string",
    "email": "string",
    "created_at": "2023-01-01T00:00:00"
  }
  ```

### 2. 文件管理接口

#### 上传文件
- **POST** `/files/upload`
- **描述**: 上传文件到知识库（需认证）
- **请求参数**:
  - `file`: 上传的文件
  - `knowledge_base_id`: 知识库ID
  - `user_id`: 用户ID（从JWT中获取）
- **响应**:
  ```json
  {
    "status": "success",
    "message": "文件上传成功",
    "document_id": "string",
    "file_name": "string",
    "processing_time": 5.2
  }
  ```

#### 获取文件列表
- **GET** `/files/list`
- **描述**: 获取用户文件列表（需认证）
- **查询参数**:
  - `knowledge_base_id`: 知识库ID（可选）
- **响应**:
  ```json
  {
    "files": [
      {
        "id": 1,
        "filename": "string",
        "original_filename": "string",
        "file_size": 1024,
        "content_type": "string",
        "upload_time": "2023-01-01T00:00:00",
        "group_id": 1
      }
    ]
  }
  ```

### 3. 问答接口

#### 基于知识库提问
- **POST** `/qa/ask`
- **描述**: 基于知识库进行智能问答（需认证）
- **请求体**:
  ```json
  {
    "question": "string",
    "knowledge_base_id": "string",
    "top_k": 5,
    "temperature": 0.7
  }
  ```
- **响应**:
  ```json
  {
    "status": "success",
    "answer": "string",
    "citations": [
      {
        "content": "string",
        "score": 0.85,
        "metadata": {}
      }
    ],
    "confidence_score": 0.85,
    "processing_time": 2.3
  }
  ```

#### 获取问答历史
- **GET** `/qa/history`
- **描述**: 获取用户问答历史（需认证）
- **查询参数**:
  - `limit`: 返回记录数量（默认10）
  - `offset`: 偏移量（默认0）
- **响应**:
  ```json
  {
    "records": [
      {
        "id": 1,
        "question": "string",
        "answer": "string",
        "created_at": "2023-01-01T00:00:00",
        "group_id": 1
      }
    ]
  }
  ```

### 4. 群组管理接口

#### 创建群组
- **POST** `/groups/create`
- **描述**: 创建新群组（需认证）
- **请求体**:
  ```json
  {
    "name": "string",
    "description": "string"
  }
  ```
- **响应**:
  ```json
  {
    "id": 1,
    "name": "string",
    "description": "string",
    "owner_id": 1,
    "created_at": "2023-01-01T00:00:00"
  }
  ```

#### 加入群组
- **POST** `/groups/join`
- **描述**: 加入群组（需认证）
- **请求体**:
  ```json
  {
    "group_id": 1
  }
  ```
- **响应**:
  ```json
  {
    "status": "success",
    "message": "成功加入群组"
  }
  ```

#### 微信小程序登录
- **POST** `/wechat/login`
- **描述**: 微信小程序登录接口，如未配置微信凭据则使用模拟模式
- **请求体**:
  ```json
  {
    "code": "string"
  }
  ```
- **响应**:
  ```json
  {
    "access_token": "string",
    "token_type": "bearer",
    "user_id": 1,
    "username": "string"
  }
  ```

### 2. 文件管理接口

#### 上传文件
- **POST** `/file/upload`
- **描述**: 上传文件到知识库
- **认证**: Bearer JWT Token
- **表单数据**:
  - `file`: 文件
  - `knowledge_base_id`: 知识库ID
- **响应**:
  ```json
  {
    "filename": "string",
    "size": 1234,
    "message": "string"
  }
  ```

#### 文件列表
- **GET** `/file/list`
- **描述**: 获取用户上传的文件列表
- **认证**: Bearer JWT Token
- **查询参数**:
  - `knowledge_base_id`: 知识库ID
- **响应**:
  ```json
  {
    "files": [
      {
        "id": 1,
        "filename": "string",
        "size": 1234,
        "upload_date": "2023-01-01T00:00:00"
      }
    ]
  }
  ```

### 3. 问答接口

#### 智能问答
- **POST** `/api/v1/ask-question`
- **描述**: 提交问题并获取AI回答
- **认证**: Bearer JWT Token
- **请求体**:
  ```json
  {
    "question": "string",
    "knowledge_base_id": 1
  }
  ```
- **响应**:
  ```json
  {
    "answer": "string",
    "sources": ["string"],
    "confidence": 0.95
  }
  ```

#### 问答历史
- **GET** `/api/v1/qa/list`
- **描述**: 获取用户问答历史记录
- **认证**: Bearer JWT Token
- **查询参数**:
  - `limit`: 返回记录数量，默认20
  - `offset`: 偏移量，默认0
- **响应**:
  ```json
  {
    "records": [
      {
        "id": 1,
        "question": "string",
        "answer": "string",
        "created_at": "2023-01-01T00:00:00"
      }
    ]
  }
  ```

### 4. 群组管理接口

#### 创建群组
- **POST** `/group/group/create`
- **描述**: 创建新群组
- **认证**: Bearer JWT Token
- **请求体**:
  ```json
  {
    "name": "string",
    "description": "string"
  }
  ```
- **响应**:
  ```json
  {
    "id": 1,
    "name": "string",
    "description": "string",
    "owner_id": 1
  }
  ```

#### 获取群组列表
- **GET** `/group/group/list`
- **描述**: 获取用户所属的群组列表
- **认证**: Bearer JWT Token
- **响应**:
  ```json
  {
    "groups": [
      {
        "id": 1,
        "name": "string",
        "description": "string"
      }
    ]
  }
  ```

### 5. 收藏功能接口

#### 添加收藏
- **POST** `/favorite/favorite/add`
- **描述**: 收藏问答记录
- **认证**: Bearer JWT Token
- **请求体**:
  ```json
  {
    "qa_record_id": 1
  }
  ```
- **响应**:
  ```json
  {
    "id": 1,
    "qa_record_id": 1,
    "created_at": "2023-01-01T00:00:00"
  }
  ```

#### 收藏列表
- **GET** `/favorite/favorite/list`
- **描述**: 获取用户收藏列表
- **认证**: Bearer JWT Token
- **响应**:
  ```json
  {
    "favorites": [
      {
        "id": 1,
        "qa_record_id": 1,
        "question": "string",
        "answer": "string"
      }
    ]
  }
  ```

#### 删除收藏
- **DELETE** `/favorite/favorite/{fav_id}`
- **描述**: 删除指定收藏
- **认证**: Bearer JWT Token
- **路径参数**:
  - `fav_id`: 收藏ID
- **响应**: 200 OK

### 6. 系统接口

#### 健康检查
- **GET** `/health`
- **描述**: 检查系统健康状态
- **响应**:
  ```json
  {
    "status": "healthy",
    "service": "Knowledge QA System"
  }
  ```

#### API根路径
- **GET** `/`
- **描述**: API根路径
- **响应**:
  ```json
  {
    "message": "欢迎使用知识问答系统API"
  }
  ```

## 数据库设计

### 用户表 (users)
- id: 整数，主键，自增长
- username: 字符串，唯一索引
- email: 字符串，唯一索引
- hashed_password: 字符串
- created_at: 时间戳，默认当前时间

### 群组表 (groups)
- id: 整数，主键，自增长
- name: 字符串，索引
- description: 文本
- owner_id: 整数，外键引用用户表
- created_at: 时间戳，默认当前时间

### 群组成员表 (group_members)
- id: 整数，主键，自增长
- group_id: 整数，外键引用群组表
- user_id: 整数，外键引用用户表
- joined_at: 时间戳，默认当前时间

### 问答记录表 (qa_records)
- id: 整数，主键，自增长
- user_id: 整数，外键引用用户表
- question: 文本
- answer: 文本
- sources: JSON文本
- created_at: 时间戳，默认当前时间

### 收藏表 (favorites)
- id: 整数，主键，自增长
- user_id: 整数，外键引用用户表
- qa_record_id: 整数，外键引用问答记录表
- created_at: 时间戳，默认当前时间

### 文件表 (files)
- id: 整数，主键，自增长
- user_id: 整数，外键引用用户表
- filename: 字符串
- filepath: 字符串
- size: 整数
- knowledge_base_id: 整数
- upload_date: 时间戳，默认当前时间

## 部署说明

### 开发环境部署

1. 克隆项目代码
2. 安装Python依赖:
   ```bash
   pip install -r requirements.txt
   ```
3. 配置环境变量
4. 启动后端服务:
   ```bash
   python run_backend.py
   ```
5. 访问 `http://127.0.0.1:8002` 查看API文档

### 生产环境部署建议

1. 使用反向代理（如nginx）处理静态文件和SSL
2. 配置进程管理器（如supervisor或pm2）确保服务持续运行
3. 使用生产级数据库（如PostgreSQL）
4. 设置适当的日志轮转机制
5. 配置监控和告警

## 错误处理

### 常见HTTP状态码
- 200: 请求成功
- 400: 请求参数错误
- 401: 未认证
- 403: 权限不足
- 404: 资源不存在
- 422: 请求格式错误
- 500: 服务器内部错误

### 认证错误处理
- 所有需要认证的接口都需要在Header中携带 `Authorization: Bearer <token>`
- 令牌过期或无效时返回401状态码

## 安全措施

1. 使用JWT进行身份验证
2. 密码使用bcrypt进行哈希存储
3. 所有敏感数据使用HTTPS传输
4. 输入验证和SQL注入防护
5. 文件上传类型和大小限制

## 维护说明

### 日志管理
- 应用日志记录在控制台输出
- 建议在生产环境中重定向到日志文件

### 数据备份
- 定期备份SQLite数据库文件
- 向量数据库备份策略需根据实际需求制定

### 性能优化
- 合理使用索引提高查询性能
- 定期清理过期数据
- 根据负载调整数据库连接池大小