from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from .base import ChatMessage, LLMResponse, LLMClientBase


@dataclass
class FallbackConfig:
    """
    降级策略配置
    """
    # 若 LLM 调用失败，是否返回“仅引用资料的保底答案”
    return_context_only_on_fail: bool = True
    # 保底文本最大长度
    max_chars: int = 1200


class FallbackClient:
    """
    LLM Client 包装器：失败时降级

    - primary：主 LLM 客户端（DeepSeekClient）
    - fallback_text_supplier：可选，提供保底文本（例如：检索片段拼接）
    """

    def __init__(
        self,
        primary: LLMClientBase,
        cfg: Optional[FallbackConfig] = None,
        fallback_text_supplier=None,
    ) -> None:
        self.primary = primary
        self.cfg = cfg or FallbackConfig()
        self.fallback_text_supplier = fallback_text_supplier

    def generate(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        try:
            return self.primary.generate(messages, **kwargs)
        except Exception as e:
            if not self.cfg.return_context_only_on_fail:
                raise

            text = self._fallback_text(str(e))
            return LLMResponse(text=text, raw={"error": str(e)}, usage=None)

    def stream(self, messages: List[ChatMessage], **kwargs) -> Iterable[str]:
        try:
            for chunk in self.primary.stream(messages, **kwargs):
                yield chunk
        except Exception as e:
            if not self.cfg.return_context_only_on_fail:
                yield f"\n[LLM_ERROR] {str(e)}\n"
                return
            yield self._fallback_text(str(e))

    def _fallback_text(self, err_msg: str) -> str:
        base = "LLM 调用失败，已降级返回检索资料片段。\n"
        base += f"错误信息：{err_msg}\n\n"
        extra = ""
        if self.fallback_text_supplier:
            try:
                extra = str(self.fallback_text_supplier())
            except Exception:
                extra = ""
        text = (base + extra).strip()
        return text[: self.cfg.max_chars]
