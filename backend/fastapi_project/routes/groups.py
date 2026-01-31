from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from schemas.index import GroupCreate, GroupResponse
from models.database_models import User, Group, GroupMember
from database.db_config import get_db
from utils.security import get_current_user

router = APIRouter(prefix="/group", tags=["群组管理"])

@router.post("/create", response_model=GroupResponse, summary="创建群组")
async def create_group(
    group: GroupCreate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
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
    
    from utils.security import logger
    logger.info(f"用户 {current_user.username} 创建了群组 {db_group.name}")
    return db_group

@router.get("/list", response_model=List[GroupResponse], summary="获取群组列表")
async def get_groups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    获取用户所属的所有群组
    """
    groups = db.query(Group).join(GroupMember).filter(GroupMember.user_id == current_user.id).all()
    return groups