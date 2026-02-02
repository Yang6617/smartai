from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Optional

from core.vector_engine.embedding_loader.model_manager import EmbeddingModelManager
from core.vector_engine.vector_db_proxy.proxy import VectorDBProxy
from core.rag_engine.orchestrator import RAGOrchestrator
from core.rag_engine.query_understanding.context_state import ConversationState
from core.rag_engine.llm_client.base import ChatMessage, LLMClientBase


@dataclass
class AskConfig:
    """
    ask 接口配置
    """
    # 向量库集合名（你们若统一为单集合可固定 "knowledge_base_chunks"）
    collection_name: str = "knowledge_base_chunks"
    # LLM 采样参数
    temperature: float = 0.2
    max_tokens: int = 1024
    # 向量检索 top_k
    top_k: int = 8


class RAGService:
    """
    对外 RAG 服务接口（可被 API 层直接调用）
    """

    def __init__(
        self,
        db_proxy: VectorDBProxy,
        embedding_model_manager: EmbeddingModelManager,
        llm_client: LLMClientBase,
        cfg: Optional[AskConfig] = None,
    ) -> None:
        self.db_proxy = db_proxy
        self.embedding_model_manager = embedding_model_manager
        self.llm_client = llm_client
        self.cfg = cfg or AskConfig()

        self.orchestrator = RAGOrchestrator(
            db_proxy=db_proxy,
            collection_name=self.cfg.collection_name,
            vector_top_k=self.cfg.top_k,
        )

    def ask(
        self,
        question: str,
        model_alias: str,
        conversation_state: Optional[ConversationState] = None,
        stream: bool = False,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        对外统一 ask 接口

        参数：
        - question：用户问题
        - model_alias：Embedding 模型别名（由调用方提前 load_model 或由服务启动时 load）
        - conversation_state：多轮上下文（可选）
        - stream：是否流式输出

        返回：
        - stream=False：{"answer": "...", "citations": [...], "debug": {...}}
        - stream=True：{"stream": generator, "citations": [...], "debug": {...}}
        """
        conversation_state = conversation_state or ConversationState()
        # 确保 kb_id 能用于过滤（你可以由上层设置）
        kb_id = conversation_state.user_context.knowledge_base_id

        # 添加调试信息
        print(f"[DEBUG] RAG Service - Received question: {question[:50]}...")
        print(f"[DEBUG] RAG Service - Knowledge base ID: {kb_id}")
        print(f"[DEBUG] RAG Service - Knowledge base ID type: {type(kb_id)}")

        # 1) 生成 query embedding
        # encode 返回：np.ndarray 或 List[List[float]]（取决于 SentenceTransformer 参数）
        emb = self.embedding_model_manager.encode(model_alias, [question])
        if emb is None:
            raise RuntimeError(f"模型 {model_alias} 未加载或编码失败")
        query_vec = emb[0].tolist() if hasattr(emb[0], "tolist") else list(emb[0])

        # 2) 连接 DB（也可由外层保持长连接，这里按最稳妥方式）
        if not self.db_proxy.connect():
            raise RuntimeError("向量库连接失败")

        try:
            # 3) 动态确定集合名称（与存储时保持一致）
            # 确保 kb_id 不为 None 或空字符串，否则无法找到正确的集合
            if kb_id is None or kb_id == "":
                raise ValueError("知识库ID不能为空")
            
            # 将kb_id转换为字符串以确保一致性
            kb_id_str = str(kb_id).strip()
            collection_name = f"kb_{kb_id_str}"
            
            print(f"[DEBUG] RAG Service - Using collection name: {collection_name}")
            
            # 创建临时orchestrator实例以使用正确的集合名
            temp_orchestrator = RAGOrchestrator(
                db_proxy=self.db_proxy,
                collection_name=collection_name,
                vector_top_k=self.cfg.top_k,
            )
            
            result = temp_orchestrator.run(
                question=question,
                query_embedding=query_vec,
                conversation_state=conversation_state,
                cfg=self.cfg,
            )
            assembled = result["prompt"]

            citations = assembled.citations

            # 4) 调用 LLM - 检查LLM客户端是否可用
            if self.llm_client is None:
                # 如果LLM客户端不可用，基于检索到的内容生成基础回复
                hits = result.get("hits", [])
                retrieved_texts = []
                for hit in hits:
                    # 确保hit有text属性且不为空
                    if hasattr(hit, 'text') and hit.text:
                        retrieved_texts.append(hit.text)
                
                if retrieved_texts:
                    # 基于检索到的文本片段提供简要总结
                    preview_text = " ".join(retrieved_texts[:3])  # 使用前3个匹配项
                    if len(preview_text) > 200:
                        preview_text = preview_text[:200] + "..."
                    answer = f"找到了相关资料，但语言模型服务暂不可用。\n\n相关摘要: {preview_text}\n\n请稍后重试或联系管理员配置语言模型服务。"
                else:
                    answer = "未找到相关资料，且语言模型服务暂不可用。\n\n请确认知识库中有相关内容，或联系管理员配置语言模型服务。"
                return {
                    "answer": answer,
                    "citations": citations,
                    "debug": {
                        "kb_id": kb_id,
                        "intent": result["intent"].intent.value,
                        "rewrite": result["rewrite"].rewritten,
                        "original_question": question,
                        "expansion": {
                            "expanded_query": result.get("expansion", {}).expanded_query if "expansion" in result else "",
                            "expansion_terms": result.get("expansion", {}).expansion_terms if "expansion" in result else [],
                            "confidence": result.get("expansion", {}).confidence if "expansion" in result else 0.0
                        } if "expansion" in result else {},
                        "hit_count": len(result["hits"]),
                    },
                }

            messages: list[ChatMessage] = [
                {"role": "system", "content": assembled.system_prompt},
                {"role": "user", "content": assembled.user_prompt},
            ]

            if not stream:
                llm_resp = self.llm_client.generate(
                    messages,
                    temperature=self.cfg.temperature,
                    max_tokens=self.cfg.max_tokens,
                )
                return {
                    "answer": llm_resp["text"] if isinstance(llm_resp, dict) else llm_resp.text,
                    "citations": citations,
                    "debug": {
                        "kb_id": kb_id,
                        "intent": result["intent"].intent.value,
                        "rewrite": result["rewrite"].rewritten,
                        "original_question": question,
                        "expansion": {
                            "expanded_query": result.get("expansion", {}).expanded_query if "expansion" in result else "",
                            "expansion_terms": result.get("expansion", {}).expansion_terms if "expansion" in result else [],
                            "confidence": result.get("expansion", {}).confidence if "expansion" in result else 0.0
                        } if "expansion" in result else {},
                        "hit_count": len(result["hits"]),
                    },
                }

            # 流式：返回 generator
            gen = self.llm_client.stream(
                messages,
                temperature=self.cfg.temperature,
                max_tokens=self.cfg.max_tokens,
            )
            return {
                "stream": gen,
                "citations": citations,
                "debug": {
                    "kb_id": kb_id,
                    "intent": result["intent"].intent.value,
                    "rewrite": result["rewrite"].rewritten,
                    "original_question": question,
                    "expansion": {
                        "expanded_query": result.get("expansion", {}).expanded_query if "expansion" in result else "",
                        "expansion_terms": result.get("expansion", {}).expansion_terms if "expansion" in result else [],
                        "confidence": result.get("expansion", {}).confidence if "expansion" in result else 0.0
                    } if "expansion" in result else {},
                    "hit_count": len(result["hits"]),
                },
            }
        finally:
            self.db_proxy.disconnect()
