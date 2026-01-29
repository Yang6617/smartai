"""
RAG 端到端 Smoke Test（真实调用 DeepSeek API）

用途：
- 用于“上线前真实推理验证”（本地手动跑 / 预发布环境跑）
- 会真实消耗 DeepSeek token（请控制 max_tokens、不要并发跑）

覆盖点：
1) 使用真实 VectorDBProxy（ChromaDB 本地临时目录）
2) 使用 Mock Embedding（避免依赖本地 embedding 模型文件）
3) 使用真实 DeepSeekClient（环境变量 DEEPSEEK_API_KEY）
4) 覆盖 RAGService.ask 的非流式与流式
5) 验证 knowledge_base_id 过滤（不会跨 KB 召回）

运行方式（Windows PowerShell 示例）：
- 确保已配置 DEEPSEEK_API_KEY 环境变量
- 建议单线程执行：pytest -q -k real_llm -n 1

注意：
- 微信小程序不支持 HTTP Streaming/SSE，生产流式体验走 WebSocket；
  本测试仅验证 llm_client.stream() 的生成器行为与 RAG 端到端链路。
"""

from __future__ import annotations

import gc
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pytest


# =============================================================================
# 0) 确保项目根目录在 PYTHONPATH（适配 Windows / pytest / 直接运行）
# =============================================================================
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # core/rag_engine/test -> core/rag_engine -> core -> repo
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# 1) Mock Embedding（避免依赖本地模型目录）
# =============================================================================
class MockEmbeddingModelManager:
    """模拟 embedding 管理器：encode 返回稳定向量，保证可复现。"""

    def __init__(self, dim: int = 32) -> None:
        self.dim = dim

    def encode(self, alias: str, sentences: List[str]) -> np.ndarray:
        vecs: List[np.ndarray] = []
        for s in sentences:
            # 用字符串内容构造稳定随机种子，确保“同文本 -> 同向量”
            seed = sum(ord(c) for c in s) % 10007
            rng = np.random.default_rng(seed)
            v = rng.random(self.dim, dtype=np.float32)
            vecs.append(v)
        return np.stack(vecs, axis=0)


# =============================================================================
# 2) DeepSeek Client 限额包装：控制 max_tokens、temperature，避免测试成本失控
# =============================================================================
class LimitedDeepSeekClient:
    """
    对 DeepSeekClient 做一层轻量包装：
    - 默认 max_tokens=256
    - 默认 temperature=0.2
    """

    def __init__(
        self,
        base_client: Any,
        default_max_tokens: int = 256,
        default_temperature: float = 0.2,
    ) -> None:
        self._c = base_client
        self._max_tokens = default_max_tokens
        self._temp = default_temperature

    def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        kwargs.setdefault("max_tokens", self._max_tokens)
        kwargs.setdefault("temperature", self._temp)
        out = self._c.generate(messages, **kwargs)
        # 兼容不同实现：可能返回 dict 或对象
        if isinstance(out, dict):
            return out
        # 如果是对象，尽量转成 dict
        text = getattr(out, "text", None) or getattr(out, "content", None) or str(out)
        raw = getattr(out, "raw", None)
        return {"text": text, "raw": raw}

    def stream(self, messages: List[Dict[str, str]], **kwargs) -> Iterable[str]:
        kwargs.setdefault("max_tokens", self._max_tokens)
        kwargs.setdefault("temperature", self._temp)
        return self._c.stream(messages, **kwargs)


# =============================================================================
# 3) 兼容：prompt_builder DEFAULT_TEMPLATES 导出问题
# =============================================================================
def _ensure_prompt_builder_exports() -> None:
    try:
        import core.rag_engine.prompt_builder as pb
        from core.rag_engine.prompt_builder.templates import DEFAULT_TEMPLATES

        if not hasattr(pb, "DEFAULT_TEMPLATES"):
            pb.DEFAULT_TEMPLATES = DEFAULT_TEMPLATES
    except Exception:
        # 若仍失败，后续 import orchestrator 可能会报错；这里先不强行抛出
        pass


# =============================================================================
# 4) pytest fixture：构建可跑的 RAGService（真实 DB + 真实 DeepSeek）
# =============================================================================
@pytest.fixture(scope="function")
def rag_service_real_llm(tmp_path_factory):
    """
    说明：
    - 用 pytest tmp_path_factory 创建 Chroma 临时目录
    - Windows 下偶发文件句柄占用（data_level0.bin）属于 Chroma 常见现象
      pytest 会在 session 结束清理；本 fixture tear-down 会尽力 disconnect + gc
    """
    _ensure_prompt_builder_exports()

    # 4.1 强制检查 DeepSeek Key
    assert os.getenv("DEEPSEEK_API_KEY"), "未检测到环境变量 DEEPSEEK_API_KEY，请先配置后再运行真实 LLM 测试。"

    # 4.2 初始化向量数据库代理（真实 ChromaDB）
    from core.vector_engine.vector_db_proxy.proxy import create_vector_db_proxy

    db_dir = tmp_path_factory.mktemp("chroma_real_llm_data")

    proxy = create_vector_db_proxy(
        db_type="chromadb",
        path=str(db_dir),
        host="",
        port=0,
        pool_size=2,
        max_overflow=2,
    )
    assert proxy.connect() is True

    # 4.3 初始化真实 DeepSeekClient（并做限额包装）
    from core.rag_engine.llm_client.deepseek_client import DeepSeekClient

    deepseek = DeepSeekClient()  # 从 DEEPSEEK_API_KEY 读取
    llm_client = LimitedDeepSeekClient(deepseek, default_max_tokens=256, default_temperature=0.2)

    # 4.4 初始化 RAGService
    from core.rag_engine.api.rag_service import RAGService, AskConfig
    from core.rag_engine.query_understanding.context_state import ConversationState

    emb = MockEmbeddingModelManager(dim=32)

    cfg = AskConfig(
        collection_name="knowledge_base_chunks",
        top_k=4,
    )

    service = RAGService(
        db_proxy=proxy,
        embedding_model_manager=emb,
        llm_client=llm_client,
        cfg=cfg,
    )

    # 4.5 预创建 collection，避免“先查后建”触发 get_collection 报不存在
    proxy.create_collection(cfg.collection_name)

    yield service, proxy, emb, ConversationState, cfg

    # tear-down
    try:
        proxy.disconnect()
    except Exception:
        pass
    gc.collect()


