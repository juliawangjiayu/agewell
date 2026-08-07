"""
STT client: wraps OpenAI Whisper API.

Usage:
    from app.stt import transcribe_audio
    text = transcribe_audio(audio_bytes, content_type="audio/webm")
"""
from __future__ import annotations

import io
import os
import subprocess

import httpx

OPENAI_API_BASE = "https://api.openai.com/v1"
DEFAULT_TIMEOUT = 60.0


def _to_wav(audio_bytes: bytes, content_type: str) -> bytes:
    """Convert any supported audio format to 16 kHz mono WAV via ffmpeg."""
    fmt = content_type.split("/")[-1].split(";")[0].strip()
    if fmt == "wav":
        return audio_bytes

    proc = subprocess.run(
        [
            "ffmpeg",
            "-i", "pipe:0",
            "-ar", "16000",
            "-ac", "1",
            "-acodec", "pcm_s16le",
            "-f", "wav",
            "pipe:1",
        ],
        input=audio_bytes,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {proc.returncode}): {proc.stderr.decode()[:500]}"
        )
    return proc.stdout


def transcribe_audio(
    audio_bytes: bytes,
    content_type: str = "audio/webm",
) -> str:
    """
    Transcribe audio via OpenAI Whisper API.
    Returns the full transcript string.
    Raises RuntimeError on non-2xx or missing OPENAI_API_KEY.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    wav_bytes = _to_wav(audio_bytes, content_type)

    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(
            f"{OPENAI_API_BASE}/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("audio.wav", io.BytesIO(wav_bytes), "audio/wav")},
            data={"model": "whisper-1", "language": "zh"},
        )

    if resp.status_code != 200:
        raise RuntimeError(
            f"OpenAI API error {resp.status_code}: {resp.text[:300]!r}"
        )

    data = resp.json()
    return data.get("text", "")
