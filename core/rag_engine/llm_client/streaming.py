from __future__ import annotations

import json
from typing import Iterable, Iterator, Optional


def iter_sse_lines(byte_iter: Iterable[bytes]) -> Iterator[str]:
    """
    解析最常见的 SSE（Server-Sent Events）行
    - 输入：requests/urllib 的 bytes 迭代器
    - 输出：去掉前缀 "data:" 的纯文本行
    """
    buffer = b""
    for chunk in byte_iter:
        if not chunk:
            continue
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            line_str = line.decode("utf-8", errors="ignore").strip()
            if not line_str:
                continue
            # 常见：data: {...}
            if line_str.startswith("data:"):
                yield line_str[len("data:"):].strip()
            else:
                yield line_str


def extract_openai_delta_text(event_data: str) -> Optional[str]:
    """
    从 OpenAI 兼容流式事件中提取 delta 文本（尽量宽容）
    """
    if event_data.strip() == "[DONE]":
        return None
    try:
        obj = json.loads(event_data)
    except Exception:
        return None

    # 兼容 OpenAI Chat Completions streaming：
    # {"choices":[{"delta":{"content":"..."},"finish_reason":null}]}
    try:
        choices = obj.get("choices") or []
        if not choices:
            return None
        delta = choices[0].get("delta") or {}
        txt = delta.get("content")
        if txt:
            return str(txt)
    except Exception:
        return None

    return None
