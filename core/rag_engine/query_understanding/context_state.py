from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Turn:
    """
    对话中的单轮消息
    """
    role: str            # user / assistant / system
    content: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class UserContext:
    """
    用户级上下文信息（请求维度）
    """
    user_id: Optional[str] = None
    knowledge_base_id: Optional[str] = None
    locale: str = "zh"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """
    多轮对话状态管理

    功能：
    - 维护最近 N 轮对话
    - 构造检索/重写用的上下文提示
    - 可序列化存储（Redis / DB）
    """
    max_turns: int = 20
    turns: List[Turn] = field(default_factory=list)
    user_context: UserContext = field(default_factory=UserContext)

    def add_user_message(self, content: str) -> None:
        self._append(Turn(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        self._append(Turn(role="assistant", content=content))

    def add_system_message(self, content: str) -> None:
        self._append(Turn(role="system", content=content))

    def _append(self, turn: Turn) -> None:
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns :]

    def last_user_query(self) -> Optional[str]:
        """
        获取最近一条用户问题
        """
        for t in reversed(self.turns):
            if t.role == "user" and t.content.strip():
                return t.content.strip()
        return None

    def build_context_hint(self, max_chars: int = 800) -> str:
        """
        构造用于检索/重写的上下文摘要（非最终 prompt）
        """
        parts = []
        if self.user_context.knowledge_base_id:
            parts.append(f"[kb={self.user_context.knowledge_base_id}]")

        for t in self.turns[-6:]:
            prefix = "U" if t.role == "user" else "A"
            parts.append(f"{prefix}: {t.content[:160]}")

        hint = "\n".join(parts)
        return hint[-max_chars:]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_turns": self.max_turns,
            "turns": [asdict(t) for t in self.turns],
            "user_context": asdict(self.user_context),
        }
