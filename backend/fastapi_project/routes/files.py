from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import logging
from pathlib import Path

from schemas.index import FileInfoResponse
from models.database_models import User, FileInfo, FileType, GroupMember
from database.db_config import get_db
from utils.security import get_current_user, logger
from utils.helpers import determine_file_type

router = APIRouter(prefix="/file", tags=["文件管理"])

# 文件上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload", response_model=FileInfoResponse, summary="上传文件")
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
        logger = logging.getLogger(__name__)
        logger.error(f"保存文件信息时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="保存文件信息时发生错误")


@router.get("/list", response_model=List[FileInfoResponse], summary="高级检索文档")
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