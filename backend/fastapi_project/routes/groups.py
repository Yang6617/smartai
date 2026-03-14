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
    
    # 自动将创建者加入群组，并设置为管理员
    member = GroupMember(group_id=db_group.id, user_id=current_user.id, role="admin")
    db.add(member)
    db.commit()
    db.refresh(member)
    
    # 加载用户名
    member.user = db.query(User).filter(User.id == current_user.id).first()
    
    # 加载成员列表
    db_group.members = [member]
    
    from utils.security import logger
    logger.info(f"用户 {current_user.username} 创建了群组 {db_group.name}")
    return db_group

@router.get("/list", response_model=List[GroupResponse], summary="获取群组列表")
async def get_groups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    获取用户所属的所有群组
    """
    groups = db.query(Group).join(GroupMember).filter(GroupMember.user_id == current_user.id).all()
    
    # 为每个群组加载成员列表（包含角色信息和用户名）
    for group in groups:
        members = db.query(GroupMember).filter(GroupMember.group_id == group.id).all()
        # 加载用户名
        for member in members:
            member.user = db.query(User).filter(User.id == member.user_id).first()
        group.members = members
    
    return groups

@router.post("/add-member", summary="添加群组成员")
async def add_group_member(
    group_id: int,
    user_id: int,
    role: str = "member",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    管理员添加新成员到群组
    """
    # 验证群组是否存在
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 验证当前用户是否为管理员
    current_member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    ).first()
    if not current_member or current_member.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以添加成员")
    
    # 验证用户是否已存在
    existing_member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    if existing_member:
        raise HTTPException(status_code=400, detail="用户已加入该群组")
    
    # 添加成员
    member = GroupMember(group_id=group_id, user_id=user_id, role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    
    # 加载用户名
    member.user = db.query(User).filter(User.id == user_id).first()
    
    from utils.security import logger
    logger.info(f"用户 {current_user.username} 将用户 {user_id} 添加到群组 {group_id}")
    
    return member

@router.delete("/remove-member", summary="移除群组成员")
async def remove_group_member(
    group_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    管理员移除群组成员
    """
    # 验证群组是否存在
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 验证当前用户是否为管理员
    current_member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    ).first()
    if not current_member or current_member.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以移除成员")
    
    # 验证要移除的成员是否存在
    member_to_remove = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    if not member_to_remove:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    # 不能移除群组所有者
    if group.owner_id == user_id:
        raise HTTPException(status_code=400, detail="不能移除群组所有者")
    
    # 不能移除自己
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能移除自己，需要转让所有权或退出群组")
    
    # 移除成员
    db.delete(member_to_remove)
    db.commit()
    
    from utils.security import logger
    logger.info(f"用户 {current_user.username} 移除了群组 {group_id} 中的成员 {user_id}")
    
    return {"message": f"成员 {user_id} 已成功移除"}

@router.put("/update-member-role", summary="更新成员角色")
async def update_member_role(
    group_id: int,
    user_id: int,
    role: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    管理员更新成员角色
    """
    # 验证群组是否存在
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 验证当前用户是否为管理员
    current_member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    ).first()
    if not current_member or current_member.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以更新成员角色")
    
    # 验证要更新的成员是否存在
    member_to_update = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    if not member_to_update:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    # 验证角色值
    if role not in ["admin", "member"]:
        raise HTTPException(status_code=400, detail="无效的角色值，必须是 'admin' 或 'member'")
    
    # 更新角色
    member_to_update.role = role
    db.commit()
    db.refresh(member_to_update)
    
    # 加载用户名
    member_to_update.user = db.query(User).filter(User.id == user_id).first()
    
    from utils.security import logger
    logger.info(f"用户 {current_user.username} 将群组 {group_id} 中的成员 {user_id} 角色更新为 {role}")
    
    return member_to_update