"""
LLM client: wraps DeepSeek Chat API (OpenAI-compatible).

Usage:
    from app.llm import chat_completion
    reply = chat_completion(messages=[{"role":"user","content":"hi"}])
"""
from __future__ import annotations

import os
import json
import httpx
from typing import Any

DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT = 60.0


def chat_completion(
    messages: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> str:
    """
    Call DeepSeek chat completions. Returns the assistant's text content.
    Raises RuntimeError on non-2xx or missing DEEPSEEK_API_KEY.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY environment variable is not set.")

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(
            f"{DEEPSEEK_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            content=json.dumps(payload, ensure_ascii=False).encode(),
        )

    if resp.status_code != 200:
        raise RuntimeError(
            f"DeepSeek API error {resp.status_code}: {resp.text[:300]}"
        )

    data = resp.json()
    return data["choices"][0]["message"]["content"]
