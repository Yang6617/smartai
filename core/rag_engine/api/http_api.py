# rag_engine/api/http_api.py
"""
FastAPI HTTP + WebSocket API（面向微信小程序）

说明：
- 微信小程序不支持标准 HTTP Streaming/SSE，因此流式输出建议走 WebSocket。
- 本文件提供：
  1) HTTP：POST /rag/ask        —— 一次性返回完整答案（小程序可用）
  2) WS：  /ws/rag/ask         —— 流式返回（推荐，小程序体验最佳）
  3) 健康检查：GET /healthz

使用方式：
- 在启动脚本里构建好 RAGService，然后调用 create_app(rag_service) 获取 app
- 例：uvicorn.run(app, host="0.0.0.0", port=8000)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

# =========================================================
# 0) 确保项目根目录在 PYTHONPATH（解决 windows/直接运行时 import core 失败）
# =========================================================
_THIS_FILE = Path(__file__).resolve()

# 把可能的根目录都塞进去（重复插入无害）
for _p in [
    _THIS_FILE.parents[3],  # 常见：repo/
    _THIS_FILE.parents[4],  # 更深一层：repo/
    _THIS_FILE.parents[2],  # 兜底
]:
    if _p.exists():
        sys.path.insert(0, str(_p))

# =========================================================
# 1) 业务依赖：RAGService / ConversationState
# =========================================================
try:
    from core.rag_engine.api.rag_service import RAGService
except Exception:
    # 兼容你旧路径（如果尚未迁移）
    from core.vector_engine.api.rag_service import RAGService  # type: ignore

from core.rag_engine.query_understanding.context_state import ConversationState

# =========================================================
# 2) 兼容：orchestrator 可能从 rag_engine.prompt_builder import DEFAULT_TEMPLATES
#    如果 prompt_builder/__init__.py 未导出该变量，这里提前注入，避免运行时报错
# =========================================================
try:
    import rag_engine.prompt_builder as pb
    from core.rag_engine.prompt_builder.templates import DEFAULT_TEMPLATES

    if not hasattr(pb, "DEFAULT_TEMPLATES"):
        pb.DEFAULT_TEMPLATES = DEFAULT_TEMPLATES
except Exception:
    # 不影响服务启动（但建议你修一下 __init__.py 的导出）
    pass


# =========================================================
# 3) HTTP 请求/响应模型
# =========================================================
class AskRequestModel(BaseModel):
    question: str = Field(..., description="用户问题")
    knowledge_base_id: Optional[str] = Field(None, description="知识库ID（用于过滤检索）")
    conversation_id: Optional[str] = Field(None, description="会话ID（可选）")
    user_id: Optional[str] = Field(None, description="用户ID（可选，用于日志/权限）")
    top_k: Optional[int] = Field(None, description="覆盖默认 top_k（可选）")
    # 小程序 HTTP 模式不建议 stream=True；WebSocket 模式才是真流式
    stream: bool = Field(False, description="仅用于标识；HTTP接口默认非流式")


class AskResponseModel(BaseModel):
    answer: str
    citations: list
    debug: Optional[dict] = None


# =========================================================
# 4) WebSocket 消息协议（建议）
#   客户端发送：
#     {"question": "...", "knowledge_base_id": "...", "conversation_id": "...", "user_id": "...", "top_k": 8}
#
#   服务端返回（多条）：
#     {"type":"chunk","content":"..."}            # 流式片段
#     {"type":"end","citations":[...],"debug":{...}}  # 结束
#     {"type":"error","message":"..."}           # 错误
# =========================================================


def _build_state(req: Dict[str, Any]) -> ConversationState:
    """
    把请求字段写入 ConversationState，供检索过滤、日志等使用
    """
    state = ConversationState()
    # 你当前的 ConversationState dataclass 里未必有 conversation_id/user_id 字段；
    # 这里采用“尽量写入，有则写，无则忽略”的方式，避免破坏兼容性。
    kb_id = req.get("knowledge_base_id")
    if kb_id:
        state.user_context.knowledge_base_id = kb_id

    # 可选字段：如果你的 ConversationState 未定义这些属性，不要报错
    conv_id = req.get("conversation_id")
    if conv_id and hasattr(state, "conversation_id"):
        setattr(state, "conversation_id", conv_id)

    user_id = req.get("user_id")
    if user_id and hasattr(state.user_context, "user_id"):
        setattr(state.user_context, "user_id", user_id)

    return state


def _safe_json(obj: Any) -> str:
    """
    将对象安全序列化为 JSON（用于调试/日志）
    """
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def create_app(rag_service: RAGService) -> FastAPI:
    """
    创建 FastAPI app，并注入已构建好的 rag_service
    """
    app = FastAPI(
        title="RAG Inference Service (WeChat MiniProgram)",
        description="面向微信小程序的 RAG 推理服务：HTTP（非流式）+ WebSocket（流式）",
        version="1.0.0",
    )

    @app.get("/healthz")
    def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    # =====================================================
    # 1) HTTP：一次性返回（小程序最稳）
    # =====================================================
    @app.post("/rag/ask", response_model=AskResponseModel)
    def rag_ask(req: AskRequestModel):
        """
        一次性返回完整答案
        - 小程序 wx.request 可直接调用
        """
        try:
            state = _build_state(req.model_dump())

            # 注意：你目前的 RAGService.ask() 签名是否带 top_k 参数不确定
            # 为了兼容，我们采取“有则传，无则忽略”的方式
            kwargs = dict(
                question=req.question,
                model_alias="default",
                conversation_state=state,
                stream=False,
            )

            # 如果 RAGService.ask 支持 top_k，则传入
            if req.top_k is not None:
                kwargs["top_k"] = req.top_k

            resp = rag_service.ask(**kwargs)  # type: ignore
            # resp 是 dict：{"answer":..., "citations":..., "debug":...}
            return resp

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # =====================================================
    # 2) WebSocket：流式输出（小程序推荐）
    # =====================================================
    @app.websocket("/ws/rag/ask")
    async def rag_ask_ws(ws: WebSocket):
        """
        WebSocket 流式问答（推荐用于微信小程序）
        """
        await ws.accept()

        try:
            # 接收客户端第一条消息（JSON）
            req = await ws.receive_json()
            if not isinstance(req, dict):
                await ws.send_json({"type": "error", "message": "请求必须是 JSON 对象"})
                return

            question = (req.get("question") or "").strip()
            if not question:
                await ws.send_json({"type": "error", "message": "question 不能为空"})
                return

            state = _build_state(req)
            top_k = req.get("top_k", None)

            # 调用 rag_service.ask(stream=True)，返回 {"stream": generator, "citations":..., "debug":...}
            kwargs = dict(
                question=question,
                model_alias="default",
                conversation_state=state,
                stream=True,
            )
            if top_k is not None:
                kwargs["top_k"] = top_k

            result = rag_service.ask(**kwargs)  # type: ignore

            stream = result.get("stream")
            if stream is None:
                await ws.send_json({"type": "error", "message": "服务端未返回 stream"})
                return

            # 推送 chunk
            for chunk in stream:
                # 客户端按 chunk 拼接成完整答案
                await ws.send_json({"type": "chunk", "content": str(chunk)})

            # 推送结束消息
            await ws.send_json(
                {
                    "type": "end",
                    "citations": result.get("citations", []),
                    "debug": result.get("debug", None),
                }
            )

        except WebSocketDisconnect:
            # 客户端断开：无需报错
            return
        except Exception as e:
            # 异常：尽量回传给前端
            try:
                await ws.send_json({"type": "error", "message": str(e)})
            except Exception:
                # 如果连接已经不可写，直接吞掉
                return

    return app
