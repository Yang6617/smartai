# 灵析AI - 后端服务

灵析AI后端服务是基于FastAPI构建的高性能Web服务，负责处理用户认证、知识库管理、文档上传、智能问答等核心功能。后端与前端微信小程序配合，提供完整的知识库问答解决方案。

## 功能特性

- 🔐 **用户认证**：JWT认证系统，支持用户注册、登录和会话管理
- 👥 **群组管理**：支持创建、加入、退出群组，实现知识库共享
- 📁 **文件管理**：支持多种文件格式上传（PDF、DOCX、MD、TXT等）
- 🧠 **智能问答**：集成RAG引擎，基于知识库内容进行智能问答
- ⭐ **收藏功能**：用户可收藏有价值的问答记录
- 📤 **分享导出**：支持将问答记录分享到群组或导出为多种格式
- 📱 **微信集成**：支持微信小程序登录和API调用
- 📊 **数据统计**：记录用户活动和问答历史

## 系统架构

```
后端服务架构
├── main.py                     # 主应用入口，路由注册
├── run_backend.py              # 后端启动脚本
├── routes/                     # API路由模块
│   ├── auth.py                 # 认证相关接口
│   ├── files.py                # 文件上传管理接口
│   ├── groups.py               # 群组管理接口
│   ├── qa.py                   # 问答功能接口
│   ├── qa_api.py               # 问答API接口（外部调用）
│   └── misc.py                 # 其他功能接口（微信登录等）
├── models/database_models.py   # 数据库模型定义
├── schemas/index.py            # API请求/响应模型
├── database/db_config.py       # 数据库配置
├── utils/                      # 工具函数
│   ├── security.py             # 安全认证工具
│   └── ai_client.py            # AI服务客户端
├── uploads/                    # 上传文件存储目录
└── chroma_data/                # 向量数据库存储目录
```

## 环境配置

在运行项目之前，请确保创建`.env`文件并配置以下环境变量：

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

## 快速开始

### 环境准备

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 初始化向量数据库：
```bash
python -c "from core.vector_engine.scripts.init_chromadb_local import initialize_database; initialize_database()"
```

3. 启动后端服务：
```bash
python run_backend.py
```

4. 访问 `http://127.0.0.1:8000/docs` 查看API文档

### Docker部署

```bash
# 构建镜像
docker build -t lingxi-backend .

# 运行容器
docker run -p 8000:8000 --env-file .env lingxi-backend
```

## API接口

### 认证接口
- `POST /auth/register` - 用户注册
- `POST /auth/login` - 用户登录
- `GET /auth/profile` - 获取用户信息（需认证）

### 文件接口
- `POST /files/upload` - 上传文件到知识库
- `GET /files/list` - 获取文件列表
- `DELETE /files/delete/{file_id}` - 删除文件

### 问答接口
- `POST /qa/ask` - 基于知识库提问
- `GET /qa/history` - 获取问答历史
- `POST /qa/favorite` - 收藏问答记录

### 群组接口
- `POST /groups/create` - 创建群组
- `POST /groups/join` - 加入群组
- `GET /groups/my` - 获取用户群组列表

## 技术栈

- **Web框架**：FastAPI - 高性能异步Web框架
- **数据库**：SQLAlchemy + SQLite - ORM和关系型数据库
- **向量数据库**：ChromaDB - 专门的向量存储系统
- **认证系统**：JWT - 无状态用户认证
- **文件处理**：Unstructured - 多格式文档解析
- **AI集成**：集成RAG引擎，支持多种大模型

## 与核心模块集成

后端服务与`core/`目录下的核心模块深度集成：

- **文档预处理**：`core/doc_preprocessor` - 处理上传文档的解析和分块
- **RAG引擎**：`core/rag_engine` - 执行智能问答逻辑
- **向量存储**：`core/vector_engine` - 管理向量数据库操作

## 部署说明

### 开发环境
```bash
python run_backend.py
```

### 生产环境
```bash
gunicorn main:app -c gunicorn.conf.py
```

### 环境变量
- `DATABASE_URL` - 数据库连接字符串
- `SECRET_KEY` - JWT密钥
- `WECHAT_APP_ID` - 微信小程序AppID
- `WECHAT_APP_SECRET` - 微信小程序密钥
- ReDoc: `/redoc`

## 数据库设计

项目使用SQLAlchemy ORM进行数据库操作，支持SQLite、PostgreSQL和MySQL。

详细数据库设计请参考 [database_design.md](database_design.md)。

## 文件说明

- `main.py`: 包含所有API路由、数据库模型和业务逻辑的主应用文件
- `requirements.txt`: 项目依赖包列表
- `Dockerfile`: 用于构建Docker镜像
- `gunicorn.conf.py`: Gunicorn服务器配置文件
- `simple_run.py`: 用于本地开发的简单启动脚本
- `start_server.py`: 通用服务器启动脚本
- `windows_start.py`: Windows平台专用启动脚本
- `validate_app.py`: 用于验证应用功能的脚本
- `server.py`: 服务器配置脚本
- `Untitled-*.py`: 旧测试文件，应该被删除
- `uploads/`: 存储用户上传文件的目录
- `*.db`: SQLite数据库文件

## 注意事项

1. 项目目前所有功能都在一个文件(main.py)中，建议后续重构为模块化结构
2. 需要清理不必要的测试文件和目录
3. 项目根目录中有几个不应该存在的用户目录，需要清理
4. 应该将模型、路由、工具函数等分离到不同的模块中