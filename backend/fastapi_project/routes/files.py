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
    上传文件到个人空间或群组共享
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
        return db_file_info
    except Exception as e:
        # 清理已保存的文件
        storage.delete_file(storage_path)
        db.rollback()
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


@router.get("/{file_id}", summary="下载文件")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    下载指定ID的文件
    """
    # 获取文件信息
    file_info = db.query(FileInfo).filter(FileInfo.id == file_id).first()
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 检查用户是否有权限访问此文件
    if file_info.group_id is not None:
        # 如果文件属于某个群组，检查用户是否属于该群组
        membership = db.query(GroupMember).filter(
            GroupMember.user_id == current_user.id,
            GroupMember.group_id == file_info.group_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="您没有权限访问此文件")
    else:
        # 如果是个人文件，检查是否为当前用户上传
        if file_info.uploader_id != current_user.id:
            raise HTTPException(status_code=403, detail="您没有权限访问此文件")
    
    # 使用存储系统加载文件
    try:
        file_data = storage.load_file(file_info.filename)
        # 使用实际的内容类型，如果为空则使用默认值
        content_type = file_info.content_type or "application/octet-stream"
        return Response(
            content=file_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename*=utf-8''{file_info.original_filename}"
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件未找到")
    except Exception as e:
        logger.error(f"加载文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="加载文件失败")


@router.delete("/{file_id}", summary="删除文件")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除指定ID的文件
    """
    # 获取文件信息
    file_info = db.query(FileInfo).filter(FileInfo.id == file_id).first()
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 检查用户是否有权限删除此文件
    if file_info.uploader_id != current_user.id:
        raise HTTPException(status_code=403, detail="您没有权限删除此文件")
    
    # 使用存储系统删除文件
    try:
        success = storage.delete_file(file_info.filename)
        if not success:
            logger.warning(f"物理文件删除失败: {file_info.filename}")
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除文件失败")
    
    # 从数据库中删除记录
    try:
        db.delete(file_info)
        db.commit()
        logger.info(f"用户 {current_user.username} 删除了文件 {file_info.original_filename}")
        return {"message": "文件删除成功"}
    except Exception as e:
        db.rollback()
        logger.error(f"删除文件记录时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="删除文件记录失败")