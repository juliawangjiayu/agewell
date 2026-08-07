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


app = FastAPI(title="AgeWell 照护协同 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
            "outputs": result.outputs,
        }
    else:
        return {
            "type": "employer",
            "skill_on": result.skill_on,
            "raw_instruction": result.raw_instruction,
            "understood": result.understood,
            "tasks": result.tasks,
            "helper_message": result.helper_message,
            "confirmation_items": result.confirmation_items,
        }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/healthz")
def healthz():
    return {"status": "ok"}


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
        )

        # Persist to DB
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
    """Clear all observations and task_breakdowns; re-seed seed observations."""
    with get_connection() as conn:
        fam = _get_family_or_404(conn, slug)
        deleted = repo.reset_family_observations(conn, fam["id"])
    # Re-seed if this is the demo family
    if slug == "ah-ma":
        try:
            from app.seed import SEED_OBSERVATIONS
            import copy
            with get_connection() as conn:
                fam = repo.get_family_by_slug(conn, slug)
                fid = fam["id"]
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
