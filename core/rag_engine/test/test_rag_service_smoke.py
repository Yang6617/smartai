"""
RAG 端到端 Smoke Test（增强版，可用于 CI）

增强点：
1) 验证 stream=True 的流式输出能力
2) 验证 knowledge_base_id 过滤是否生效（不会误召回其它 KB 的数据）

特点：
- 不依赖真实 Embedding 模型
- 不依赖真实 LLM
- 使用真实 ChromaDB（本地临时目录）
- 覆盖 ask() 的完整 RAG 链路
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

import sys
from pathlib import Path

# === 确保项目根目录在 PYTHONPATH 中 ===
PROJECT_ROOT = Path(__file__).resolve().parents[3]
# core/rag_engine/test -> core/rag_engine -> core -> 项目根
sys.path.insert(0, str(PROJECT_ROOT))

# =========================================================
# Mock：EmbeddingModelManager
# =========================================================

class MockEmbeddingModelManager:
    """
    模拟 embedding 模型管理器
    - encode 接口与真实实现保持一致
    - 使用固定维度向量，避免 768 / 1024 争议
    """
    def __init__(self, dim: int = 8) -> None:
        self.dim = dim

    def encode(self, alias: str, sentences: List[str]):
        vecs = []
        for s in sentences:
            seed = sum(ord(c) for c in s) % 997
            rng = np.random.default_rng(seed)
            v = rng.random(self.dim, dtype=np.float32)
            vecs.append(v)
        return np.stack(vecs, axis=0)


# =========================================================
# Mock：LLMClient
# =========================================================

@dataclass
class MockLLMResponse:
    text: str
    raw: Optional[Dict] = None
    usage: Optional[Dict] = None


class MockLLMClient:
    """
    模拟 LLM：
    - generate：一次性返回完整回答
    - stream：分片返回
    """

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs,
    ) -> MockLLMResponse:
        answer = (
            "系统通过向量检索从知识库中查找相关片段。[1]\n"
            "回答时通过引用编号标注来源，保证可追溯性。[1]"
        )
        return MockLLMResponse(text=answer, raw={"mock": True})

    def stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs,
    ) -> Iterable[str]:
        text = self.generate(messages).text
        for i in range(0, len(text), 15):
            yield text[i:i + 15]


# =========================================================
# 兼容 rag_service 导入路径
# =========================================================

def _import_rag_service():
    try:
        from core.rag_engine.api.rag_service import RAGService, AskConfig
        return RAGService, AskConfig
    except Exception:
        from core.rag_engine.api.rag_service import RAGService, AskConfig
        return RAGService, AskConfig


# =========================================================
# Smoke Test 主体
# =========================================================

def test_rag_service_smoke_end_to_end_with_enhancements():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        # -------------------------------------------------
        # 1) 初始化真实 VectorDBProxy（ChromaDB）
        # -------------------------------------------------
        from core.vector_engine.vector_db_proxy.proxy import create_vector_db_proxy

        proxy = create_vector_db_proxy(
            db_type="chromadb",
            path=tmpdir,
            host="",
            port=0,
            pool_size=2,
            max_overflow=2,
        )
        assert proxy.connect() is True

        collection = "knowledge_base_chunks"

        # -------------------------------------------------
        # 2) 写入两组不同 KB 的测试数据（用于过滤验证）
        # -------------------------------------------------
        emb_manager = MockEmbeddingModelManager(dim=8)

        # ===== KB A（目标知识库）=====
        kb_a = "kb_target"
        docs_a = [
            "向量检索用于在知识库中查找相似内容。",
            "引用机制保证回答来源可追溯。",
        ]
        vecs_a = emb_manager.encode("mock", docs_a).tolist()

        meta_a = [
            {
                "document_id": "doc_a",
                "chunk_index": i,
                "source_info": f"smoke://doc_a#{i}",
                "source_type": "test",
                "knowledge_base_id": kb_a,
                "uploader_id": "tester",
            }
            for i in range(len(docs_a))
        ]

        assert proxy.add_vectors(
            collection_name=collection,
            vectors=vecs_a,
            ids=[f"a_{i}" for i in range(len(docs_a))],
            documents=docs_a,
            metadatas=meta_a,
        )

        # ===== KB B（干扰知识库，不应被召回）=====
        kb_b = "kb_noise"
        docs_b = ["这是另一个知识库的内容，不应被检索到。"]
        vecs_b = emb_manager.encode("mock", docs_b).tolist()

        meta_b = [{
            "document_id": "doc_b",
            "chunk_index": 0,
            "source_info": "smoke://doc_b#0",
            "source_type": "test",
            "knowledge_base_id": kb_b,
            "uploader_id": "tester",
        }]

        assert proxy.add_vectors(
            collection_name=collection,
            vectors=vecs_b,
            ids=["b_0"],
            documents=docs_b,
            metadatas=meta_b,
        )

        # -------------------------------------------------
        # 3) 确保 DEFAULT_TEMPLATES 可被 orchestrator 使用
        # -------------------------------------------------
        import core.rag_engine.prompt_builder as pb
        from core.rag_engine.prompt_builder.templates import DEFAULT_TEMPLATES

        if not hasattr(pb, "DEFAULT_TEMPLATES"):
            pb.DEFAULT_TEMPLATES = DEFAULT_TEMPLATES

        # -------------------------------------------------
        # 4) 初始化 RAGService
        # -------------------------------------------------
        RAGService, AskConfig = _import_rag_service()

        llm = MockLLMClient()
        service = RAGService(
            db_proxy=proxy,
            embedding_model_manager=emb_manager,
            llm_client=llm,
            cfg=AskConfig(collection_name=collection, top_k=3),
        )

        from core.rag_engine.query_understanding.context_state import ConversationState

        state = ConversationState()
        state.user_context.knowledge_base_id = kb_a

        question = "请说明向量检索和引用机制的作用"

        # =================================================
        # 5️⃣ 非流式 ask 测试
        # =================================================
        resp = service.ask(
            question=question,
            model_alias="mock",
            conversation_state=state,
            stream=False,
        )

        assert "answer" in resp
        assert "[1]" in resp["answer"]

        citations = resp["citations"]
        assert len(citations) > 0

        # ✅ 增强点 1：验证只引用了 KB A
        for c in citations:
            assert c["knowledge_base_id"] == kb_a

        # =================================================
        # 6️⃣ 流式 ask 测试（新增）
        # =================================================
        stream_resp = service.ask(
            question=question,
            model_alias="mock",
            conversation_state=state,
            stream=True,
        )

        assert "stream" in stream_resp

        streamed_text = ""
        for chunk in stream_resp["stream"]:
            streamed_text += chunk

        # ✅ 增强点 2：流式输出内容正确
        assert "向量检索" in streamed_text
        assert "[1]" in streamed_text

        # -------------------------------------------------
        # 7) 清理
        # -------------------------------------------------
        proxy.disconnect()


if __name__ == "__main__":
    test_rag_service_smoke_end_to_end_with_enhancements()
    print("✓ RAG smoke test (enhanced) passed.")
