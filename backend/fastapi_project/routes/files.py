from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Form, Response
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
from utils.file_storage import LocalFileStorage
from core.service_interface import upload_file_interface

router = APIRouter(prefix="/file", tags=["文件管理"])

# 初始化文件存储系统
storage = LocalFileStorage()


@router.post("/upload", response_model=FileInfoResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    original_filename: Optional[str] = Form(default=None),  # 允许客户端提供原始文件名
    group_id: Optional[str] = Form(default=None),
    category: str = Form(default="general"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传文件到个人空间或群组共享，并自动解析和向量化
    """
    # 限制文件大小 (例如最大50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    contents = await file.read()  # 使用await读取上传内容

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件过大，最大支持50MB")
    
    # 使用客户端提供的原始文件名，如果未提供则使用系统提供的文件名
    actual_original_filename = original_filename if original_filename else file.filename
    
    # 安全地生成唯一文件名（只包含字母、数字、下划线和点）
    safe_original_filename = "".join(c for c in actual_original_filename if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()
    unique_filename = f"{uuid.uuid4()}_{safe_original_filename}"
    
    # 将字符串类型的group_id转换为整数（如果存在）
    group_id_int = None
    if group_id is not None:
        try:
            group_id_int = int(group_id)
        except ValueError:
            logger.error(f"无效的群组ID: {group_id}")
            raise HTTPException(status_code=400, detail="无效的群组ID")
    
    # 使用存储系统保存文件
    try:
        storage_path = storage.save_file(contents, unique_filename, group_id_int)
    except Exception as e:
        logger.error(f"保存文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="保存文件失败")
    
    # 获取文件大小
    file_size = len(contents)
    file_type = determine_file_type(file.filename)
    
    # 创建文件信息记录
    db_file_info = FileInfo(
        filename=storage_path,  # 存储相对路径而不是文件名
        original_filename=actual_original_filename,  # 使用客户端提供的或实际的原始文件名
        file_size=file_size,
        content_type=file.content_type or "application/octet-stream",
        uploader_id=current_user.id,
        group_id=group_id_int,
        file_category=category,
        file_type=file_type.value
    )
    db.add(db_file_info)
    try:
        db.commit()
        db.refresh(db_file_info)
        logger.info(f"用户 {current_user.username} 上传了文件 {actual_original_filename}")
        
        # 获取文件完整路径用于解析
        file_path = storage.get_file_path(storage_path)
        
        # 使用知识库ID（群组ID作为知识库ID）
        knowledge_base_id = str(group_id_int) if group_id_int else f"user_{current_user.id}"
        
        # 自动解析和向量化文件
        try:
            logger.info(f"开始解析文件: {actual_original_filename} (知识库ID: {knowledge_base_id})")
            parse_result = upload_file_interface(
                file_path=file_path,
                user_id=str(current_user.id),
                knowledge_base_id=knowledge_base_id,
                file_name=actual_original_filename
            )
            logger.info(f"文件解析完成: {parse_result}")
        except Exception as e:
            logger.error(f"文件解析失败: {str(e)}")
            # 解析失败不影响文件上传成功，但记录错误
        
        return db_file_info
    except Exception as e:
        # 清理已保存的文件
        storage.delete_file(storage_path)
        db.rollback()
        logger.error(f"保存文件信息时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="保存文件信息时发生错误")
