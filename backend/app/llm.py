"""
LLM client: wraps DeepSeek Chat API (OpenAI-compatible).

Usage:
    from app.llm import chat_completion
    reply = chat_completion(messages=[{"role":"user","content":"hi"}])
"""
from __future__ import annotations

import os
import json
import time
import httpx
from typing import Any

DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT = 60.0
# 雇主端一轮输出（understood + conflicts + tasks + helper_message）会超过 1024，
# 截断后 JSON 解析失败 → 整轮静默降级。留足余量。
DEFAULT_MAX_TOKENS = 4096
RETRY_BACKOFF_SECONDS = 1.0


def chat_completion(
    messages: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    attempts: int = 2,
) -> str:
    """
    Call DeepSeek chat completions. Returns the assistant's text content.
    Raises RuntimeError on non-2xx or missing DEEPSEEK_API_KEY.

    Retries once on transient failures — a single API hiccup during a live
    demo otherwise surfaces as a red error banner.
    """
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return _chat_completion_once(messages, model, temperature, max_tokens)
        except Exception as exc:  # noqa: BLE001 - retry any transport/API error
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(RETRY_BACKOFF_SECONDS)
    raise last_error  # type: ignore[misc]


def _chat_completion_once(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
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
