from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import datetime
import os
import secrets
import string
from http import HTTPStatus

from schemas.index import ShareToGroupRequest, WeChatCodeRequest, WeChatLoginResponse
from models.database_models import User, QaRecord, Group, GroupMember
from database.db_config import get_db
from utils.security import get_current_user, create_access_token, get_password_hash, logger
import httpx
import os

router = APIRouter(tags=["其他功能"])

# 从环境变量中获取微信配置
WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")

@router.post("/share/to_group", summary="群组分享")
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

# 导出功能
@router.get("/export/qa/{qa_id}", summary="导出问答")
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

@router.get("/", summary="API根路径")
def read_root():
    return {"message": "欢迎使用知识问答系统API"}

@router.get("/health", summary="健康检查")
def health_check():
    """
    健康检查端点，用于监控服务状态
    """
    return {"status": "healthy", "service": "Knowledge QA System"}

@router.post("/wechat/login", response_model=WeChatLoginResponse, summary="微信小程序登录")
async def wechat_login(request: WeChatCodeRequest, db: Session = Depends(get_db)):
    """
    微信小程序登录接口
    通过微信登录凭证(code)换取用户openid和session_key
    """
    # 如果没有配置微信AppID和AppSecret，使用模拟模式（仅用于开发测试）
    if not WECHAT_APP_ID or not WECHAT_APP_SECRET:
        logger.warning("未配置微信小程序AppID或AppSecret，使用模拟登录模式")
        
        # 使用请求中的code生成模拟用户信息
        # 在开发模式下，使用code的一部分作为模拟的openid
        import hashlib
        simulated_openid = hashlib.md5(request.code.encode()).hexdigest()[:16]
        
        # 检查用户是否已存在，如果不存在则创建一个新用户
        # 使用模拟的openid作为用户名前缀，加上"wx_"标识
        wx_username = f"wx_{simulated_openid}"
        user = db.query(User).filter(User.username == wx_username).first()
        
        if not user:
            # 创建新用户
            # 为微信用户设置一个安全的默认密码哈希（对于微信登录用户来说，实际不需要密码）
            # 使用预生成的安全密码哈希，避免长度问题
            # 这个哈希值对应于一个安全的默认密码
            hashed_password = "$2b$12$LQv3cSHxEOJEteUcqM1bbeFn0qzHqrXJdm2KC4TmNFZZgSJj3VZ.q"  # 预生成的哈希值
            
            user = User(
                username=wx_username,
                email=f"{wx_username}@weixin.example.com",  # 临时邮箱
                hashed_password=hashed_password
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"开发模式：创建模拟微信用户: {wx_username}")

        # 生成访问令牌
        access_token_expires = datetime.timedelta(minutes=30)  # 使用默认值
        access_token = create_access_token(
            data={"sub": user.username}
        )
        
        logger.info(f"开发模式：模拟微信用户登录: {wx_username}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username
        }
    else:
        # 正常的微信登录流程
        try:
            # 请求微信服务器获取用户信息
            wx_session_url = (
                f"https://api.weixin.qq.com/sns/jscode2session?"
                f"appid={WECHAT_APP_ID}&secret={WECHAT_APP_SECRET}&js_code={request.code}"
                f"&grant_type=authorization_code"
            )
            
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
                # 为微信用户设置一个安全的默认密码哈希（对于微信登录用户来说，实际不需要密码）
                # 使用预生成的安全密码哈希，避免长度问题
                # 这个哈希值对应于一个安全的默认密码
                hashed_password = "$2b$12$LQv3cSHxEOJEteUcqM1bbeFn0qzHqrXJdm2KC4TmNFZZgSJj3VZ.q"  # 预生成的哈希值
                
                user = User(
                    username=wx_username,
                    email=f"{wx_username}@weixin.example.com",  # 临时邮箱
                    hashed_password=hashed_password
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"微信用户注册: {wx_username}")

            # 生成访问令牌
            access_token_expires = datetime.timedelta(minutes=30)  # 使用默认值
            access_token = create_access_token(
                data={"sub": user.username}
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