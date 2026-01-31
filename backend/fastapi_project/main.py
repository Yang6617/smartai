import sys
import os

# 添加项目根目录到Python路径，以便导入核心服务
current_file_dir = os.path.dirname(os.path.abspath(__file__))  # fastapi_project目录
project_root = os.path.dirname(current_file_dir)  # 项目根目录 (ai_model_service)
project_root = os.path.abspath(project_root)  # 确保是绝对路径

# 将项目根目录添加到Python路径的开头
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from pydantic import BaseModel
from typing import Optional, List
import datetime
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
import uuid
from enum import Enum
import secrets
import httpx  # 用于调用模型服务
import hashlib
import json
import logging
from dotenv import load_dotenv  # 新增

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# JWT配置 - 从环境变量读取
SECRET_KEY = os.getenv("SECRET_KEY", "your-default-secret-key-change-this")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# 数据库配置 - 从环境变量读取
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./knowledge_system.db"
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

# 定义枚举类型
class MediaType(str, Enum):
    text = "text"
    image = "image"
    audio = "audio"


class FileType(str, Enum):
    document = "document"
    image = "image"
    video = "video"
    audio = "audio"
    other = "other"


# 用户模型
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# 群组模型
class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 关系
    owner = relationship("User")
    members = relationship("GroupMember", back_populates="group")
    files = relationship("FileInfo", back_populates="group")

# 群组成员关系模型
class GroupMember(Base):
    __tablename__ = "group_members"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 关系
    group = relationship("Group", back_populates="members")
    user = relationship("User")

# 文件信息模型
class FileInfo(Base):
    __tablename__ = "file_info"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    original_filename = Column(String)
    file_size = Column(Integer)
    content_type = Column(String)
    upload_time = Column(DateTime, default=datetime.datetime.utcnow)
    uploader_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)  # 可选的群组关联
    file_category = Column(String, default="general")  # 文件分类
    file_type = Column(String, default=FileType.other)  # 文件类型
    
    # 关系
    uploader = relationship("User")
    group = relationship("Group", back_populates="files")

# 问答记录模型
class QaRecord(Base):
    __tablename__ = "qa_records"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text)
    answer = Column(Text)
    media_type = Column(String, default="text")
    user_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)  # 可选的群组关联
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    source_document_id = Column(Integer, ForeignKey("file_info.id"), nullable=True)  # 来源文档ID
    
    # 关系
    user = relationship("User")
    group = relationship("Group")
    source_document = relationship("FileInfo")  # 问答来源文档

