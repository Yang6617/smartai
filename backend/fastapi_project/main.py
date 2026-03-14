from passlib.context import CryptContext
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# 密码哈希配置
pwd_context = CryptContext(schemes=["bcrypt", "pbkdf2_sha256"])

# 创建FastAPI实例
app = FastAPI(
    title="知识问答系统", 
    description="支持群组管理、知识库管理、多媒体问答、收藏和分享功能的系统",
    default_response_class=JSONResponse,
    json_encoders={
        str: lambda x: x
    }
)

# 包含新的API路由
from routes.qa_api import router as qa_api_router
from routes.auth import router as auth_router
from routes.files import router as files_router
from routes.favorites import router as favorites_router
from routes.groups import router as groups_router
from routes.misc import router as misc_router

# 挂载API路由器
app.include_router(qa_api_router)
app.include_router(auth_router)  # auth 路由已经有 /auth 前缀
app.include_router(files_router)
app.include_router(favorites_router)
app.include_router(groups_router)
app.include_router(misc_router)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动时创建数据库表
from database.db_config import engine
from models.database_models import Base as DBBase

DBBase.metadata.create_all(bind=engine)
