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
        "restored_text": "午饭进食量减少约50%，本周多次；并新出现头晕",
        "clarifying_questions": [],
        "grade": "escalate",
        "notify": ["doctor", "family"],
        "reason": "头晕为新出现，与2天前上调 Amlodipine 时间关联；进食减少在调药之前已存在，属独立趋势",
        "outputs": {
            "family": "妈妈今天午饭吃得少，还说有点头晕。头晕是这两天才有的，周三刚把降压药加量，时间上可能有关系。你方便打个电话问问她；周五复诊时也可以跟医生提一句。",
            "doctor": "82F，高血压 / 2型糖尿病。Amlodipine 5→10mg（2天前）。此后新发头晕。另：进食量减少约50%，起于调药前2天，本周多次，暂无明确解释。无发热、无呕吐。照护者观察，未经临床评估。",
            "helper": "好的 Rosa，你做得对，及时说很重要。接下来这几天帮我留意她起身的时候晕不晕。如果她站不稳或说话不清楚，直接按紧急按钮或打 995。",
            "elder": "这件事我需要告诉你女儿。",
        },
    },
    # helper skill: record path
    "eat a bit less": {
        "restored_text": "午饭进食略少，精神状态如常",
        "clarifying_questions": [],
        "grade": "record",
        "notify": [],
        "reason": "单次轻微波动，无持续性、无用药关联，不构成信号",
        "outputs": {
            "family": None,
            "doctor": None,
            "helper": "好的 Rosa，我记下了，先观察就好，不用担心。",
            "elder": None,
        },
    },
    # helper skill: 任务回执 + 澄清提问（女佣执行完汇报，且话说得太简单）
    "dinner done": {
        "restored_text": "女佣回报晚饭与用药已按交代完成；另提到老人今天状态不佳，未说明是哪一方面",
        "task_confirmations": [
            "晚饭 18:30 已开饭（5人份，与交代一致）",
            "Metformin 已在饭后服用（与交代一致，非饭前）",
        ],
        "clarifying_questions": ["是哪方面不太好——吃饭、走动，还是精神？"],
        "grade": "record",
        "notify": [],
        "reason": "任务已按交代落地；健康描述信息量不足以分级，已提出一条当场可答的问题",
        "outputs": {
            "family": None,
            "doctor": None,
            "helper": "收到 Rosa，今晚的都对上了。方便的话告诉我是哪方面不太好？",
            "elder": None,
        },
    },
    # helper skill: 澄清提问路径（模糊输入 → 先问一句，再定级）
    "not so good": {
        "restored_text": "女佣报告老人今天状态不佳，但未说明是哪一方面",
        "clarifying_questions": ["是哪方面不太好——吃饭、走动，还是精神？"],
        "grade": "record",
        "notify": [],
        "reason": "信息量不足以分级；已提出一条当场可答、且会改变判断的问题",
        "outputs": {
            "family": None,
            "doctor": None,
            "helper": "好的 Rosa，我先记下了。方便的话告诉我是哪方面不太好？",
            "elder": None,
        },
    },
    # employer skill
    "今晚我们四个人": {
        "understood": (
            "今晚Rachel一家4人来 Ah Ma 家吃晚饭，连 Ah Ma 共5人，需备够5人份。"
            "另：指令说「药饭前吃」，但晚饭对应的是 Metformin，"
            "标准建议为随餐或饭后服用，已列入待确认。"
        ),
        "conflicts": [
            {
                "instruction": "妈妈的药记得饭前吃",
                "fact": "晚饭对应的是 Metformin（二甲双胍），标准建议随餐或饭后服用以减少肠胃反应；两种降压药在早饭后，与今晚无关。",
                "question": "你是指晚饭时随餐吃 Metformin 吗？",
            }
        ],
        "tasks": [
            {"item": "去买菜", "time": "16:00", "tell_by": "15:30",
             "detail": "买今晚5人份的菜（4位客人 + Ah Ma）；家里够的话可跳过"},
            {"item": "开始备菜", "time": "17:00", "tell_by": None,
             "detail": "洗切腌好，18:00 要能下锅"},
            {"item": "炒菜", "time": "18:00", "tell_by": "17:00", "detail": "5人份"},
            {"item": "开饭", "time": "18:30", "tell_by": None, "detail": "5人份，摆5副餐具"},
            {"item": "让 Ah Ma 吃降糖药 Metformin", "time": "19:00", "tell_by": None,
             "detail": "饭后吃，不是饭前——按用药表随餐或饭后服用，已在跟Rachel确认"},
        ],
        "helper_message": (
            "Hi Rosa, tonight 4 guests + Ah Ma = 5 people, so please prepare for 5. "
            "By 3:30 PM check the groceries and buy more if not enough. Start prepping at 5 PM, "
            "cook at 6 PM, dinner at 6:30 PM. For Ah Ma's Metformin — please give it WITH dinner "
            "or just after, not before. Ma'am wrote 'before food', I'm checking with her; "
            "for now follow the with-food timing. Thank you!"
        ),
        "confirmation_items": [
            "16:00 去买菜（5人份）",
            "17:00 开始备菜",
            "18:00 炒菜",
            "18:30 开饭",
            "19:00 Ah Ma 吃降糖药 Metformin（饭后，不是饭前）",
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
