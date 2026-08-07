"""
STT client: wraps MERaLiON audio transcription API.

Usage:
    from app.stt import transcribe_audio
    text = transcribe_audio(audio_bytes, content_type="audio/wav")
"""
from __future__ import annotations

import base64
import io
import os
import struct
import subprocess
import tempfile
import wave

import httpx

MERALION_API_BASE = "https://api.meralion.ai"
DEFAULT_TIMEOUT = 60.0


def _decode_to_raw_pcm(audio_bytes: bytes, content_type: str) -> bytes:
    """Decode any audio format to 16-bit 16kHz mono raw PCM using ffmpeg."""
    fmt = content_type.split("/")[-1].split(";")[0].strip()

    if fmt == "wav":
        # Parse WAV to extract raw PCM
        with wave.open(io.BytesIO(audio_bytes), "rb") as w:
            nchannels = w.getnchannels()
            sampwidth = w.getsampwidth()
            framerate = w.getframerate()
            nframes = w.getnframes()
            raw = w.readframes(nframes)
            # If already 16-bit mono 16kHz, return as-is
            if sampwidth == 2 and nchannels == 1 and framerate == 16000:
                return raw
        # Otherwise fall through to ffmpeg for resampling

    # Use ffmpeg to decode to raw PCM s16le 16kHz mono
    with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False) as in_f:
        in_f.write(audio_bytes)
        in_path = in_f.name

    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", in_path,
            "-ar", "16000",
            "-ac", "1",
            "-acodec", "pcm_s16le",
            "-f", "s16le",
            "pipe:1",
        ],
        capture_output=True,
        check=False,
    )
    os.unlink(in_path)

    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {proc.returncode}): {proc.stderr.decode()[:500]}"
        )
    return proc.stdout


def _build_wav(raw_pcm: bytes) -> bytes:
    """Build a minimal valid WAV file from raw 16-bit 16kHz mono PCM data."""
    data_size = len(raw_pcm)
    file_size = 36 + data_size

    header = (
        b"RIFF"
        + struct.pack("<I", file_size)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<I", 16)  # subchunk1 size
        + struct.pack("<H", 1)   # PCM format
        + struct.pack("<H", 1)   # mono
        + struct.pack("<I", 16000)  # sample rate
        + struct.pack("<I", 32000)  # byte rate
        + struct.pack("<H", 2)   # block align
        + struct.pack("<H", 16)  # bits per sample
        + b"data"
        + struct.pack("<I", data_size)
    )
    return header + raw_pcm


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

    raw_pcm = _decode_to_raw_pcm(audio_bytes, content_type)
    wav_bytes = _build_wav(raw_pcm)
    audio_b64 = base64.b64encode(wav_bytes).decode()
    audio_url = f"data:audio/wav;base64,{audio_b64}"

    print(f"[STT DEBUG] raw_pcm={len(raw_pcm)} wav={len(wav_bytes)} b64_prefix={audio_b64[:30]}")

    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = client.post(
            f"{MERALION_API_BASE}/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"audio_url": audio_url},
        )

    print(f"[STT DEBUG] status={resp.status_code} body={resp.text[:200]!r}")

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
