from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import logging

from schemas.index import UserCreate, UserLogin, Token, UserResponse
from models.database_models import User
from utils.security import authenticate_user, create_access_token, get_user
from database.db_config import get_db
from utils.security import get_password_hash

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])

@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    注册新用户
    临时修改：跳过密码哈希，方便测试
    """
    db_user = get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 临时修改：直接存储明文密码，跳过哈希处理
    # 正式环境应使用 get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=user.password  # 临时使用明文密码
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"新用户注册: {user.username}")
    return db_user

@router.post("/login", response_model=Token, summary="用户登录")
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录并获取访问令牌
    """
    user = authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = 30  # minutes
    access_token = create_access_token(
        data={"sub": user.username}
    )
    logger.info(f"用户登录: {credentials.username}")
    return {"access_token": access_token, "token_type": "bearer"}