"""
Mock implementations for LLM and STT clients.

Used in tests (and optionally in local dev) to avoid hitting real APIs.

Set environment variable USE_MOCK=1 to activate mocks project-wide.
"""
from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# LLM mock
# ---------------------------------------------------------------------------

# Canned responses keyed by a substring in the last user message content.
_LLM_FIXTURES: dict[str, dict] = {
    # helper skill: escalate path
    "dizzy": {
        "restored_text": "午饭进食量减少约50%，本周第3次，并主诉头晕",
        "grade": "escalate",
        "notify": ["doctor", "family"],
        "reason": "头晕与3天前上调降压药时间关联，食欲下降+头晕症状组合",
        "outputs": {
            "family": "妈妈今天午饭吃得少，还说有点头晕，周三刚加了降压药可能有关系。今晚可以打个电话问问她。",
            "doctor": "患者女性82岁，高血压/2型糖尿病。Day3上调Amlodipine 5→10mg。此后本周3次进食量减少约50%，Day5主诉头晕。照护者观察，未经临床评估。",
            "helper": "好的 Rosa，你做得对，我记下了。接下来留意她还晕不晕，如果站不稳马上告诉我。",
        },
    },
    # helper skill: record path
    "eat a bit less": {
        "restored_text": "午饭进食略少，精神状态如常",
        "grade": "record",
        "notify": [],
        "reason": "单次轻微波动，无持续性、无用药关联，不构成信号",
        "outputs": {
            "family": None,
            "doctor": None,
            "helper": "好的 Rosa，我记下了，先观察就好，不用担心。",
        },
    },
    # employer skill
    "今晚我们四个人": {
        "understood": "今晚丽珍一家4人来Ah Ma家吃晚饭，连Ah Ma共5人，需备够5人的菜；Ah Ma降压药饭前吃；18:00炒菜、18:30前开饭，需提前买菜备菜",
        "tasks": [
            {"item": "去买菜", "time": "16:00", "detail": "买今晚5人份的菜（4位客人+Ah Ma）"},
            {"item": "开始备菜", "time": None, "detail": "洗菜切菜，18:00要能下锅炒"},
            {"item": "让 Ah Ma 吃降压药", "time": "17:30", "detail": "饭前吃"},
            {"item": "开饭", "time": "18:30", "detail": "18:00炒菜，18:30前5人开饭"},
        ],
        "helper_message": "Hi Rosa, for tonight (4 guests + Ah Ma = 5 people): (1) ~4 PM buy groceries for 5; (2) prep food, ready to cook by 6 PM; (3) 5:30 PM give Ah Ma her blood pressure medicine; (4) dinner by 6:30 PM. Thank you!",
        "confirmation_items": [
            "16:00 去买菜（5人份）",
            "备菜（洗切，时间灵活）",
            "17:30 Ah Ma 吃药（饭前）",
            "18:30 前开饭",
        ],
    },
}

_NO_SKILL_FIXTURE = "好的，我已经注意到了。"


def mock_chat_completion(messages: list[dict], **kwargs) -> str:
    """Return a canned JSON fixture based on the last user message."""
    last = messages[-1]["content"] if messages else ""
    for keyword, fixture in _LLM_FIXTURES.items():
        if keyword.lower() in last.lower():
            return json.dumps(fixture, ensure_ascii=False)
    # Default: plain text reply (no-skill mode)
    return _NO_SKILL_FIXTURE


# ---------------------------------------------------------------------------
# STT mock
# ---------------------------------------------------------------------------

def mock_transcribe_audio(audio_bytes: bytes, content_type: str = "audio/wav") -> str:
    """Return a fixed Singlish transcription for any audio bytes."""
    return "Ma'am, Ah Ma today no mood to eat, lunch eat small small only half bowl… and she say she feel a bit dizzy."
