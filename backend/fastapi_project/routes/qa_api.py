from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel
import sys
from pathlib import Path
import json

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
from models.database_models import User

router = APIRouter(prefix="/api/v1")


class AskQuestionRequest(BaseModel):
    # 完全不设置 Config，使用 Pydantic 默认配置
    question: str
    knowledge_base_id: Union[str, int]  # 支持字符串或整数类型
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
            knowledge_base_id=request.knowledge_base_id,
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
            raise HTTPException(status_code=400, detail=result.get("message", "未知错误"))
        
        # 使用JSONResponse确保中文不被转义
        return JSONResponse(
            content=result,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
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
        
        # 使用JSONResponse确保中文不被转义
        return JSONResponse(
            content=result,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
