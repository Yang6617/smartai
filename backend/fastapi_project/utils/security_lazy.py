from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from jose import jwt
from jose.exceptions import JWTError
from pydantic import ValidationError
from typing import Optional
import datetime
import os
import logging
from dotenv import load_dotenv
from models.database_models import User
from schemas.index import TokenData
from database.db_config import get_db
import hashlib
import secrets

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# JWT配置 - 从环境变量读取
SECRET_KEY = os.getenv("SECRET_KEY", "your-default-secret-key-change-this")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# 安全配置
oauth2_scheme = HTTPBearer()

# 用于存储bcrypt上下文的全局变量
_bcrypt_context = None

def _get_bcrypt_context():
    """懒加载bcrypt上下文，避免启动时初始化错误"""
    global _bcrypt_context
    if _bcrypt_context is None:
        try:
            from passlib.context import CryptContext
            _bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        except ImportError:
            logger.error("passlib/bcrypt not available")
            raise
        except Exception as e:
            logger.error(f"Error initializing bcrypt context: {e}")
            raise
    return _bcrypt_context

def verify_password(plain_password, hashed_password):
    """验证密码"""
    try:
        pwd_context = _get_bcrypt_context()
        # 检查密码长度
        if len(plain_password.encode('utf-8')) > 72:
            # 截断到72字节以内再验证
            plain_password = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password):
    """生成密码哈希"""
    try:
        pwd_context = _get_bcrypt_context()
        # 检查密码长度
        if len(password.encode('utf-8')) > 72:
            # 截断到72字节以内
            password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise


def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user