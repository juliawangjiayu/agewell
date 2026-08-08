"""
Task 8: End-to-end pipeline smoke test (mocked DB + LLM).

Demo flow:
  1. Helper escalate → grade=escalate, notify doctor+family
  2. Employer task breakdown → tasks + 5-person count
  3. skill_off comparison → grade=record, no notify
"""
from __future__ import annotations

import os
os.environ.setdefault("USE_MOCK", "1")
os.environ.setdefault("DATABASE_URL", "postgresql://fake")

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.mocks import mock_chat_completion

client = TestClient(app)

FAKE_FAMILY = {"id": 99, "slug": "ah-ma"}
FAKE_PROFILES = {
    "elder": {
        "name": "Ah Ma", "age": 82,
        "conditions": ["高血压", "2型糖尿病"],
        "baseline_notes": "",
        "medications": [{"drug": "Amlodipine", "timing": "早饭后"}],
        "followups": {},
        "last_med_change_date": "2026-07-30",
    },
    "employer": {"name": "Rachel", "relation": "女儿", "work_schedule": "工作日不在场"},
    "caregiver": {"name": "Rosa"},
}
FAKE_OBS = [
    {"grade": "record", "restored_text": "午饭进食略少"},
    {"grade": "record", "restored_text": "仍进食减少"},
]


def _patches():
    return [
        patch("app.main.get_connection", return_value=_ctx()),
        patch("app.main.repo.get_family_by_slug", return_value=FAKE_FAMILY),
        patch("app.main.repo.get_profiles", return_value=FAKE_PROFILES),
        patch("app.main.repo.get_recent_observations", return_value=FAKE_OBS),
        patch("app.main.repo.get_recent_task_breakdowns", return_value=[]),
        patch("app.main.repo.save_observation", return_value={}),
        patch("app.main.repo.save_task_breakdown", return_value={}),
        patch("app.main._get_llm", return_value=mock_chat_completion),
    ]


def _ctx():
    conn = MagicMock()
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=conn)
    m.__exit__ = MagicMock(return_value=False)
    return m


def _post(text, role="auto", skill_on=True):
    with _patches()[0], _patches()[1], _patches()[2], \
         _patches()[3], _patches()[4], _patches()[5], _patches()[6]:
        return client.post(
            "/families/ah-ma/message",
            json={"text": text, "role": role, "skill_on": skill_on},
        )


class TestE2EDemo:
    def test_healthz(self):
        assert client.get("/healthz").status_code == 200

    def test_day5_helper_escalate(self):
        """节拍1: Rosa 汇报头晕 → escalate 红标。"""
        resp = _post(
            "Ma'am, Ah Ma today no mood to eat, lunch eat small small only half bowl and she say she feel a bit dizzy.",
            role="helper", skill_on=True,
        )
        assert resp.status_code == 200
        d = resp.json()
        assert d["type"] == "helper"
        assert d["grade"] == "escalate"
        assert "doctor" in d["notify"]
        assert "family" in d["notify"]
        assert d["outputs"]["helper"] is not None
        assert d["outputs"]["family"] is not None
        assert d["outputs"]["doctor"] is not None

    def test_day5_employer_task_breakdown(self):
        """节拍2: Rachel发备餐指令 → 5人份 tasks + English helper_message。"""
        resp = _post(
            "今晚我们四个人过来吃饭，妈妈的药记得饭前吃，6点要炒菜就早点准备",
            role="employer", skill_on=True,
        )
        assert resp.status_code == 200
        d = resp.json()
        assert d["type"] == "employer"
        assert "5" in d["understood"]
        assert len(d["tasks"]) >= 1
        assert len(d["confirmation_items"]) >= 1
        english_words = ["rosa", "tonight", "dinner", "pm", "hi", "thank"]
        assert any(w in d["helper_message"].lower() for w in english_words)

    def test_skill_off_comparison(self):
        """节拍3: skill_off → record, notify 空。"""
        resp = _post(
            "she feel a bit dizzy",
            role="helper", skill_on=False,
        )
        assert resp.status_code == 200
        d = resp.json()
        assert d["skill_on"] is False
        assert d["grade"] == "record"
        assert d["notify"] == []

    def test_404_unknown_family(self):
        with patch("app.main.get_connection", return_value=_ctx()), \
             patch("app.main.repo.get_family_by_slug", return_value=None):
            resp = client.post(
                "/families/ghost/message",
                json={"text": "hi", "role": "auto", "skill_on": True},
            )
        assert resp.status_code == 404
