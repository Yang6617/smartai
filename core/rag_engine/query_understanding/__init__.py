"""
查询理解模块（Query Understanding）

功能包括：
- 查询意图识别
- 查询重写与规范化
- 多轮对话上下文状态管理
"""

from .intent_classifier import IntentClassifier, QueryIntent, IntentResult
from .query_rewrite import QueryRewriter, RewriteResult
from .context_state import ConversationState, Turn, UserContext

__all__ = [
    "IntentClassifier",
    "QueryIntent",
    "IntentResult",
    "QueryRewriter",
    "RewriteResult",
    "ConversationState",
    "Turn",
    "UserContext",
]
