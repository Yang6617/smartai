from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Protocol, TypedDict


class ChatMessage(TypedDict):
    """
    Chat 消息结构（兼容 OpenAI 风格）
    """
    role: str          # system / user / assistant
    content: str


@dataclass
class LLMResponse:
    """
    LLM 返回结果（非流式）
    """
    text: str
    raw: Optional[Dict] = None
    usage: Optional[Dict] = None


class LLMClientBase(Protocol):
    """
    LLM Client 抽象接口（建议所有实现对齐）
    """

    def generate(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs,
    ) -> LLMResponse:
        """
        非流式生成
        """
        ...

    def stream(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs,
    ) -> Iterable[str]:
        """
        流式输出：yield 文本增量片段
        """
        ...
