# 知识问答系统

这是一个基于FastAPI构建的知识问答系统，支持用户认证、群组管理、文件上传、智能问答、收藏分享等功能。

## 功能特性

- 用户注册与登录（JWT认证）
- 群组管理（创建、加入、退出群组）
- 文件上传与管理（支持多种文件类型）
- 智能问答（调用AI模型进行问答）
- 收藏功能（收藏有价值的问答记录）
- 分享功能（将问答分享到群组）
- 导出功能（支持多种格式导出问答）
- 微信小程序登录

## 项目结构

```
smartai/
├── README.md                     # 项目说明文档
├── requirements.txt             # 项目依赖
├── Dockerfile                   # Docker镜像配置
├── gunicorn.conf.py            # Gunicorn生产环境配置
├── .env                         # 环境变量配置文件（本地）
├── .gitignore                   # Git忽略配置
├── database_design.md          # 数据库设计文档
├── main.py                     # 主应用文件（包含所有路由和模型）
├── simple_run.py               # 开发环境启动脚本
├── start_server.py             # 启动脚本
├── windows_start.py            # Windows启动脚本
├── validate_app.py             # 应用验证脚本
├── server.py                   # 服务器配置
├── Untitled-1.py               # 旧测试文件（待清理）
├── Untitled-1_fixed.py         # 旧测试文件（待清理）
├── Untitled-1_modified.py      # 旧测试文件（待清理）
├── uploads/                    # 上传文件存储目录
├── __pycache__/                # Python缓存目录
├── venv/                       # 虚拟环境目录
├── file_management.db          # SQLite数据库文件
├── knowledge_system.db         # SQLite数据库文件
├── test.db                     # SQLite数据库文件
└── Users/                      # 不必要的用户目录（待清理）
```

## 环境配置

在运行项目之前，请确保创建`.env`文件并配置以下环境变量：

```env
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./knowledge_system.db
MODEL_SERVICE_URL=http://localhost:5000
MODEL_TIMEOUT=30.0
WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-app-secret
```

## 快速开始

### 本地开发

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 启动开发服务器：

```bash
python simple_run.py
```

3. 访问 `http://127.0.0.1:8002` 查看API文档

### 生产环境部署

使用Docker部署：

```bash
# 构建镜像
docker build -t knowledge-qa-system .

# 运行容器
docker run -p 8000:8000 knowledge-qa-system
```

或使用Gunicorn直接运行：

```bash
gunicorn main:app -c gunicorn.conf.py
```

## API文档

启动服务后，可通过以下地址访问API文档：

- Swagger UI: `/docs`
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