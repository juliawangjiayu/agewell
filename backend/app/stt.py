"""
STT client: wraps MERaLiON audio transcription API.

Usage:
    from app.stt import transcribe_audio
    text = transcribe_audio(audio_bytes, content_type="audio/wav")
"""
from __future__ import annotations

import base64
import os
import subprocess

import httpx

MERALION_API_BASE = "https://api.meralion.ai"
DEFAULT_TIMEOUT = 60.0


def _to_wav(audio_bytes: bytes, content_type: str) -> bytes:
    """Convert any supported audio format to 16 kHz mono WAV via ffmpeg."""
    fmt = content_type.split("/")[-1].split(";")[0].strip()
    if fmt == "wav":
        return audio_bytes

    # ffmpeg auto-detects input format from content
    proc = subprocess.run(
        [
            "ffmpeg",
            "-i", "pipe:0",          # read from stdin
            "-ar", "16000",          # 16 kHz
            "-ac", "1",              # mono
            "-acodec", "pcm_s16le",  # 16-bit PCM (standard WAV)
            "-f", "wav",             # output format
            "pipe:1",                # write to stdout
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

    wav_bytes = _to_wav(audio_bytes, content_type)
    audio_b64 = base64.b64encode(wav_bytes).decode()
    audio_url = f"data:audio/wav;base64,{audio_b64}"

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