# 收藏记录模型
class Favorite(Base):
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    qa_record_id = Column(Integer, ForeignKey("qa_records.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 关系
    user = relationship("User")
    qa_record = relationship("QaRecord")

# Pydantic模型定义
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class GroupCreate(BaseModel):
    name: str
    description: str

class GroupResponse(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class FileInfoResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    upload_time: datetime.datetime
    uploader_id: int
    group_id: Optional[int] = None
    file_category: str
    file_type: str

    class Config:
        from_attributes = True

class QaCreate(BaseModel):
    question: str
    media_type: MediaType = MediaType.text
    group_id: Optional[int] = None
    source_document_id: Optional[int] = None

class QaResponse(BaseModel):
    id: int
    question: str
    answer: str
    media_type: str
    user_id: int
    group_id: Optional[int] = None
    source_document_id: Optional[int] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class FavoriteCreate(BaseModel):
    qa_record_id: int

class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    qa_record_id: int
    qa_record: QaResponse
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ShareToGroupRequest(BaseModel):
    qa_record_id: int
    target_group_id: int

class WeChatCodeRequest(BaseModel):
    code: str

class WeChatLoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI实例
app = FastAPI(title="知识问答系统", description="支持群组管理、知识库管理、多媒体问答、收藏和分享功能的系统")

# 包含新的API路由
from routes.qa_api import router as qa_api_router
app.include_router(qa_api_router)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全配置
oauth2_scheme = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT工具函数
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

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

# 文件上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 添加模型服务配置
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:5000")  # 模型服务地址
MODEL_TIMEOUT = float(os.getenv("MODEL_TIMEOUT", "30.0"))  # 模型服务超时时间

async def get_answer_from_model(question: str, context: Optional[str] = None, document_id: Optional[int] = None):
    """
    调用AI模型获取答案
    """
    try:
        async with httpx.AsyncClient(timeout=MODEL_TIMEOUT) as client:
            payload = {
                "question": question,
                "context": context or "",
                "document_id": document_id  # 如果有文档ID，传递给模型服务
            }
            response = await client.post(f"{MODEL_SERVICE_URL}/predict", json=payload)
            
            # 检查HTTP错误
            if response.status_code != 200:
                logger.warning(f"Model service returned status {response.status_code}: {response.text}")
                # 返回一个更友好的消息而不是直接报错
                return f"参考问题: {question}\n\n这是模拟响应，实际模型服务暂不可用。请稍后重试或联系管理员。"
            
            try:
                result = response.json()
            except json.JSONDecodeError:
                logger.warning(f"Model service returned invalid JSON: {response.text}")
                return f"参考问题: {question}\n\n模型服务返回的数据格式错误。这是模拟响应。"
            
            # 检查返回的数据结构
            if "answer" not in result:
                logger.warning(f"Model service response missing 'answer' field: {result}")
                return f"参考问题: {question}\n\n模型服务返回的数据格式错误。这是模拟响应。"
                
            return result.get("answer", "抱歉，我暂时无法回答您的问题。")
    except httpx.TimeoutException:
        logger.warning(f"Model service timeout after {MODEL_TIMEOUT}s")
        # 超时时返回模拟响应而不是抛出异常
        return f"参考问题: {question}\n\n模型服务响应超时，这是模拟响应。请稍后重试。"
    except httpx.RequestError as e:
        logger.error(f"Error calling model service: {e}")
        # 请求错误时返回模拟响应而不是抛出异常
        return f"参考问题: {question}\n\n模型服务暂时不可用，请稍后再试。这是模拟响应。"
    except Exception as e:
        logger.error(f"Unexpected error calling model service: {e}")
        # 其他异常也返回模拟响应
        return f"参考问题: {question}\n\n处理您的问题时发生错误。这是模拟响应。"


def determine_file_type(filename: str) -> FileType:
    """根据文件扩展名判断文件类型"""
    ext = Path(filename).suffix.lower()
    if ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx']:
        return FileType.document
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
        return FileType.image
    elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']:
        return FileType.video
    elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg']:
        return FileType.audio
    else:
        return FileType.other

# 1. 用户认证功能
@app.post("/register", response_model=UserResponse, summary="用户注册")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    注册新用户
    """
    db_user = get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"新用户注册: {user.username}")
    return db_user

@app.post("/login", response_model=Token, summary="用户登录")
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
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    logger.info(f"用户登录: {credentials.username}")
    return {"access_token": access_token, "token_type": "bearer"}

# 2. 群组管理功能
@app.post("/group/create", response_model=GroupResponse, summary="创建群组")
async def create_group(group: GroupCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    创建一个新的群组
    """
    db_group = Group(
        name=group.name,
        description=group.description,
        owner_id=current_user.id
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    
    # 自动将创建者加入群组
    member = GroupMember(group_id=db_group.id, user_id=current_user.id)
    db.add(member)
    db.commit()
    
    logger.info(f"用户 {current_user.username} 创建了群组 {db_group.name}")
    return db_group

@app.get("/group/list", response_model=List[GroupResponse], summary="获取群组列表")
async def get_groups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    获取用户所属的所有群组
    """
    groups = db.query(Group).join(GroupMember).filter(GroupMember.user_id == current_user.id).all()
    return groups

# 2. 知识库管理功能
@app.post("/file/upload", response_model=FileInfoResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    group_id: Optional[int] = Query(None, description="群组ID，如果不指定则上传到个人空间"),
    category: str = Query("general", description="文件分类"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传文件到个人空间或群组共享
    """
    # 限制文件大小 (例如最大50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    contents = await file.read()  # 使用await读取上传内容

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件过大，最大支持50MB")
    
    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_location = UPLOAD_DIR / unique_filename
    
    # 异步写入文件
    try:
        with open(file_location, "wb") as file_object:
            file_object.write(contents)
    except Exception as e:
        logger.error(f"保存文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="保存文件失败")
    
    # 获取文件大小
    file_size = os.path.getsize(file_location)
    file_type = determine_file_type(file.filename)
    
    # 创建文件信息记录
    db_file_info = FileInfo(
        filename=unique_filename,
        original_filename=file.filename,
        file_size=file_size,
        content_type=file.content_type or "application/octet-stream",
        uploader_id=current_user.id,
        group_id=group_id,
        file_category=category,
        file_type=file_type.value
    )
    db.add(db_file_info)
    try:
        db.commit()
        db.refresh(db_file_info)
        logger.info(f"用户 {current_user.username} 上传了文件 {file.filename}")
        return db_file_info
    except Exception as e:
        # 清理已保存的文件
        if file_location.exists():
            file_location.unlink()
        db.rollback()
        logger.error(f"保存文件信息时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="保存文件信息时发生错误")


@app.get("/knowledge/list", response_model=List[FileInfoResponse], summary="高级检索文档")
async def list_knowledge(
    group_id: Optional[int] = Query(None, description="群组ID，如果不指定则查询个人空间"),
    category: Optional[str] = Query(None, description="文件分类"),
    file_type: Optional[FileType] = Query(None, description="文件类型"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, le=100, description="返回的最大记录数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    支持按群组、分类、关键词搜索文档，支持排序和分页
    """
    query = db.query(FileInfo)
    
    # 如果指定了群组ID，验证用户是否属于该群组
    if group_id is not None:
        membership = db.query(GroupMember).filter(
            GroupMember.user_id == current_user.id,
            GroupMember.group_id == group_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="您不是目标群组的成员，无法访问该群组的文件")
        query = query.filter(FileInfo.group_id == group_id)
    else:
        query = query.filter(FileInfo.uploader_id == current_user.id).filter(FileInfo.group_id.is_(None))
        
    if category is not None:
        query = query.filter(FileInfo.file_category == category)
        
    if file_type is not None:
        query = query.filter(FileInfo.file_type == file_type.value)
        
    if keyword is not None:
        query = query.filter(FileInfo.original_filename.contains(keyword))
    
    # 排序和分页
    files = query.order_by(FileInfo.upload_time.desc()).offset(skip).limit(limit).all()
    return files

# 3. 多媒体问答功能
@app.post("/qa/ask", response_model=QaResponse, summary="智能问答")
async def ask_question(
    qa_create: QaCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    基于知识库内容进行问答
    """
    # 如果指定了群组ID，验证用户是否属于该群组
    if qa_create.group_id:
        membership = db.query(GroupMember).filter(
            GroupMember.user_id == current_user.id,
            GroupMember.group_id == qa_create.group_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="您不是目标群组的成员，无法在该群组中提问")
    
    # 如果指定了来源文档，验证用户是否有权访问该文档
    source_document_id = None
    if qa_create.source_document_id:
        doc = db.query(FileInfo).filter(FileInfo.id == qa_create.source_document_id).first()
        if not doc or (doc.uploader_id != current_user.id and doc.group_id not in [gm.group_id for gm in db.query(GroupMember).filter(GroupMember.user_id == current_user.id).all()]):
            raise HTTPException(status_code=403, detail="您无权访问该文档")
        source_document_id = qa_create.source_document_id

    # 调用模型服务获取答案
    answer = await get_answer_from_model(qa_create.question, document_id=source_document_id)
    
    # 创建问答记录
    qa_record = QaRecord(
        question=qa_create.question,
        answer=answer,
        media_type=qa_create.media_type.value,
        user_id=current_user.id,
        group_id=qa_create.group_id,
        source_document_id=source_document_id
    )
    db.add(qa_record)
    try:
        db.commit()
        db.refresh(qa_record)
        logger.info(f"用户 {current_user.username} 创建了问答记录")
        return qa_record
    except Exception as e:
        db.rollback()
        logger.error(f"保存问答记录时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="保存问答记录时发生错误")


# 4. 收藏功能
@app.post("/favorite/add", response_model=FavoriteResponse, summary="添加收藏")
async def add_favorite(
    favorite: FavoriteCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    将有价值的问答记录收藏
    """
    # 检查问答记录是否存在
    qa_record = db.query(QaRecord).filter(QaRecord.id == favorite.qa_record_id).first()
    if not qa_record:
        raise HTTPException(status_code=404, detail="问答记录不存在")
    
    # 检查是否已收藏
    existing_favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.qa_record_id == favorite.qa_record_id
    ).first()
    
    if existing_favorite:
        raise HTTPException(status_code=400, detail="该问答记录已被收藏")
    
    # 检查是否有权限收藏此记录（必须是自己的或者在共享群组中的）
    if qa_record.user_id != current_user.id and qa_record.group_id not in [gm.group_id for gm in db.query(GroupMember).filter(GroupMember.user_id == current_user.id).all()]:
        raise HTTPException(status_code=403, detail="您没有权限收藏此问答记录")
    
    # 创建收藏记录
    favorite_record = Favorite(
        user_id=current_user.id,
        qa_record_id=favorite.qa_record_id
    )
    db.add(favorite_record)
    db.commit()
    db.refresh(favorite_record)
    
    # 加载关联的问答记录
    favorite_record.qa_record = db.query(QaRecord).filter(QaRecord.id == favorite.qa_record_id).first()
    logger.info(f"用户 {current_user.username} 收藏了问答记录 {favorite.qa_record_id}")
    return favorite_record

@app.get("/favorite/list", response_model=List[FavoriteResponse], summary="收藏列表")
async def list_favorites(
    skip: int = 0, 
    limit: int = 100, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    查看所有收藏的问答
    """
    favorites = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .offset(skip).limit(limit).all()
    )
    
    # 为每个收藏加载关联的问答记录
    for fav in favorites:
        fav.qa_record = db.query(QaRecord).filter(QaRecord.id == fav.qa_record_id).first()
    
    return favorites

@app.delete("/favorite/{fav_id}", summary="删除收藏")
async def delete_favorite(
    fav_id: int, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除不需要的收藏
    """
    favorite = db.query(Favorite).filter(
        Favorite.id == fav_id,
        Favorite.user_id == current_user.id
    ).first()
    
    if not favorite:
        raise HTTPException(status_code=404, detail="收藏记录不存在")
    
    db.delete(favorite)
    db.commit()
    logger.info(f"用户 {current_user.username} 删除了收藏记录 {fav_id}")
    
    return {"message": "收藏已成功删除"}

# 5. 分享功能
@app.post("/share/to_group", summary="群组分享")
async def share_to_group(
    share_request: ShareToGroupRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    将问答结果分享到指定群组
    """
    # 验证问答记录是否存在且属于当前用户
    qa_record = db.query(QaRecord).filter(
        QaRecord.id == share_request.qa_record_id,
        QaRecord.user_id == current_user.id
    ).first()
    if not qa_record:
        raise HTTPException(status_code=404, detail="问答记录不存在或不属于当前用户")
    
    # 验证目标群组是否存在
    target_group = db.query(Group).filter(Group.id == share_request.target_group_id).first()
    if not target_group:
        raise HTTPException(status_code=404, detail="目标群组不存在")
    
    # 验证用户是否属于目标群组
    membership = db.query(GroupMember).filter(
        GroupMember.user_id == current_user.id,
        GroupMember.group_id == share_request.target_group_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="您不是目标群组的成员，无法分享内容")
    
    # 更新问答记录的群组关联
    qa_record.group_id = share_request.target_group_id
    db.commit()
    logger.info(f"用户 {current_user.username} 将问答 {share_request.qa_record_id} 分享到了群组 {target_group.name}")
    
    return {"message": f"问答记录已成功分享到群组 {target_group.name}"}

# 6. 导出功能
@app.get("/export/qa/{qa_id}", summary="导出问答")
async def export_qa(
    qa_id: int, 
    format: str = Query(default="text", description="导出格式：text, json, markdown"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    将问答结果导出为不同格式
    """
    qa_record = db.query(QaRecord).filter(
        QaRecord.id == qa_id,
        QaRecord.user_id == current_user.id
    ).first()
    if not qa_record:
        raise HTTPException(status_code=404, detail="问答记录不存在或不属于当前用户")
    
    # 根据format参数返回不同的格式
    if format == "json":
        return {
            "question": qa_record.question,
            "answer": qa_record.answer,
            "created_at": qa_record.created_at.isoformat(),
            "media_type": qa_record.media_type,
            "group_name": db.query(Group).filter(Group.id == qa_record.group_id).first().name if qa_record.group_id else "个人空间",
        }
    elif format == "markdown":
        content = f"""# 问答记录\n\n**问题**: {qa_record.question}\n\n**答案**: \n\n{qa_record.answer}\n\n---\n*时间*: {qa_record.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n*类型*: {qa_record.media_type}\n*位置*: {db.query(Group).filter(Group.id == qa_record.group_id).first().name if qa_record.group_id else '个人空间'}"""
        return {"content": content, "format": "markdown"}
    else:  # 默认为text格式
        content = f"""
    问答导出报告
    =============
    
    问题: {qa_record.question}
    回答: {qa_record.answer}
    时间: {qa_record.created_at}
    类型: {qa_record.media_type}
    位置: {db.query(Group).filter(Group.id == qa_record.group_id).first().name if qa_record.group_id else '个人空间'}
    
    此内容由知识问答系统导出
    """
        return {
            "qa_id": qa_id,
            "question": qa_record.question,
            "answer": qa_record.answer,
            "exported_at": datetime.datetime.utcnow(),
            "format": format
        }

@app.get("/", summary="API根路径")
def read_root():
    return {"message": "欢迎使用知识问答系统API"}

@app.get("/health", summary="健康检查")
def health_check():
    """
    健康检查端点，用于监控服务状态
    """
    return {"status": "healthy", "service": "Knowledge QA System"}

# 添加微信登录接口
# 从环境变量中获取微信配置
WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")

@app.post("/wechat/login", response_model=WeChatLoginResponse, summary="微信小程序登录")
async def wechat_login(request: WeChatCodeRequest, db: Session = Depends(get_db)):
    """
    微信小程序登录接口
    通过微信登录凭证(code)换取用户openid和session_key
    """
    if not WECHAT_APP_ID or not WECHAT_APP_SECRET:
        raise HTTPException(
            status_code=500, 
            detail="服务器未配置微信小程序AppID或AppSecret"
        )

    # 请求微信服务器获取用户信息
    wx_session_url = (
        f"https://api.weixin.qq.com/sns/jscode2session?"
        f"appid={WECHAT_APP_ID}&secret={WECHAT_APP_SECRET}&js_code={request.code}"
        f"&grant_type=authorization_code"
    )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(wx_session_url)
            wx_response = response.json()

        if "errcode" in wx_response:
            logger.warning(f"微信登录失败: {wx_response.get('errmsg', 'Unknown error')}")
            raise HTTPException(
                status_code=401, 
                detail=f"微信登录失败: {wx_response.get('errmsg', 'Unknown error')}"
            )

        openid = wx_response.get("openid")
        if not openid:
            raise HTTPException(
                status_code=401, 
                detail="未能获取用户OpenID"
            )

        # 检查用户是否已存在，如果不存在则创建一个新用户
        # 使用openid作为用户名前缀，加上"wx_"标识
        wx_username = f"wx_{openid[:16]}"
        user = db.query(User).filter(User.username == wx_username).first()
        
        if not user:
            # 创建新用户
            user = User(
                username=wx_username,
                email=f"{wx_username}@weixin.example.com",  # 临时邮箱
                hashed_password=get_password_hash(secrets.token_urlsafe(16))  # 生成随机密码
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"微信用户注册: {wx_username}")

        # 生成访问令牌
        access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        logger.info(f"微信用户登录: {wx_username}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username
        }
    except httpx.RequestError as e:
        logger.error(f"WeChat API request error: {e}")
        raise HTTPException(status_code=500, detail="微信登录服务暂时不可用")
    except Exception as e:
        logger.error(f"Unexpected error during WeChat login: {e}")
        raise HTTPException(status_code=500, detail="处理微信登录时发生错误")