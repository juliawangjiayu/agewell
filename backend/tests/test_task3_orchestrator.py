"""
Task 3 tests: Orchestrator with mock LLM.
No DB, no real API.
"""
from __future__ import annotations

import json
import pytest

from app.mocks import mock_chat_completion
from app.orchestrator import (
    process_helper_observation,
    process_employer_instruction,
    _parse_json_reply,
    HelperResult,
    EmployerResult,
)

# Minimal fake profiles (no DB needed)
FAKE_PROFILES = {
    "elder": {
        "name": "Ah Ma",
        "age": 82,
        "conditions": ["高血压", "2型糖尿病"],
        "baseline_notes": "能自己走动，晚饭后爱看电视",
        "medications": [
            {"drug": "Amlodipine", "timing": "早饭后", "time": "08:00"},
        ],
        "followups": {"last_date": "Day3"},
        "last_med_change_date": "2026-07-30",
    },
    "employer": {
        "name": "Rachel",
        "relation": "女儿",
        "work_schedule": "工作日不在场，周五晚接老人吃饭",
    },
    "caregiver": {
        "name": "Rosa",
        "mother_tongue": "Tagalog",
    },
    "recent_observations": [
        {"grade": "record", "restored_text": "午饭进食略少"},
        {"grade": "record", "restored_text": "仍进食减少"},
    ],
}


class TestHelperObservation:
    def test_escalate_skill_on(self):
        result = process_helper_observation(
            raw_text="she got no mood to eat and she feel a bit dizzy",
            profiles=FAKE_PROFILES,
            skill_on=True,
            llm=mock_chat_completion,
        )
        assert isinstance(result, HelperResult)
        assert result.skill_on is True
        assert result.grade == "escalate"
        assert "doctor" in result.notify
        assert "family" in result.notify
        assert result.outputs.get("helper") is not None

    def test_record_skill_on(self):
        result = process_helper_observation(
            raw_text="Ah Ma eat a bit less lah",
            profiles=FAKE_PROFILES,
            skill_on=True,
            llm=mock_chat_completion,
        )
        assert result.grade == "record"
        assert result.notify == []
        assert result.outputs.get("family") is None

    def test_skill_off_returns_plain_text(self):
        result = process_helper_observation(
            raw_text="she got no mood to eat and she feel a bit dizzy",
            profiles=FAKE_PROFILES,
            skill_on=False,
            llm=mock_chat_completion,
        )
        assert result.skill_on is False
        # In no-skill mode, grade is always "record"
        assert result.grade == "record"
        # outputs.helper should have something
        assert result.outputs.get("helper")


class TestEmployerInstruction:
    def test_skill_on_parses_tasks(self):
        result = process_employer_instruction(
            raw_instruction="今晚我们四个人过来吃饭，妈妈的药记得饭前吃",
            profiles=FAKE_PROFILES,
            skill_on=True,
            llm=mock_chat_completion,
        )
        assert isinstance(result, EmployerResult)
        assert result.skill_on is True
        assert len(result.tasks) >= 1
        assert result.helper_message != ""
        assert len(result.confirmation_items) >= 1
        # Must mention 5 people
        assert "5" in result.understood

    def test_skill_off_returns_plain_text(self):
        result = process_employer_instruction(
            raw_instruction="今晚我们四个人过来吃饭",
            profiles=FAKE_PROFILES,
            skill_on=False,
            llm=mock_chat_completion,
        )
        assert result.skill_on is False
        assert result.helper_message != ""
        assert result.tasks == []  # no structured tasks in no-skill mode


class TestParseJsonReply:
    def test_plain_json(self):
        raw = json.dumps({"grade": "record", "notify": []})
        result = _parse_json_reply(raw)
        assert result["grade"] == "record"

    def test_fenced_json(self):
        raw = "```json\n{\"grade\": \"escalate\"}\n```"
        result = _parse_json_reply(raw)
        assert result["grade"] == "escalate"

    def test_invalid_json_returns_none(self):
        result = _parse_json_reply("this is not json at all")
        assert result is None

    def test_empty_string_returns_none(self):
        result = _parse_json_reply("")
        assert result is None
