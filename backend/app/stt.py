"""
STT client: wraps MERaLiON audio transcription API.

Usage:
    from app.stt import transcribe_audio
    text = transcribe_audio(audio_bytes, content_type="audio/wav")
"""
from __future__ import annotations

import base64
import os
import httpx

MERALION_API_BASE = "https://api.meralion.ai"
DEFAULT_TIMEOUT = 60.0


def transcribe_audio(
    audio_bytes: bytes,
    content_type: str = "audio/wav",
) -> str:
    """
    Transcribe audio via MERaLiON ASR endpoint.
    Returns the full transcript string.
    Raises RuntimeError on non-2xx or missing MERALION_API_KEY.
    """
    api_key = os.environ.get("MERALION_API_KEY")
    if not api_key:
        raise RuntimeError("MERALION_API_KEY environment variable is not set.")

    audio_b64 = base64.b64encode(audio_bytes).decode()
    audio_url = f"data:{content_type};base64,{audio_b64}"

    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(
            f"{MERALION_API_BASE}/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"audio_url": audio_url},
        )

    if resp.status_code != 200:
        raise RuntimeError(
            f"MERaLiON API error {resp.status_code}: {resp.text[:300]!r}"
            f" | url={resp.url}"
            f" | key_prefix={api_key[:8]}..."
        )

    data = resp.json()
    return data["choices"][0]["message"]["content"]
