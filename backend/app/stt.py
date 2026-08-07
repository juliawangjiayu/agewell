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
import tempfile

import httpx

MERALION_API_BASE = "https://api.meralion.ai"
DEFAULT_TIMEOUT = 60.0


def _to_wav(audio_bytes: bytes, content_type: str) -> bytes:
    """Convert any supported audio format to 16 kHz mono WAV via ffmpeg."""
    fmt = content_type.split("/")[-1].split(";")[0].strip()
    if fmt == "wav":
        return audio_bytes

    # Write input to temp file, convert to temp output file
    # (ffmpeg pipe output may lack complete WAV header)
    with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False) as in_f:
        in_f.write(audio_bytes)
        in_path = in_f.name

    out_path = in_path.replace(f".{fmt}", "_out.wav")

    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", in_path,
            "-ar", "16000",
            "-ac", "1",
            "-acodec", "pcm_s16le",
            out_path,
        ],
        capture_output=True,
        check=False,
    )

    os.unlink(in_path)

    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {proc.returncode}): {proc.stderr.decode()[:500]}"
        )

    with open(out_path, "rb") as f:
        result = f.read()
    os.unlink(out_path)
    return result


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
        # Try both endpoints; MERaLiON docs are inconsistent
        for endpoint in ["/v1/audio/transcriptions", "/audio/transcription"]:
            resp = client.post(
                f"{MERALION_API_BASE}{endpoint}",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"audio_url": audio_url},
            )
            if resp.status_code != 404:
                break

    if resp.status_code != 200:
        raise RuntimeError(
            f"MERaLiON API error {resp.status_code}: {resp.text[:300]!r}"
            f" | url={resp.url}"
            f" | key_prefix={api_key[:8]}..."
            f" | audio_size={len(wav_bytes)}"
            f" | audio_b64_prefix={audio_b64[:50]}..."
        )

    data = resp.json()
    return data["choices"][0]["message"]["content"]
