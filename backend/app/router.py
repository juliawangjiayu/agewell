"""
Router: decide whether an incoming message is from helper or employer,
then call the right orchestrator function.

Detection heuristics (lightweight, no LLM needed):
- If the text contains mostly Latin/Singlish keywords → helper
- If the text is Chinese / explicit role hint → employer
- Explicit role parameter always wins.
"""
from __future__ import annotations

from app.orchestrator import (
    process_helper_observation,
    process_employer_instruction,
    HelperResult,
    EmployerResult,
    LLMCallable,
)

HELPER_SIGNALS = [
    "ah ma", "ma'am", "madam", "lah", "leh", "lor", "sia", "cannot",
    "she say", "she feel", "she got", "today", "eat", "dizzy", "fever",
    "no mood", "small small",
]
EMPLOYER_SIGNALS_CN = [
    "我们", "过来", "吃饭", "记得", "药", "准备", "妈妈", "你", "帮",
    "买菜", "煮", "今晚", "早点",
]


def detect_role(text: str) -> str:
    """
    Return 'helper' or 'employer' based on content heuristics.
    Falls back to 'helper' when ambiguous.
    """
    lower = text.lower()
    helper_score = sum(1 for kw in HELPER_SIGNALS if kw in lower)
    employer_score = sum(1 for kw in EMPLOYER_SIGNALS_CN if kw in text)
    return "employer" if employer_score > helper_score else "helper"


def route(
    text: str,
    profiles: dict,
    skill_on: bool = True,
    role: str | None = None,   # explicit override: "helper" | "employer"
    llm: LLMCallable | None = None,
    pending_question: str | None = None,
) -> HelperResult | EmployerResult:
    """
    Route a message to the correct orchestrator.

    Args:
        text: raw message text
        profiles: family context dict
        skill_on: whether to use skill prompts
        role: explicit role override; if None, auto-detect
        llm: optional LLM callable (for testing)

    Returns:
        HelperResult or EmployerResult
    """
    resolved_role = role if role in ("helper", "employer") else detect_role(text)

    if resolved_role == "employer":
        return process_employer_instruction(
            raw_instruction=text,
            profiles=profiles,
            skill_on=skill_on,
            llm=llm,
        )
    else:
        return process_helper_observation(
            raw_text=text,
            profiles=profiles,
            skill_on=skill_on,
            llm=llm,
            pending_question=pending_question,
        )
