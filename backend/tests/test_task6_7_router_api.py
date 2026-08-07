"""
Task 6 + 7: Router and FastAPI endpoint tests.
Uses TestClient (no real DB, no real API).
"""
from __future__ import annotations

import json
import os
import pytest

# Patch env before importing app
os.environ.setdefault("USE_MOCK", "1")
os.environ.setdefault("DATABASE_URL", "postgresql://fake")

from app.router import detect_role, route
from app.orchestrator import HelperResult, EmployerResult
from app.mocks import mock_chat_completion

# ---------------------------------------------------------------------------
# Task 6: Router unit tests
# ---------------------------------------------------------------------------

class TestDetectRole:
    def test_singlish_is_helper(self):
        assert detect_role("Ah Ma today no mood to eat lah") == "helper"

    def test_chinese_instruction_is_employer(self):
        assert detect_role("今晚我们四个人过来吃饭，妈妈的药记得饭前吃") == "employer"

    def test_explicit_role_helper(self):
        result = route(
            "今晚我们四个人过来吃饭",
            profiles=_fake_profiles(),
            skill_on=True,
            role="helper",
            llm=mock_chat_completion,
        )
        assert isinstance(result, HelperResult)

    def test_explicit_role_employer(self):
        result = route(
            "Ah Ma today feel dizzy",
            profiles=_fake_profiles(),
            skill_on=True,
            role="employer",
            llm=mock_chat_completion,
        )
        assert isinstance(result, EmployerResult)

    def test_auto_routes_singlish_to_helper(self):
        result = route(
            "she feel a bit dizzy and eat small small",
            profiles=_fake_profiles(),
            skill_on=True,
            role=None,
            llm=mock_chat_completion,
        )
        assert isinstance(result, HelperResult)

    def test_auto_routes_chinese_to_employer(self):
        result = route(
            "今晚我们四个人过来吃饭，妈妈的药记得饭前吃",
            profiles=_fake_profiles(),
            skill_on=True,
            role=None,
            llm=mock_chat_completion,
        )
        assert isinstance(result, EmployerResult)


# ---------------------------------------------------------------------------
# Task 7: FastAPI endpoint tests (no real DB)
# ---------------------------------------------------------------------------

# We mock the DB layer so tests can run without a live Postgres
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=True)


def _fake_profiles():
    return {
        "elder": {
            "name": "Ah Ma", "age": 82,
            "conditions": ["高血压"],
            "baseline_notes": "",
            "medications": [],
            "followups": {},
            "last_med_change_date": "2026-07-30",
        },
        "employer": {"name": "丽珍", "relation": "女儿", "work_schedule": "工作日不在场"},
        "caregiver": {"name": "Rosa"},
        "recent_observations": [],
    }


def _mock_conn_ctx():
    """Return a MagicMock that acts as a psycopg3 context manager."""
    conn = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, conn


class TestHealthEndpoint:
    def test_healthz(self):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestMessageEndpoint:
    def _call_message(self, text: str, role: str = "auto", skill_on: bool = True):
        ctx, conn = _mock_conn_ctx()
        conn.execute.return_value.fetchone.return_value = {"id": 1, "slug": "ah-ma"}

        with patch("app.main.get_connection", return_value=ctx), \
             patch("app.main.repo.get_family_by_slug", return_value={"id": 1, "slug": "ah-ma"}), \
             patch("app.main.repo.get_profiles", return_value=_fake_profiles()), \
             patch("app.main.repo.get_recent_observations", return_value=[]), \
             patch("app.main.repo.save_observation", return_value={}), \
             patch("app.main.repo.save_task_breakdown", return_value={}), \
             patch("app.main._get_llm", return_value=mock_chat_completion):
            resp = client.post(
                "/families/ah-ma/message",
                json={"text": text, "role": role, "skill_on": skill_on},
            )
        return resp

    def test_helper_message_returns_grade(self):
        resp = self._call_message(
            "she feel a bit dizzy", role="helper", skill_on=True
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "helper"
        assert "grade" in data
        assert data["grade"] == "escalate"

    def test_employer_message_returns_tasks(self):
        resp = self._call_message(
            "今晚我们四个人过来吃饭，妈妈的药记得饭前吃",
            role="employer", skill_on=True
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "employer"
        assert "tasks" in data
        assert len(data["tasks"]) >= 1

    def test_skill_off_still_returns_200(self):
        resp = self._call_message(
            "she feel a bit dizzy", role="helper", skill_on=False
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill_on"] is False

    def test_404_for_unknown_family(self):
        with patch("app.main.get_connection", return_value=_mock_conn_ctx()[0]), \
             patch("app.main.repo.get_family_by_slug", return_value=None):
            resp = client.post(
                "/families/nonexistent/message",
                json={"text": "hi", "role": "auto", "skill_on": True},
            )
        assert resp.status_code == 404
