from __future__ import annotations

from typing import Any, Dict, Optional

from core.rag_engine.query_understanding import (
    IntentClassifier,
    QueryRewriter,
    ConversationState,
)
from core.rag_engine.retrieval import (
    VectorRetriever,
    VectorRetrieverConfig,
    RetrievalFilter,
    FusionConfig,
    fuse_hits,
    Reranker,
)
from core.rag_engine.prompt_builder import (
    PromptAssembler,
    PromptType,
    DEFAULT_TEMPLATES,
)
from core.vector_engine.vector_db_proxy.proxy import VectorDBProxy

from core.rag_engine.config import RAGConfig
class RAGOrchestrator:
    """
    RAG 推理引擎主编排器

    流程：
    1. 查询理解（意图识别 + 重写）
    2. 向量检索
    3. 结果融合 / 重排
    4. Prompt 组装
    5. 调用 LLM（此处只返回 prompt，方便你接入任意 LLM Client）
    """

    def __init__(
        self,
        db_proxy: VectorDBProxy,
        collection_name: str,
        vector_top_k: int = 8,
        cfg: Optional[RAGConfig] = None,
    ) -> None:
        self.cfg = cfg or RAGConfig(
            collection_name="knowledge_base_chunks",
            vector_top_k=8,
            temperature=0.2,
            max_tokens=1024,
        )
        self.db_proxy = db_proxy
        self.collection_name = collection_name

        self.intent_classifier = IntentClassifier()
        self.query_rewriter = QueryRewriter()
        self.prompt_assembler = PromptAssembler()

        self.vector_retriever = VectorRetriever(
            db_proxy,
            VectorRetrieverConfig(top_k=self.cfg.vector_top_k),
        )

        self.reranker = Reranker()

    def run(
        self,
        question: str,
        query_embedding: list[float],
        conversation_state: Optional[ConversationState] = None,
        cfg: Optional[RAGConfig] = None,
    ) -> Dict[str, Any]:
        """
        执行一次 RAG 推理（不直接调用 LLM）
        """
        cfg = cfg or self.cfg
        conversation_state = conversation_state or ConversationState()
        conversation_state.add_user_message(question)

        # 1️⃣ 意图识别
        intent_result = self.intent_classifier.classify(question)

        # 2️⃣ 查询重写
        rewrite_result = self.query_rewriter.rewrite(
            question,
            hints={
                "knowledge_base_id": conversation_state.user_context.knowledge_base_id
            },
        )

        # 3️⃣ 构建检索过滤条件
        rf = RetrievalFilter(
            knowledge_base_id=conversation_state.user_context.knowledge_base_id
        )

        # 4️⃣ 向量检索
        vector_hits = self.vector_retriever.retrieve(
            collection_name=self.collection_name,
            query_embedding=query_embedding,
            rf=rf,
        )

        # 5️⃣ 重排（可选）
        final_hits = self.reranker.rerank(
            rewrite_result.rewritten,
            vector_hits,
        )

        # 6️⃣ 选择 Prompt 模板
        try:
            prompt_type = PromptType(intent_result.intent.value)
        except Exception:
            prompt_type = PromptType.DEFAULT

        template = DEFAULT_TEMPLATES.get(prompt_type, DEFAULT_TEMPLATES[PromptType.DEFAULT])

        # 7️⃣ 组装 Prompt
        assembled = self.prompt_assembler.assemble(
            template=template,
            question=rewrite_result.rewritten,
            hits=final_hits,
        )

        return {
            "intent": intent_result,
            "rewrite": rewrite_result,
            "prompt": assembled,
            "hits": final_hits,
        }
