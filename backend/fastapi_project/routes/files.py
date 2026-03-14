from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Form, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import os
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

# 初始化文件存储系统（使用绝对路径）
storage = LocalFileStorage(base_path=str(Path(__file__).parent.parent / "uploads"))


@router.post("/upload", response_model=FileInfoResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    original_filename: Optional[str] = Form(default=None),  # 允许客户端提供原始文件名
    group_id: str = Form(...),  # 必须提供群组ID（知识库ID）
    category: str = Form(default="general"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传文件到知识库，并自动解析和向量化
    """
    # 限制文件大小 (例如最大50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    contents = await file.read()  # 使用await读取上传内容

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件过大，最大支持50MB")
    
    # 使用客户端提供的原始文件名，如果未提供则使用系统提供的文件名
    actual_original_filename = original_filename if original_filename else file.filename
    
    # 将字符串类型的group_id转换为整数
    try:
        group_id_int = int(group_id)
    except ValueError:
        logger.error(f"无效的群组ID: {group_id}")
        raise HTTPException(status_code=400, detail="无效的群组ID")
    
    # 检查用户是否有上传权限（只有管理员可以上传文件）
    group_member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id_int,
        GroupMember.user_id == current_user.id
    ).first()
    if not group_member or group_member.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以上传文件到知识库")
    
    # 使用存储系统保存文件（存储系统会处理文件名唯一性）
    try:
        storage_path = storage.save_file(contents, actual_original_filename, group_id_int)
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
        logger.info(f"用户 {current_user.username} 上传了文件 {actual_original_filename} 到知识库 {group_id_int}")
        
        # 获取文件完整路径用于解析
        file_path = storage.get_file_path(storage_path)
        
        # 使用知识库ID（群组ID作为知识库ID）
        knowledge_base_id = str(group_id_int)
        
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


@router.get("/download/{file_id}", summary="下载文件")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    下载文件，用户只能下载自己所在群组中的文件
    """
    # 查询文件信息
    file_info = db.query(FileInfo).filter(FileInfo.id == file_id).first()
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 检查用户是否在该文件所属的群组中
    group_member = db.query(GroupMember).filter(
        GroupMember.group_id == file_info.group_id,
        GroupMember.user_id == current_user.id
    ).first()
    
    if not group_member:
        raise HTTPException(status_code=403, detail="您没有权限下载该文件，您不在该文件所属的群组中")
    
    # 获取文件存储路径
    storage_path = file_info.filename
    
    # 验证文件是否存在
    try:
        file_path = storage.get_file_path(storage_path)
        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail="文件在服务器上不存在")
    except Exception as e:
        logger.error(f"获取文件路径失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取文件路径失败")
    
    # 读取文件内容
    try:
        file_data = storage.load_file(storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        logger.error(f"读取文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="读取文件失败")
    
    # 获取原始文件名
    original_filename = file_info.original_filename
    
    # 设置响应头，触发浏览器下载
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{original_filename}",
        "Content-Type": file_info.content_type or "application/octet-stream"
    }
    
    return Response(content=file_data, headers=headers)


@router.get("/list", response_model=List[FileInfoResponse], summary="获取群组文件列表")
async def list_files(
    group_id: int = Query(..., description="群组ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取群组中的所有文件列表，用户只能查看自己所在群组的文件
    """
    # 检查用户是否在该群组中
    group_member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    ).first()
    
    if not group_member:
        raise HTTPException(status_code=403, detail="您不在该群组中，无法查看文件列表")
    
    # 查询群组中的所有文件
    files = db.query(FileInfo).filter(FileInfo.group_id == group_id).all()
    
    return files
