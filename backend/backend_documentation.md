# 灵析AI - 后端服务文档

## 项目概述

灵析AI后端服务是一个基于FastAPI构建的企业级AI知识库问答系统，支持文档预处理、向量化存储、智能问答、群组协作等功能。项目集成了用户认证、群组管理、文件上传下载、智能问答、收藏分享等完整功能。

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
│   │   ├── files.py              # 文件上传/下载管理路由
│   │   ├── groups.py             # 群组管理路由
│   │   ├── favorites.py          # 收藏功能路由
│   │   ├── qa.py                 # 问答功能路由
│   │   ├── qa_api.py             # 问答API路由（外部调用）
│   │   └── misc.py               # 其他功能路由（微信登录等）
│   ├── utils/                    # 工具函数
│   │   ├── security.py           # 安全认证工具
│   │   ├── ai_client.py          # AI服务客户端
│   │   └── file_storage.py       # 文件存储工具
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
- 文件下载功能（群组内权限控制）

### 3. 群组管理模块
- 群组创建与管理
- 成员邀请与权限控制
- 群组内知识库共享
- 协作问答功能
- 基于角色的访问控制（RBAC）
  - 管理员：可以上传文件、添加/移除成员、提升角色、下载文件
  - 普通用户：只能提问、查看群组信息、下载群组文件

### 4. 智能问答模块
- 基于知识库的问答
- RAG检索增强生成
- 引用标注与来源追踪
- 问答历史记录
- 支持通过群组ID或群组名称提问

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

### 数据库初始化

首次运行前，后端会自动创建数据库表结构。如果需要重置数据库：

```bash
python clear_database.py
```

此命令会删除 SQLite 数据库和 ChromaDB 向量数据库，下次启动时会自动重新创建。

## API接口文档

### 认证相关接口

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

### 文件管理接口

#### 上传文件
- **POST** `/file/upload`
- **描述**: 上传文件到群组知识库（需认证）
- **认证**: Bearer JWT Token
- **权限要求**: 仅群组管理员可以上传文件
- **表单数据**:
  - `file`: 上传的文件（必需）
  - `group_id`: 群组ID（必需，字符串类型）
  - `original_filename`: 原始文件名（可选）
  - `category`: 文件分类（可选，默认 "general"）
- **响应**:
  ```json
  {
    "id": 1,
    "filename": "uuid_original_filename",
    "original_filename": "string",
    "file_size": 1234,
    "content_type": "text/markdown",
    "upload_time": "2026-03-14T09:07:58.149632",
    "group_id": 1,
    "file_category": "general",
    "file_type": "markdown"
  }
  ```
- **示例**:
  ```bash
  curl -X POST http://127.0.0.1:8003/file/upload \
    -H "Authorization: Bearer <token>" \
    -F "file=@document.md" \
    -F "group_id=1"
  ```

#### 获取群组文件列表
- **GET** `/file/list`
- **描述**: 获取群组中的所有文件列表（需认证）
- **认证**: Bearer JWT Token
- **权限要求**: 仅群组成员可以查看文件列表
- **查询参数**:
  - `group_id`: 群组ID（必需）
- **响应**:
  ```json
  [
    {
      "id": 1,
      "filename": "uuid_original_filename",
      "original_filename": "string",
      "file_size": 1234,
      "content_type": "text/markdown",
      "upload_time": "2026-03-14T09:07:58.149632",
      "group_id": 1,
      "file_category": "general",
      "file_type": "markdown"
    }
  ]
  ```
- **示例**:
  ```bash
  curl -X GET "http://127.0.0.1:8003/file/list?group_id=1" \
    -H "Authorization: Bearer <token>"
  ```

#### 下载文件
- **GET** `/file/download/{file_id}`
- **描述**: 下载文件（需认证）
- **认证**: Bearer JWT Token
- **权限要求**: 仅群组成员可以下载该群组的文件
- **路径参数**:
  - `file_id`: 文件ID（必需）
- **响应**: 文件二进制内容（触发浏览器下载）
- **响应头**:
  - `Content-Disposition`: `attachment; filename*=UTF-8''{original_filename}`
  - `Content-Type`: 文件类型
- **示例**:
  ```bash
  curl -X GET "http://127.0.0.1:8003/file/download/1" \
    -H "Authorization: Bearer <token>" \
    -o downloaded_file.md
  ```

### 问答接口

