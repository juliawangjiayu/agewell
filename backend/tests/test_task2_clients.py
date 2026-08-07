"""
Task 2 tests: LLM + STT client contracts and mock correctness.
No real API calls; uses mocks.
"""
from __future__ import annotations

import json
import pytest

from app.mocks import mock_chat_completion, mock_transcribe_audio


# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------

class TestMockLLM:
    def _call(self, user_content: str) -> str:
        return mock_chat_completion(
            [{"role": "user", "content": user_content}]
        )

    def test_escalate_path_returns_valid_json(self):
        raw = self._call("she feel a bit dizzy")
        data = json.loads(raw)
        assert data["grade"] == "escalate"
        assert "doctor" in data["notify"]
        assert "family" in data["notify"]

    def test_escalate_has_all_output_keys(self):
        raw = self._call("feel a bit dizzy")
        data = json.loads(raw)
        outputs = data["outputs"]
        assert set(outputs.keys()) == {"family", "doctor", "helper"}
        assert outputs["helper"] is not None

    def test_record_path_returns_valid_json(self):
        raw = self._call("Ah Ma eat a bit less lah")
        data = json.loads(raw)
        assert data["grade"] == "record"
        assert data["notify"] == []
        assert data["outputs"]["family"] is None
        assert data["outputs"]["doctor"] is None

    def test_employer_skill_path(self):
        raw = self._call("今晚我们四个人过来吃饭")
        data = json.loads(raw)
        assert "understood" in data
        assert "tasks" in data
        assert "helper_message" in data
        assert "confirmation_items" in data
        # Must account for 5 people, not 4
        assert "5" in data["understood"]

    def test_unknown_input_returns_plain_text(self):
        raw = self._call("completely unrelated input xyz")
        # Should NOT be valid JSON (plain text no-skill response)
        try:
            json.loads(raw)
            is_json = True
        except json.JSONDecodeError:
            is_json = False
        assert not is_json


# ---------------------------------------------------------------------------
# Mock STT
# ---------------------------------------------------------------------------

class TestMockSTT:
    def test_returns_string(self):
        result = mock_transcribe_audio(b"fake_audio_bytes")
        assert isinstance(result, str)
        assert len(result) > 10

    def test_contains_dizzy(self):
        result = mock_transcribe_audio(b"any bytes")
        assert "dizzy" in result.lower()


# ---------------------------------------------------------------------------
# LLM module contract (no real API needed)
# ---------------------------------------------------------------------------

def test_llm_module_raises_without_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from app.llm import chat_completion
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        chat_completion([{"role": "user", "content": "hi"}])


def test_stt_module_raises_without_key(monkeypatch):
    monkeypatch.delenv("MERALION_API_KEY", raising=False)
    from app.stt import transcribe_audio
    with pytest.raises(RuntimeError, match="MERALION_API_KEY"):
        transcribe_audio(b"bytes")
