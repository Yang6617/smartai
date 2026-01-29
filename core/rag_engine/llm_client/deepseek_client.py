from __future__ import annotations
import os
import requests
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .base import ChatMessage, LLMResponse
from .streaming import iter_sse_lines, extract_openai_delta_text



class DeepSeekClient:
    """
    DeepSeek LLM Client（按 OpenAI 兼容接口组织）

    说明：
    - 采用 urllib（避免强依赖 requests）
    - 同时提供 generate 与 stream
    """

    def __init__(
            self,
            api_key: Optional[str] = None,
            base_url: str = "https://api.deepseek.com",
            model: str = "deepseek-chat",
            timeout: int = 60,
    ):
        # 优先使用显式传入的 api_key，其次使用环境变量
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API Key 未配置（DEEPSEEK_API_KEY）")

        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs,
    ) -> Dict:
        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )

        resp.raise_for_status()
        data = resp.json()

        return {
            "text": data["choices"][0]["message"]["content"],
            "raw": data,
        }

    def stream(
            self,
            messages: List[Dict[str, str]],
            temperature: float = 0.2,
            max_tokens: int = 1024,
            **kwargs,
    ) -> Iterable[str]:
        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with requests.post(
                url,
                json=payload,
                headers=headers,
                stream=True,
                timeout=self.timeout,
        ) as resp:
            resp.raise_for_status()

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue

                # DeepSeek 流式返回与 OpenAI 类似：以 data: 开头
                if line.startswith("data:"):
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue

    def _url(self) -> str:
        base = self.cfg.base_url.rstrip("/")
        ep = self.cfg.endpoint
        if not ep.startswith("/"):
            ep = "/" + ep
        return base + ep

    def _post_json(self, payload: Dict) -> Dict:
        url = self._url()
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.cfg.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout_s) as r:
                raw = r.read().decode("utf-8", errors="ignore")
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
            raise RuntimeError(f"DeepSeek HTTPError {e.code}: {body}")
        except Exception as e:
            raise RuntimeError(f"DeepSeek request failed: {str(e)}")