#### 智能问答（通过群组ID）
- **POST** `/api/v1/ask-question`
- **描述**: 提交问题并获取AI回答（需认证）
- **认证**: Bearer JWT Token
- **权限要求**: 仅群组成员可以提问
- **请求体**:
  ```json
  {
    "question": "string",
    "knowledge_base_id": 1,
    "model_alias": "default",
    "stream": false,
    "top_k": 8
  }
  ```
- **参数说明**:
  - `question`: 问题内容（必需）
  - `knowledge_base_id`: 群组ID（可选，与group_name二选一）
  - `model_alias`: 模型别名（可选，默认 "default"）
  - `stream`: 是否流式响应（可选，默认 false）
  - `top_k`: 检索相关文档数量（可选，默认 8）
- **响应**:
  ```json
  {
    "status": "success",
    "answer": "string",
    "sources": ["string"],
    "confidence": 0.95,
    "processing_time": 2.3
  }
  ```
- **示例**:
  ```bash
  curl -X POST http://127.0.0.1:8003/api/v1/ask-question \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d '{
      "question": "AI模型服务的关键决策有哪些？",
      "knowledge_base_id": 1
    }'
  ```

#### 智能问答（通过群组名称）
- **POST** `/api/v1/ask-question`
- **描述**: 提交问题并获取AI回答（通过群组名称，需认证）
- **认证**: Bearer JWT Token
- **权限要求**: 仅群组成员可以提问
- **请求体**:
  ```json
  {
    "question": "string",
    "group_name": "测试群组",
    "model_alias": "default",
    "stream": false,
    "top_k": 8
  }
  ```
- **参数说明**:
  - `question`: 问题内容（必需）
  - `group_name`: 群组名称（可选，与knowledge_base_id二选一）
  - `model_alias`: 模型别名（可选，默认 "default"）
  - `stream`: 是否流式响应（可选，默认 false）
  - `top_k`: 检索相关文档数量（可选，默认 8）
- **响应**: 与通过群组ID提问相同
- **示例**:
  ```bash
  curl -X POST http://127.0.0.1:8003/api/v1/ask-question \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d '{
      "question": "系统采用什么架构设计？",
      "group_name": "测试群组"
    }'
  ```

#### 获取问答历史
- **GET** `/api/v1/qa/list`
- **描述**: 获取用户问答历史记录（需认证）
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
        "created_at": "2023-01-01T00:00:00",
        "group_id": 1
      }
    ]
  }
  ```

### 群组管理接口

#### 创建群组
- **POST** `/group/create`
- **描述**: 创建新群组（需认证）
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
    "owner_id": 1,
    "created_at": "2026-03-14T09:07:58.149632",
    "members": [
      {
        "user_id": 1,
        "username": "adminuser",
        "role": "admin"
      }
    ]
  }
  ```
- **说明**: 创建者自动成为管理员

#### 获取群组列表
- **GET** `/group/list`
- **描述**: 获取用户所属的群组列表（需认证）
- **认证**: Bearer JWT Token
- **响应**:
  ```json
  [
    {
      "id": 1,
      "name": "string",
      "description": "string",
      "owner_id": 1,
      "created_at": "2026-03-14T09:07:58.149632",
      "members": [
        {
          "user_id": 1,
          "username": "adminuser",
          "role": "admin"
        },
        {
          "user_id": 2,
          "username": "normaluser",
          "role": "member"
        }
      ]
    }
  ]
  ```

### 群组成员管理接口（管理员专用）

#### 添加成员
- **POST** `/group/add-member`
- **描述**: 添加成员到群组（仅管理员）
- **认证**: Bearer JWT Token
- **查询参数**:
  - `group_id`: 群组ID（必需）
  - `user_id`: 用户ID（必需）
  - `role`: 角色，可选值 "admin" 或 "member"（默认 "member"）
- **响应**:
  ```json
  {
    "user_id": 2,
    "group_id": 1,
    "role": "member",
    "joined_at": "2026-03-14T09:07:58.149632",
    "user": {
      "id": 2,
      "username": "string",
      "email": "string"
    }
  }
  ```

#### 移除成员
- **DELETE** `/group/remove-member`
- **描述**: 从群组中移除成员（仅管理员）
- **认证**: Bearer JWT Token
- **查询参数**:
  - `group_id`: 群组ID（必需）
  - `user_id`: 用户ID（必需）
- **响应**:
  ```json
  {
    "status": "success",
    "message": "成员已移除"
  }
  ```

