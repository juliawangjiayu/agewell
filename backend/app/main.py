"""
FastAPI application: all HTTP endpoints.

Endpoints:
    POST /families/{slug}/onboard          - create/update family profiles
    GET  /families/{slug}/profiles         - get profiles + recent observations
    POST /families/{slug}/message          - send helper or employer message
    POST /families/{slug}/audio            - upload audio → STT → message
    GET  /families/{slug}/observations     - list recent observations
    POST /families/{slug}/reset            - clear observations, re-seed demo data
    GET  /healthz                          - health check
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Literal

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import repository as repo
from app.db import apply_schema, get_connection
from app.orchestrator import EmployerResult, HelperResult
from app.router import route

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Apply DB schema + seed demo data on startup (both idempotent)."""
    try:
        apply_schema()
        print("[startup] Schema applied.")
    except Exception as e:
        print(f"[startup] Schema apply failed: {e}")
    try:
        from app.seed import seed
        seed(skip_if_exists=True)
        print("[startup] Seed complete.")
    except Exception as e:
        print(f"[startup] Seed failed: {e}")
    yield


_STARTED_AT = datetime.now(timezone.utc).isoformat()

app = FastAPI(title="AgeWell 照护协同 API", version="0.1.0", lifespan=lifespan)

_CORS_ORIGINS = [
    "https://agewell-xi.vercel.app",
    "https://agewell.vercel.app",
    # 本地开发
    "http://localhost:5173",
    "http://localhost:3000",
]
# 支持通过环境变量追加额外 origin（如 Vercel preview URLs）
_extra = os.getenv("CORS_ORIGINS", "")
if _extra:
    _CORS_ORIGINS += [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ElderIn(BaseModel):
    name: str
    age: int | None = None
    conditions: list[str] = []
    baseline_notes: str | None = None
    medications: list[dict] = []
    followups: dict = {}
    last_med_change_date: str | None = None   # ISO date string
    # 结构化调药记录 {drug, from, to, date}。缺了这个字段，Pydantic 会把它丢掉，
    # 医生端就只能写「具体药物不详」。
    last_med_change: dict = {}


class EmployerIn(BaseModel):
    name: str
    language: str = "zh"
    relation: str | None = None
    work_schedule: str | None = None
    notes: str | None = None


class CaregiverIn(BaseModel):
    name: str
    home_country: str | None = None
    mother_tongue: str | None = None
    care_abilities: str | None = None


class OnboardRequest(BaseModel):
    elder: ElderIn
    employer: EmployerIn
    caregiver: CaregiverIn


class MessageRequest(BaseModel):
    text: str
    skill_on: bool = True
    role: Literal["helper", "employer", "auto"] = "auto"
    # 上一轮 agent 提出的澄清问题；本轮 text 是对它的回答。
    pending_question: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_family_or_404(conn, slug: str) -> dict:
    fam = repo.get_family_by_slug(conn, slug)
    if not fam:
        raise HTTPException(status_code=404, detail=f"Family '{slug}' not found.")
    return fam


def _get_llm():
    if os.environ.get("USE_MOCK") == "1":
        from app.mocks import mock_chat_completion
        return mock_chat_completion
    from app.llm import chat_completion
    return chat_completion


def _get_stt():
    if os.environ.get("USE_MOCK") == "1":
        from app.mocks import mock_transcribe_audio
        return mock_transcribe_audio
    from app.stt import transcribe_audio
    return transcribe_audio


def _build_profiles_with_obs(conn, family_id: int) -> dict:
    profiles = repo.get_profiles(conn, family_id)
    profiles["recent_observations"] = repo.get_recent_observations(conn, family_id, limit=10)
    # 女佣汇报时要能对上雇主交代过的任务，否则「确认闭环」只是前后脚发两条消息
    profiles["recent_tasks"] = repo.get_recent_task_breakdowns(conn, family_id, limit=2)
    return profiles


def _result_to_dict(result: HelperResult | EmployerResult) -> dict:
    if isinstance(result, HelperResult):
        return {
            "type": "helper",
            "skill_on": result.skill_on,
            "raw_text": result.raw_text,
            "restored_text": result.restored_text,
            "grade": result.grade,
            "notify": result.notify,
            "reason": result.reason,
            "clarifying_questions": result.clarifying_questions,
            "task_confirmations": result.task_confirmations,
            "outputs": result.outputs,
        }
    else:
        return {
            "type": "employer",
            "skill_on": result.skill_on,
            "raw_instruction": result.raw_instruction,
            "understood": result.understood,
            "conflicts": result.conflicts,
            "tasks": result.tasks,
            "helper_message": result.helper_message,
            "confirmation_items": result.confirmation_items,
        }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/healthz")
def healthz():
    """线上跑的到底是哪个 commit —— 部署链路排查全靠这个。"""
    return {
        "status": "ok",
        "version": (
            os.getenv("RAILWAY_GIT_COMMIT_SHA")
            or os.getenv("GIT_COMMIT_SHA")
            or "dev"
        )[:7],
        "started_at": _STARTED_AT,
    }


@app.post("/families/{slug}/onboard", status_code=201)
def onboard(slug: str, body: OnboardRequest) -> dict[str, Any]:
    """Create or update a family with all three profiles."""
    with get_connection() as conn:
        fam = repo.get_or_create_family(conn, slug)
        fid = fam["id"]
        employer = repo.upsert_employer_profile(conn, fid, body.employer.model_dump())
        elder = repo.upsert_elder_profile(conn, fid, body.elder.model_dump())
        caregiver = repo.upsert_caregiver_profile(conn, fid, body.caregiver.model_dump())
    return {
        "family_id": fid,
        "slug": slug,
        "employer": employer,
        "elder": elder,
        "caregiver": caregiver,
    }


@app.get("/families/{slug}/profiles")
def get_profiles(slug: str) -> dict[str, Any]:
    with get_connection() as conn:
        fam = _get_family_or_404(conn, slug)
        profiles = _build_profiles_with_obs(conn, fam["id"])
    return {"slug": slug, **profiles}


@app.post("/families/{slug}/message")
def send_message(slug: str, body: MessageRequest) -> dict[str, Any]:
    """Process a helper or employer text message."""
    with get_connection() as conn:
        fam = _get_family_or_404(conn, slug)
        fid = fam["id"]
        profiles = _build_profiles_with_obs(conn, fid)

        role = body.role if body.role != "auto" else None
        result = route(
            text=body.text,
            profiles=profiles,
            skill_on=body.skill_on,
            role=role,
            llm=_get_llm(),
            pending_question=body.pending_question,
        )

        # Persist to DB
        if isinstance(result, HelperResult):
            # 还在等澄清回答的半成品判断不落库，否则会污染后续轮次的上下文。
            if result.clarifying_questions and result.grade == "record":
                return _result_to_dict(result)
            repo.save_observation(conn, fid, {
                "raw_text": result.raw_text,
                "restored_text": result.restored_text,
                "grade": result.grade,
                "notify": result.notify,
                "reason": result.reason,
                "outputs": result.outputs,
                "skill_on": result.skill_on,
            })
        else:
            repo.save_task_breakdown(conn, fid, {
                "raw_instruction": result.raw_instruction,
                "understood": result.understood,
                "tasks": result.tasks,
                "helper_message": result.helper_message,
                "confirmation_items": result.confirmation_items,
                "skill_on": result.skill_on,
            })

    return _result_to_dict(result)


@app.post("/families/{slug}/audio")
async def send_audio(
    slug: str,
    file: UploadFile = File(...),
    skill_on: bool = Query(True),
    role: str = Query("auto"),
) -> dict[str, Any]:
    """Upload audio → STT → same pipeline as /message."""
    audio_bytes = await file.read()
    content_type = file.content_type or "audio/wav"
    print(f"[DEBUG] Audio received: {len(audio_bytes)} bytes, content_type={content_type}")
    stt = _get_stt()
    text = stt(audio_bytes, content_type)

    with get_connection() as conn:
        fam = _get_family_or_404(conn, slug)
        fid = fam["id"]
        profiles = _build_profiles_with_obs(conn, fid)

        resolved_role = role if role != "auto" else None
        result = route(
            text=text,
            profiles=profiles,
            skill_on=skill_on,
            role=resolved_role,
            llm=_get_llm(),
        )

        if isinstance(result, HelperResult):
            repo.save_observation(conn, fid, {
                "raw_text": result.raw_text,
                "restored_text": result.restored_text,
                "grade": result.grade,
                "notify": result.notify,
                "reason": result.reason,
                "outputs": result.outputs,
                "skill_on": result.skill_on,
            })
        else:
            repo.save_task_breakdown(conn, fid, {
                "raw_instruction": result.raw_instruction,
                "understood": result.understood,
                "tasks": result.tasks,
                "helper_message": result.helper_message,
                "confirmation_items": result.confirmation_items,
                "skill_on": result.skill_on,
            })

    response = _result_to_dict(result)
    response["transcript"] = text
    return response


@app.get("/families/{slug}/observations")
def list_observations(
    slug: str,
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    with get_connection() as conn:
        fam = _get_family_or_404(conn, slug)
        obs = repo.get_recent_observations(conn, fam["id"], limit=limit)
    return {"slug": slug, "observations": obs}


@app.post("/families/{slug}/reset")
def reset_family(slug: str) -> dict[str, Any]:
    """
    Reset the demo family back to seed state.

    「重置到种子状态」要名副其实：既清观察/任务记录，也把三张 profile 重新写回
    种子值。此前只重置了观察——启动时的 seed 是 skip_if_exists，一旦家庭已存在
    就跳过，profile 便永远停留在第一次播种的数据上（调药记录为空、复诊日期过期）。
    """
    with get_connection() as conn:
        fam = _get_family_or_404(conn, slug)
        deleted = repo.reset_family_observations(conn, fam["id"])
    # Re-seed if this is the demo family
    if slug == "ah-ma":
        try:
            from app.seed import CAREGIVER, ELDER, EMPLOYER, SEED_OBSERVATIONS
            import copy
            with get_connection() as conn:
                fam = repo.get_family_by_slug(conn, slug)
                fid = fam["id"]
                # profile 也回到种子值，否则调药记录/复诊日期会一直是旧的
                repo.upsert_employer_profile(conn, fid, copy.deepcopy(EMPLOYER))
                repo.upsert_elder_profile(conn, fid, copy.deepcopy(ELDER))
                repo.upsert_caregiver_profile(conn, fid, copy.deepcopy(CAREGIVER))
                for obs in copy.deepcopy(SEED_OBSERVATIONS):
                    offset = obs.pop("observed_at_offset", None)
                    saved = repo.save_observation(conn, fid, obs)
                    if offset:
                        conn.execute(
                            "UPDATE observations SET observed_at = %s WHERE id = %s",
                            (offset, saved["id"]),
                        )
                        conn.commit()
        except Exception as e:
            print(f"[reset] Re-seed failed: {e}")
    return {"ok": True, "deleted": deleted, "slug": slug}