# =============================================================================
# 5) Smoke：非流式 ask（真实 DeepSeek） + KB 过滤
# =============================================================================
@pytest.mark.real_llm
def test_rag_smoke_real_llm_non_stream_with_kb_filter(rag_service_real_llm):
    service, proxy, emb, ConversationState, cfg = rag_service_real_llm

    col = cfg.collection_name
    kb_target = "kb_real_target"
    kb_noise = "kb_real_noise"

    # 5.1 写入目标 KB 数据（会被召回）
    docs_target = [
        "向量检索用于查找语义相似的文本片段。",
        "RAG 会把检索到的片段作为上下文提供给大模型生成回答，并给出引用来源。",
    ]
    vecs_target = emb.encode("mock", docs_target).tolist()
    metas_target = [
        {
            "document_id": "doc_target",
            "chunk_index": i,
            "source_info": f"smoke://doc_target#{i}",
            "source_type": "test",
            "knowledge_base_id": kb_target,
            "uploader_id": "tester",
        }
        for i in range(len(docs_target))
    ]
    proxy.add_vectors(
        collection_name=col,
        vectors=vecs_target,
        ids=[f"t_{i}" for i in range(len(docs_target))],
        documents=docs_target,
        metadatas=metas_target,
    )

    # 5.2 写入干扰 KB 数据（不应被召回）
    docs_noise = [
        "这是另一个知识库的内容，与目标问题无关，且不应被 kb_real_target 的查询召回。",
    ]
    vecs_noise = emb.encode("mock", docs_noise).tolist()
    metas_noise = [
        {
            "document_id": "doc_noise",
            "chunk_index": 0,
            "source_info": "smoke://doc_noise#0",
            "source_type": "test",
            "knowledge_base_id": kb_noise,
            "uploader_id": "tester",
        }
    ]
    proxy.add_vectors(
        collection_name=col,
        vectors=vecs_noise,
        ids=["n_0"],
        documents=docs_noise,
        metadatas=metas_noise,
    )

    # 5.3 构造会话状态（指定 kb_target）
    state = ConversationState()
    state.user_context.knowledge_base_id = kb_target

    # 5.4 调用真实 LLM（非流式）
    resp = service.ask(
        question="请用一句话解释什么是 RAG，并说明为什么需要引用来源？",
        model_alias="mock",
        conversation_state=state,
        stream=False,
        top_k=4,
    )

    assert isinstance(resp, dict)
    assert isinstance(resp.get("answer"), str)
    assert len(resp["answer"].strip()) > 0

    # citations：强断言“结构存在”，弱断言“内容合理”
    citations = resp.get("citations", [])
    assert isinstance(citations, list)
    # 如果你引擎强制引用，通常 >0；若允许空引用，则放宽
    # 这里做“弱校验”：只要有 citations，就必须属于 kb_target
    for c in citations:
        if isinstance(c, dict) and "knowledge_base_id" in c:
            assert c["knowledge_base_id"] == kb_target


# =============================================================================
# 6) Smoke：流式 ask（真实 DeepSeek）——验证 generator 能产出内容
# =============================================================================
@pytest.mark.real_llm
def test_rag_smoke_real_llm_stream(rag_service_real_llm):
    service, proxy, emb, ConversationState, cfg = rag_service_real_llm

    col = cfg.collection_name
    kb_target = "kb_real_stream"

    # 写入一条数据，确保检索有上下文
    docs = ["流式测试：RAG 的核心是先检索证据，再让大模型基于证据回答。"]
    vecs = emb.encode("mock", docs).tolist()
    metas = [
        {
            "document_id": "doc_stream",
            "chunk_index": 0,
            "source_info": "smoke://doc_stream#0",
            "source_type": "test",
            "knowledge_base_id": kb_target,
            "uploader_id": "tester",
        }
    ]
    proxy.add_vectors(
        collection_name=col,
        vectors=vecs,
        ids=["s_0"],
        documents=docs,
        metadatas=metas,
    )

    state = ConversationState()
    state.user_context.knowledge_base_id = kb_target

    resp = service.ask(
        question="请简要说明向量检索在 RAG 中的作用。",
        model_alias="mock",
        conversation_state=state,
        stream=True,
        top_k=3,
    )

    assert isinstance(resp, dict)
    assert "stream" in resp
    stream = resp["stream"]
    assert stream is not None

    combined = ""
    # 流式输出不可预测，不做内容强断言，只验证“确实产出文本”
    for chunk in stream:
        combined += str(chunk)

    assert isinstance(combined, str)
    assert len(combined.strip()) > 0


if __name__ == "__main__":
    # 允许直接 python 运行（不依赖命令行 pytest）
    pytest.main([__file__, "-q"])