#### 更新成员角色
- **PUT** `/group/update-member-role`
- **描述**: 更新成员角色（仅管理员）
- **认证**: Bearer JWT Token
- **查询参数**:
  - `group_id`: 群组ID（必需）
  - `user_id`: 用户ID（必需）
  - `role`: 新角色，可选值 "admin" 或 "member"（必需）
- **响应**:
  ```json
  {
    "user_id": 2,
    "group_id": 1,
    "role": "admin",
    "user": {
      "id": 2,
      "username": "string",
      "email": "string"
    }
  }
  ```

### 收藏功能接口

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

### 系统接口

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
- role: 字符串，成员角色（"admin" 或 "member"），默认 "member"
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
- filename: 字符串（存储相对路径）
- original_filename: 字符串（原始文件名）
- file_size: 整数
- content_type: 字符串
- upload_time: 时间戳，默认当前时间
- group_id: 整数，外键引用群组表
- file_category: 字符串（文件分类）
- file_type: 字符串（文件类型）

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
5. 访问 `http://127.0.0.1:8003` 查看API文档

### 权限系统使用说明

1. **创建群组**: 用户注册后可以创建群组，创建者自动成为管理员
2. **添加成员**: 管理员可以邀请其他用户加入群组
3. **设置角色**: 管理员可以将普通用户提升为管理员
4. **权限控制**: 
   - 管理员拥有文件上传、成员管理、文件下载等权限
   - 普通用户只能提问、查看群组信息、下载群组文件
5. **测试权限**: 可以使用 `test_group_permissions.py` 脚本测试权限功能

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

### 权限错误处理
- 尝试无权限操作时返回403 Forbidden，错误信息说明具体权限要求
- 例如：`"您不是该知识库的成员，无法提问"`

## 安全措施

1. 使用JWT进行身份验证
2. 密码使用bcrypt进行哈希存储
3. 所有敏感数据使用HTTPS传输
4. 输入验证和SQL注入防护
5. 文件上传类型和大小限制（最大50MB）
6. 文件下载权限控制（仅群组成员可下载）

## 权限系统说明

### 基于角色的访问控制（RBAC）

系统实现了基于角色的访问控制（RBAC），每个群组中有两种角色：

#### 管理员（admin）
- 可以上传文件到知识库
- 可以添加新成员到群组
- 可以从群组中移除成员
- 可以提升普通用户为管理员
- 可以下载群组文件
- 可以提问和查看群组信息

#### 普通用户（member）
- 可以向知识库提问
- 可以下载群组文件
- 可以查看群组信息
- 不能上传文件
- 不能添加/移除成员
- 不能提升用户角色

### 权限验证规则

1. **文件上传**: 仅群组管理员可以上传文件
2. **文件下载**: 仅群组成员可以下载该群组的文件
3. **提问**: 仅群组成员可以提问（包括管理员和普通用户）
4. **成员管理**: 仅管理员可以添加、移除成员和更新角色
5. **角色提升**: 仅管理员可以提升用户角色

### 错误处理

当用户尝试执行无权限的操作时，系统会返回 403 Forbidden 错误，错误信息会说明具体的权限要求。

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

## 测试说明

### 权限功能测试

系统提供了完整的权限功能测试脚本 `test_group_permissions.py`，用于验证所有权限功能：

```bash
python test_group_permissions.py
```

测试内容包括：
1. 用户注册和登录
2. 群组创建（创建者自动成为管理员）
3. 普通用户权限限制（无法上传文件）
4. 添加成员到群组
5. 管理员上传文件
6. 普通用户提问
7. 普通用户添加成员限制
8. 角色提升（普通用户 → 管理员）
9. 新管理员上传文件
10. 群组列表显示成员信息

### 文件下载测试

系统提供了文件下载功能测试脚本 `test_file_download.py`：

```bash
python test_file_download.py
```

测试内容包括：
1. 管理员下载文件
2. 普通用户下载所在群组的文件
3. 下载不存在的文件
4. 下载不属于所在群组的文件

### 问答功能测试

系统提供了问答功能测试脚本 `test_qa.py`：

```bash
python test_qa.py
```

测试内容包括：
1. 使用 knowledge_base_id 提问
2. 使用 group_name 提问

### 完整工作流测试

系统提供了完整工作流测试脚本 `test_workflow.py`：

```bash
python test_workflow.py
```

测试内容包括：
1. 用户登录
2. 创建群组
3. 上传文件

### 数据库重置

如需重置数据库以重新开始测试：

```bash
python clear_database.py
```

此命令会删除所有数据，下次启动时会自动重新创建数据库结构。
