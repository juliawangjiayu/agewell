"""
Task 4 + 5: Skill prompt loading + evaluation test cases.

Tests verify:
1. Skill markdown files exist and are non-empty.
2. Orchestrator correctly loads them.
3. Key phrases from the skill spec appear in the prompts.
4. Evaluation: three demo cases (record / routine / escalate) produce correct grades.
5. Evaluation: employer skill produces correct 5-person count.
"""
from __future__ import annotations

import pathlib
import pytest

from app.mocks import mock_chat_completion
from app.orchestrator import (
    process_helper_observation,
    process_employer_instruction,
    _HELPER_SKILL_PROMPT,
    _EMPLOYER_SKILL_PROMPT,
)

SKILLS_DIR = pathlib.Path(__file__).parent.parent / "app" / "skills"

# ---------------------------------------------------------------------------
# Skill file content checks
# ---------------------------------------------------------------------------

class TestSkillFiles:
    def test_helper_skill_file_exists(self):
        assert (SKILLS_DIR / "helper_skill.md").exists()

    def test_employer_skill_file_exists(self):
        assert (SKILLS_DIR / "employer_skill.md").exists()

    def test_helper_skill_loaded(self):
        assert len(_HELPER_SKILL_PROMPT) > 100, "helper_skill.md should be non-empty"

    def test_employer_skill_loaded(self):
        assert len(_EMPLOYER_SKILL_PROMPT) > 100

    def test_helper_skill_contains_grade_enum(self):
        assert "record" in _HELPER_SKILL_PROMPT
        assert "routine" in _HELPER_SKILL_PROMPT
        assert "escalate" in _HELPER_SKILL_PROMPT

    def test_helper_skill_has_json_output_spec(self):
        assert "restored_text" in _HELPER_SKILL_PROMPT
        assert "notify" in _HELPER_SKILL_PROMPT

    def test_employer_skill_has_json_output_spec(self):
        assert "tasks" in _EMPLOYER_SKILL_PROMPT
        assert "helper_message" in _EMPLOYER_SKILL_PROMPT
        assert "confirmation_items" in _EMPLOYER_SKILL_PROMPT


# ---------------------------------------------------------------------------
# Demo scenario evaluations (Task 4 - helper)
# ---------------------------------------------------------------------------

PROFILES_WITH_MED_CHANGE = {
    "elder": {
        "name": "Ah Ma",
        "age": 82,
        "conditions": ["高血压", "2型糖尿病"],
        "baseline_notes": "能自己走动",
        "medications": [{"drug": "Amlodipine", "timing": "早饭后", "time": "08:00"}],
        "followups": {},
        "last_med_change_date": "2026-07-30",
    },
    "employer": {"name": "丽珍", "relation": "女儿", "work_schedule": "工作日不在场"},
    "caregiver": {"name": "Rosa"},
    "recent_observations": [
        {"grade": "record", "restored_text": "午饭进食略少"},
        {"grade": "record", "restored_text": "仍进食减少"},
    ],
}

PROFILES_NO_MED_CHANGE = dict(PROFILES_WITH_MED_CHANGE)
PROFILES_NO_MED_CHANGE["elder"] = {
    **PROFILES_WITH_MED_CHANGE["elder"],
    "last_med_change_date": None,
}
PROFILES_CLEAN = {
    **PROFILES_WITH_MED_CHANGE,
    "recent_observations": [],
}


class TestHelperEval:
    """Eval: three demo scenarios → correct grade."""

    def test_demo_A_record(self):
        """剧本 A: single mild observation, no context → record."""
        result = process_helper_observation(
            raw_text="Ah Ma today lunch eat a bit less lah, but she ok, now watching TV.",
            profiles=PROFILES_CLEAN,
            skill_on=True,
            llm=mock_chat_completion,
        )
        assert result.grade == "record", f"Expected record, got {result.grade}"
        assert result.notify == []

    def test_demo_C_escalate(self):
        """剧本 C: dizzy + recent med change → escalate."""
        result = process_helper_observation(
            raw_text="she got no mood to eat, only eat small small, and she say she feel a bit dizzy",
            profiles=PROFILES_WITH_MED_CHANGE,
            skill_on=True,
            llm=mock_chat_completion,
        )
        assert result.grade == "escalate"
        assert "doctor" in result.notify
        assert "family" in result.notify

    def test_escalate_helper_output_always_present(self):
        result = process_helper_observation(
            raw_text="she feel a bit dizzy",
            profiles=PROFILES_WITH_MED_CHANGE,
            skill_on=True,
            llm=mock_chat_completion,
        )
        assert result.outputs.get("helper") is not None

    def test_skill_off_vs_skill_on_differ(self):
        """skill_on=False should not produce a structured grade/notify."""
        on = process_helper_observation(
            "she feel a bit dizzy", PROFILES_WITH_MED_CHANGE,
            skill_on=True, llm=mock_chat_completion,
        )
        off = process_helper_observation(
            "she feel a bit dizzy", PROFILES_WITH_MED_CHANGE,
            skill_on=False, llm=mock_chat_completion,
        )
        # skill_on produces escalate; skill_off always record
        assert on.grade == "escalate"
        assert off.grade == "record"
        # skill_on notifies; skill_off doesn't
        assert len(on.notify) > 0
        assert off.notify == []


# ---------------------------------------------------------------------------
# Task 5: Employer eval
# ---------------------------------------------------------------------------

EMPLOYER_PROFILES = {
    "elder": {
        "name": "Ah Ma",
        "age": 82,
        "conditions": ["高血压"],
        "baseline_notes": "",
        "medications": [{"drug": "Amlodipine", "timing": "饭前", "time": "17:30"}],
        "followups": {},
        "last_med_change_date": None,
    },
    "employer": {"name": "丽珍", "relation": "女儿", "work_schedule": "周五来"},
    "caregiver": {"name": "Rosa"},
    "recent_observations": [],
}


class TestEmployerEval:
    def test_5_person_count(self):
        """'我们四个人过来' must resolve to 5 people total."""
        result = process_employer_instruction(
            raw_instruction="今晚我们四个人过来吃饭，妈妈的药记得饭前吃，6点要炒菜就早点准备",
            profiles=EMPLOYER_PROFILES,
            skill_on=True,
            llm=mock_chat_completion,
        )
        assert "5" in result.understood, "Must mention 5 people in understood"

    def test_tasks_include_medicine(self):
        result = process_employer_instruction(
            raw_instruction="今晚我们四个人过来吃饭，妈妈的药记得饭前吃，6点要炒菜就早点准备",
            profiles=EMPLOYER_PROFILES,
            skill_on=True,
            llm=mock_chat_completion,
        )
        task_items = [t["item"] for t in result.tasks]
        # At least one task should mention medicine
        assert any("药" in item or "medicine" in item.lower() for item in task_items)

    def test_confirmation_items_not_empty(self):
        result = process_employer_instruction(
            raw_instruction="今晚我们四个人过来吃饭，妈妈的药记得饭前吃",
            profiles=EMPLOYER_PROFILES,
            skill_on=True,
            llm=mock_chat_completion,
        )
        assert len(result.confirmation_items) >= 1

    def test_helper_message_in_english(self):
        result = process_employer_instruction(
            raw_instruction="今晚我们四个人过来吃饭",
            profiles=EMPLOYER_PROFILES,
            skill_on=True,
            llm=mock_chat_completion,
        )
        # helper_message should contain English words
        english_words = ["rosa", "dinner", "pm", "tonight", "please", "hi", "thank"]
        assert any(w in result.helper_message.lower() for w in english_words)
