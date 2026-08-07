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
import pathlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

# ---------------------------------------------------------------------------
# Skill prompts (loaded from markdown at import time)
# ---------------------------------------------------------------------------

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
    clarifying_questions: list[str] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    raw_llm: str = ""              # full LLM reply for debugging


@dataclass
class EmployerResult:
    raw_instruction: str
    skill_on: bool
    understood: str = ""
    conflicts: list[dict] = field(default_factory=list)
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


_WEEKDAYS = "一二三四五六日"


def _with_weekday(value: Any) -> str:
    """'2026-08-05' → '2026-08-05（周三）'，解析不了就原样返回。"""
    if not value:
        return ""
    text = str(value)[:10]
    try:
        return f"{text}（周{_WEEKDAYS[date.fromisoformat(text).weekday()]}）"
    except (ValueError, IndexError):
        return str(value)


def _as_obj(value: Any, default: Any) -> Any:
    """JSONB 列有时以字符串回来，统一解析。"""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default
    return value if value is not None else default


def _fmt_medications(meds: list) -> str:
    """压成简报，不要把整个 JSON 甩进 prompt（会稀释注意力）。"""
    lines = []
    for m in meds:
        if not isinstance(m, dict):
            continue
        name = m.get("drug") or m.get("name") or "?"
        note = m.get("note") or m.get("notes") or ""
        line = f"  - {name}：{m.get('timing', '')} {m.get('time', '')}".rstrip()
        if note:
            line += f"（{note}）"
        lines.append(line)
    return "\n".join(lines) or "  （无）"


def _fmt_med_change(change: Any, fallback_date: Any) -> str:
    """
    只说改了哪一个药。缺了这一层，模型会把整张用药表都写给医生，
    让人误以为三种药同时调整过。
    """
    change = _as_obj(change, {}) or {}
    if change.get("drug"):
        return (
            f"最近一次调药：{_with_weekday(change.get('date'))} "
            f"{change['drug']} {change.get('from', '?')} → {change.get('to', '?')}"
            f"（只有这一个药有变动，其余维持原方案）"
        )
    if fallback_date:
        return f"最近一次调药：{_with_weekday(fallback_date)}（具体药物不详，不要臆测是哪一个）"
    return "最近一次调药：无记录（不要把任何症状归因到用药调整）"


def _fmt_observations(recent_obs: list) -> list[str]:
    lines = []
    for obs in recent_obs[-5:]:  # show latest 5
        when = _with_weekday(obs.get("observed_at") or obs.get("date") or obs.get("created_at"))
        text = obs.get("restored_text") or obs.get("raw_text", "")
        prefix = f"  - {when} " if when else "  - "
        lines.append(f"{prefix}[{obs.get('grade', '?')}] {text}")
    return lines


def _build_family_context(profiles: dict) -> str:
    """Serialize family profiles into a readable context string for the prompt."""
    elder = profiles.get("elder") or {}
    employer = profiles.get("employer") or {}
    caregiver = profiles.get("caregiver") or {}
    recent_obs = profiles.get("recent_observations") or []

    meds = _as_obj(elder.get("medications"), [])
    followups = _as_obj(elder.get("followups"), {})

    ctx_parts = [
        "=== 家庭上下文 ===",
        f"今天：{_with_weekday(date.today().isoformat())}",
        f"老人：{elder.get('name','未知')}，{elder.get('age','?')}岁",
        f"慢病：{', '.join(elder.get('conditions') or [])}",
        f"基线备注：{elder.get('baseline_notes','无')}",
        "用药表：",
        _fmt_medications(meds),
        f"复诊：{followups.get('clinic','?')}，间隔 {followups.get('interval','?')}，"
        f"下次 {_with_weekday(followups.get('next_date')) or '未定'}",
        _fmt_med_change(elder.get("last_med_change"), elder.get("last_med_change_date")),
        f"主要照护者（雇主）：{employer.get('name','未知')}，关系：{employer.get('relation','?')}",
        f"雇主作息：{employer.get('work_schedule','未知')}",
        f"女佣：{caregiver.get('name','Rosa')}，工作语言：English/Singlish",
    ]

    obs_lines = _fmt_observations(recent_obs)
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
    pending_question: str | None = None,
) -> HelperResult:
    """
    Process a helper's observation text through the orchestrator.

    profiles dict should contain:
        elder, employer, caregiver, recent_observations

    pending_question: 上一轮 agent 提出的澄清问题；本轮输入是对它的回答。
    """
    llm = llm or _get_default_llm()
    result = HelperResult(raw_text=raw_text, skill_on=skill_on)

    context = _build_family_context(profiles)
    if pending_question:
        context += (
            f"\n\n=== 上一轮你问过 ===\n{pending_question}\n"
            "（本轮女佣的话是对这个问题的回答，请结合上一轮的观察一起判断）"
        )
    if skill_on and _HELPER_SKILL_PROMPT:
        system_msg = _HELPER_SKILL_PROMPT
        user_msg = f"{context}\n\n=== 本轮女佣观察 ===\n{raw_text}"
    else:
        system_msg = (
            "你是一个家庭照护助手。女佣发来了对老人的观察，请用中文简洁地回复她，"
            "给出你的看法和建议。"
        )
        user_msg = f"{context}\n\n=== 本轮女佣观察 ===\n{raw_text}"

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
            result.clarifying_questions = parsed.get("clarifying_questions") or []
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

    context = _build_family_context(profiles)
    if skill_on and _EMPLOYER_SKILL_PROMPT:
        system_msg = _EMPLOYER_SKILL_PROMPT
        user_msg = f"{context}\n\n=== 本轮雇主指令 ===\n{raw_instruction}"
    else:
        system_msg = (
            "你是一个家庭照护助手。雇主发来了一条指令，请用中文简洁地复述并给女佣一条操作建议。"
        )
        user_msg = f"{context}\n\n=== 本轮雇主指令 ===\n{raw_instruction}"

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
            result.conflicts = parsed.get("conflicts") or []
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

    Handles ```json ... ``` fences, and falls back to grabbing the outermost
    {...} span when the model prepends prose. 解析失败会导致整轮静默降级成
    record，所以这里要尽量宽容。
    """
    text = (text or "").strip()
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
        pass

    # Fallback: outermost brace span
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None
