from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging

from schemas.index import QaCreate, QaResponse
from models.database_models import User, QaRecord, FileInfo, GroupMember
from database.db_config import get_db
from utils.security import get_current_user, logger
from utils.ai_client import get_answer_from_model

router = APIRouter(prefix="/qa", tags=["问答"])

@router.post("/ask", response_model=QaResponse, summary="智能问答")
async def ask_question(
    qa_create: QaCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    基于知识库内容进行问答
    """
    # 如果指定了群组ID，验证用户是否属于该群组（仅群组成员可提问）
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