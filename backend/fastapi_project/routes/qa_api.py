from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import sys
from pathlib import Path
import json
import traceback

# 添加项目根目录到Python路径，以便导入核心服务
current_dir = Path(__file__).parent  # routes目录
backend_dir = current_dir.parent  # fastapi_project目录
project_root = backend_dir.parent.parent  # 项目根目录 (ai_model_service) - 需要多一级

# 将项目根目录添加到Python路径的开头
project_root_str = str(project_root.resolve())
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from core.service_interface import ask_question_interface, upload_file_interface
from utils.security import get_current_user
from models.database_models import User, GroupMember, Group
from database.db_config import get_db

router = APIRouter(prefix="/api/v1")


class AskQuestionRequest(BaseModel):
    model_config = {
        'extra': 'allow'
    }
    
    question: str
    knowledge_base_id: Optional[Union[str, int]] = Field(default=None, description="知识库ID（群组ID），与group_name二选一")
    model_alias: str = "default"
    stream: bool = False
    top_k: Optional[int] = None
    group_id: Optional[int] = None
    group_name: Optional[str] = Field(default=None, description="群组名称，与knowledge_base_id二选一")


class UploadFileRequest(BaseModel):
    file_path: str
    knowledge_base_id: str
    file_name: Optional[str] = None
    custom_metadata: Optional[Dict[str, Any]] = None


@router.post("/ask-question")
async def api_ask_question(
    request: AskQuestionRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    用户提问接口
    支持两种方式指定知识库：
    1. 通过 knowledge_base_id（群组ID）
    2. 通过 group_name（群组名称）
    """
    try:
        group_id_int = None
        
        # 优先使用 knowledge_base_id
        if request.knowledge_base_id is not None:
            group_id_int = int(request.knowledge_base_id)
        elif request.group_name is not None:
            # 如果提供了 group_name，查询群组ID
            group = db.query(Group).join(GroupMember).filter(
                Group.name == request.group_name,
                GroupMember.user_id == current_user.id
            ).first()
            if not group:
                raise HTTPException(status_code=404, detail=f"群组 '{request.group_name}' 不存在或您不在该群组中")
            group_id_int = group.id
        else:
            raise HTTPException(status_code=400, detail="请提供 knowledge_base_id 或 group_name 来指定知识库")
        
        # 检查用户是否有提问权限
        group_member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id_int,
            GroupMember.user_id == current_user.id
        ).first()
        if not group_member:
            raise HTTPException(status_code=403, detail="您不是该知识库的成员，无法提问")
        
        # 调试：检查接收到的问题
        print(f"[DEBUG] Received question: {request.question}")
        print(f"[DEBUG] Question type: {type(request.question)}")
        if isinstance(request.question, str):
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in request.question)
            print(f"[DEBUG] Contains Chinese: {has_chinese}")
            chinese_count = sum(1 for char in request.question if '\u4e00' <= char <= '\u9fff')
            print(f"[DEBUG] Chinese chars count: {chinese_count}")
        
        result = ask_question_interface(
            question=request.question,
            user_id=str(current_user.id),
            knowledge_base_id=str(group_id_int),  # 转换为字符串
            model_alias=request.model_alias,
            stream=request.stream,
            top_k=request.top_k
        )
        
        # 调试：检查 LLM 返回的答案
        if result["status"] == "success" and "answer" in result:
            answer = result["answer"]
            print(f"[DEBUG] LLM Answer: {answer}")
            print(f"[DEBUG] Answer type: {type(answer)}")
            if isinstance(answer, str):
                has_chinese = any('\u4e00' <= char <= '\u9fff' for char in answer)
                print(f"[DEBUG] Contains Chinese: {has_chinese}")
                chinese_count = sum(1 for char in answer if '\u4e00' <= char <= '\u9fff')
                print(f"[DEBUG] Chinese chars count: {chinese_count}")
        
        if result["status"] == "error":
            error_message = result.get("message", "未知错误")
            if not error_message:
                error_message = "未知错误"
            raise HTTPException(status_code=400, detail=error_message)
        
        # 使用JSONResponse确保中文不被转义
        return JSONResponse(
            content=result,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-file")
async def api_upload_file(
    request: UploadFileRequest,
    current_user: User = Depends(get_current_user)
):
    """
    文件上传接口
    """
    try:
        result = upload_file_interface(
            file_path=request.file_path,
            user_id=str(current_user.id),
            knowledge_base_id=request.knowledge_base_id,
            file_name=request.file_name,
            custom_metadata=request.custom_metadata
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "未知错误"))
        
        # 使用JSONResponse确保中文不被转义
        return JSONResponse(
            content=result,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
