from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional, Dict, Any
from pydantic import BaseModel
import sys
import os

# 添加项目根目录到Python路径，以便导入核心服务
current_dir = os.path.dirname(os.path.abspath(__file__))  # routes目录
backend_dir = os.path.dirname(current_dir)  # fastapi_project目录
project_root = os.path.dirname(backend_dir)  # 项目根目录 (ai_model_service)
project_root = os.path.abspath(project_root)  # 确保是绝对路径

# 将项目根目录添加到Python路径的开头
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.service_interface import ask_question_interface, upload_file_interface
from utils.security import get_current_user
from models.database_models import User
import json

router = APIRouter(prefix="/api/v1")


class AskQuestionRequest(BaseModel):
    model_config = {'protected_namespaces': ()}  # 禁用模型字段保护命名空间
    
    question: str
    knowledge_base_id: str
    model_alias: str = "default"
    stream: bool = False
    top_k: Optional[int] = None
    group_id: Optional[int] = None  # 添加群组ID参数


class UploadFileRequest(BaseModel):
    file_path: str
    knowledge_base_id: str
    file_name: Optional[str] = None
    custom_metadata: Optional[Dict[str, Any]] = None


@router.post("/ask-question")
async def api_ask_question(
    request: AskQuestionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    用户提问接口
    """
    try:
        result = ask_question_interface(
            question=request.question,
            user_id=str(current_user.id),
            knowledge_base_id=request.knowledge_base_id,
            model_alias=request.model_alias,
            stream=request.stream,
            top_k=request.top_k
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "未知错误"))
        
        return result
    except Exception as e:
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
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/list")
async def list_documents(
    knowledge_base_id: str,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """
    获取知识库文档列表
    """
    try:
        # 这里应该查询数据库获取文档列表
        # 由于没有具体的文档模型，这里返回模拟数据
        # 在实际实现中，这应该连接到数据库或向量存储
        documents = []
        
        # 模拟文档数据
        for i in range((page-1)*limit, page*limit):
            documents.append({
                "id": i+1,
                "filename": f"document_{i+1}.pdf",
                "size": 1024 * (i+1),  # 模拟文件大小
                "upload_time": "2023-01-01T00:00:00Z",
                "knowledge_base_id": knowledge_base_id
            })
        
        return {
            "data": documents[(page-1)*limit:page*limit],
            "total": 100,
            "page": page,
            "limit": limit,
            "has_more": page * limit < 100
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qa/list")
async def get_qa_history(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    knowledge_base_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    获取问答历史记录
    """
    try:
        # 模拟问答历史数据
        # 在实际实现中，这应该查询数据库中的问答记录
        history = []
        
        for i in range((page-1)*page_size, page*page_size):
            history.append({
                "id": i+1,
                "question": f"问题 {i+1}",
                "answer": f"这是对问题 {i+1} 的答案...",
                "timestamp": "2023-01-01T00:00:00Z",
                "knowledge_base_id": knowledge_base_id or "default_kb"
            })
        
        return {
            "data": history,
            "total": 200,
            "page": page,
            "page_size": page_size,
            "has_more": page * page_size < 200
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))