"""
LLM Client 模块

提供：
- 抽象接口 LLMClientBase
- DeepSeekClient（OpenAI兼容接口风格）
- FallbackClient（失败降级）
- 流式输出辅助
"""

from .base import LLMClientBase, LLMResponse, ChatMessage
from .deepseek_client import DeepSeekClient, DeepSeekClient
from .fallback import FallbackClient, FallbackConfig

__all__ = [
    "LLMClientBase",
    "LLMResponse",
    "ChatMessage",
    "DeepSeekClient",
    "FallbackClient",
    "FallbackConfig",
]
