from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from schemas.index import FavoriteCreate, FavoriteResponse
from models.database_models import User, Favorite, QaRecord, GroupMember
from database.db_config import get_db
from utils.security import get_current_user, logger

router = APIRouter(prefix="/favorite", tags=["收藏"])

@router.post("/add", response_model=FavoriteResponse, summary="添加收藏")
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

@router.get("/list", response_model=List[FavoriteResponse], summary="收藏列表")
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

@router.delete("/{fav_id}", summary="删除收藏")
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
    from utils.security import logger
    logger.info(f"用户 {current_user.username} 删除了收藏记录 {fav_id}")
    
    return {"message": "收藏已成功删除"}