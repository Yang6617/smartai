from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from pathlib import Path

# 加载环境变量
load_dotenv()

# 获取 fastapi_project 目录（db_config.py 的父目录的父目录）
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库配置 - 从环境变量读取
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"sqlite:///{BASE_DIR / 'knowledge_system.db'}"
    # 如使用PostgreSQL: "postgresql://user:password@localhost/dbname"
    # 如使用MySQL: "mysql+pymysql://user:password@localhost/dbname"
)

if DATABASE_URL.startswith("postgres"):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
elif DATABASE_URL.startswith("mysql"):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()