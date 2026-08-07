"""
Orchestrator: composes family context + skill prompt → LLM → parsed result.

Two entry points:
    process_helper_observation(...)  → HelperResult
    process_employer_instruction(...)→ EmployerResult

skill_on=True  → full skill prompt (structured JSON output).
skill_on=False → generic assistant prompt (no-skill / baseline mode).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Skill prompts (loaded from markdown at import time)
# ---------------------------------------------------------------------------

import pathlib

_SKILLS_DIR = pathlib.Path(__file__).parent / "skills"


def _load_skill(filename: str) -> str:
    path = _SKILLS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


_HELPER_SKILL_PROMPT: str = _load_skill("helper_skill.md")
_EMPLOYER_SKILL_PROMPT: str = _load_skill("employer_skill.md")

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class HelperResult:
    raw_text: str
    skill_on: bool
    restored_text: str = ""
    grade: str = "record"          # record | routine | escalate
    notify: list[str] = field(default_factory=list)
    reason: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)
    raw_llm: str = ""              # full LLM reply for debugging


@dataclass
class EmployerResult:
    raw_instruction: str
    skill_on: bool
    understood: str = ""
    tasks: list[dict] = field(default_factory=list)
    helper_message: str = ""
    confirmation_items: list[str] = field(default_factory=list)
    raw_llm: str = ""


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

# The LLM callable is injected so tests can substitute a mock.
LLMCallable = Callable[[list[dict]], str]


def _get_default_llm() -> LLMCallable:
    if os.environ.get("USE_MOCK") == "1":
        from app.mocks import mock_chat_completion
        return mock_chat_completion
    from app.llm import chat_completion
    return chat_completion


def _build_family_context(profiles: dict) -> str:
    """Serialize family profiles into a readable context string for the prompt."""
    elder = profiles.get("elder") or {}
    employer = profiles.get("employer") or {}
    caregiver = profiles.get("caregiver") or {}
    recent_obs = profiles.get("recent_observations") or []

    meds = elder.get("medications", [])
    if isinstance(meds, str):
        try:
            meds = json.loads(meds)
        except Exception:
            meds = []

    followups = elder.get("followups", {})
    if isinstance(followups, str):
        try:
            followups = json.loads(followups)
        except Exception:
            followups = {}

    obs_lines = []
    for obs in recent_obs[-5:]:  # show latest 5
        obs_lines.append(
            f"  - [{obs.get('grade','?')}] {obs.get('restored_text') or obs.get('raw_text','')}"
        )

    ctx_parts = [
        f"=== 家庭上下文 ===",
        f"老人：{elder.get('name','未知')}，{elder.get('age','?')}岁",
        f"慢病：{', '.join(elder.get('conditions') or [])}",
        f"基线备注：{elder.get('baseline_notes','无')}",
        f"用药表：{json.dumps(meds, ensure_ascii=False)}",
        f"复诊信息：{json.dumps(followups, ensure_ascii=False)}",
        f"最近调药日期（last_med_change_date）：{elder.get('last_med_change_date') or '无'}",
        f"主要照护者（雇主）：{employer.get('name','未知')}，关系：{employer.get('relation','?')}",
        f"雇主作息：{employer.get('work_schedule','未知')}",
        f"女佣：{caregiver.get('name','Rosa')}，工作语言：English/Singlish",
    ]
    if obs_lines:
        ctx_parts.append("近期观察记录（最新在后）：")
        ctx_parts.extend(obs_lines)

    return "\n".join(ctx_parts)


# ---------------------------------------------------------------------------
# Helper observation
# ---------------------------------------------------------------------------

def process_helper_observation(
    raw_text: str,
    profiles: dict,
    skill_on: bool = True,
    llm: LLMCallable | None = None,
) -> HelperResult:
    """
    Process a helper's observation text through the orchestrator.

    profiles dict should contain:
        elder, employer, caregiver, recent_observations
    """
    llm = llm or _get_default_llm()
    result = HelperResult(raw_text=raw_text, skill_on=skill_on)

    if skill_on and _HELPER_SKILL_PROMPT:
        context = _build_family_context(profiles)
        system_msg = _HELPER_SKILL_PROMPT
        user_msg = f"{context}\n\n=== 本轮女佣观察 ===\n{raw_text}"
    else:
        system_msg = (
            "你是一个家庭照护助手。女佣发来了对老人的观察，请用中文简洁地回复她，"
            "给出你的看法和建议。"
        )
        user_msg = raw_text

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    raw_llm = llm(messages)
    result.raw_llm = raw_llm

    if skill_on:
        parsed = _parse_json_reply(raw_llm)
        if parsed:
            result.restored_text = parsed.get("restored_text", "")
            result.grade = parsed.get("grade", "record")
            result.notify = parsed.get("notify", [])
            result.reason = parsed.get("reason", "")
            result.outputs = parsed.get("outputs", {})
        else:
            # JSON parse failed: safe fallback
            result.grade = "record"
            result.reason = "JSON parse error; treating as record"
            result.outputs = {"helper": raw_llm, "family": None, "doctor": None}
    else:
        # No-skill mode: treat LLM reply as plain helper message
        result.grade = "record"
        result.outputs = {"helper": raw_llm, "family": None, "doctor": None}

    return result


# ---------------------------------------------------------------------------
# Employer instruction
# ---------------------------------------------------------------------------

def process_employer_instruction(
    raw_instruction: str,
    profiles: dict,
    skill_on: bool = True,
    llm: LLMCallable | None = None,
) -> EmployerResult:
    """
    Process an employer's Chinese instruction through the orchestrator.
    """
    llm = llm or _get_default_llm()
    result = EmployerResult(raw_instruction=raw_instruction, skill_on=skill_on)

    if skill_on and _EMPLOYER_SKILL_PROMPT:
        context = _build_family_context(profiles)
        system_msg = _EMPLOYER_SKILL_PROMPT
        user_msg = f"{context}\n\n=== 本轮雇主指令 ===\n{raw_instruction}"
    else:
        system_msg = (
            "你是一个家庭照护助手。雇主发来了一条指令，请用中文简洁地复述并给女佣一条操作建议。"
        )
        user_msg = raw_instruction

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    raw_llm = llm(messages)
    result.raw_llm = raw_llm

    if skill_on:
        parsed = _parse_json_reply(raw_llm)
        if parsed:
            result.understood = parsed.get("understood", "")
            result.tasks = parsed.get("tasks", [])
            result.helper_message = parsed.get("helper_message", "")
            result.confirmation_items = parsed.get("confirmation_items", [])
        else:
            result.understood = "JSON parse error"
            result.helper_message = raw_llm
    else:
        result.helper_message = raw_llm

    return result


# ---------------------------------------------------------------------------
# JSON parse helper
# ---------------------------------------------------------------------------

def _parse_json_reply(text: str) -> dict | None:
    """
    Try to extract JSON from LLM reply.
    Handles cases where the model wraps JSON in ```json ... ``` fences.
    """
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        inner = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        )
        text = inner.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
