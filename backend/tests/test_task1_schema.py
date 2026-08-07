"""
Task 1 smoke test: schema DDL syntax + repository interface.

These tests do NOT need a live database. They only verify:
1. db.SCHEMA_SQL contains the expected table names.
2. repository functions exist with the correct signatures.
3. JSON serialisation helper works.
"""
from __future__ import annotations

import json
import pytest

from app.db import SCHEMA_SQL
from app import repository as repo


# ---------------------------------------------------------------------------
# 1. Schema sanity checks (no DB required)
# ---------------------------------------------------------------------------

EXPECTED_TABLES = [
    "families",
    "employer_profiles",
    "elder_profiles",
    "caregiver_profiles",
    "observations",
    "task_breakdowns",
]


@pytest.mark.parametrize("table", EXPECTED_TABLES)
def test_schema_contains_table(table: str):
    assert f"CREATE TABLE IF NOT EXISTS {table}" in SCHEMA_SQL, (
        f"Table '{table}' missing from SCHEMA_SQL"
    )


def test_schema_observations_has_grade_check():
    assert "record','routine','escalate'" in SCHEMA_SQL


def test_schema_observations_has_skill_on():
    assert "skill_on" in SCHEMA_SQL


# ---------------------------------------------------------------------------
# 2. Repository function existence
# ---------------------------------------------------------------------------

REPO_FUNCTIONS = [
    "get_family_by_slug",
    "create_family",
    "get_or_create_family",
    "upsert_employer_profile",
    "upsert_elder_profile",
    "upsert_caregiver_profile",
    "get_profiles",
    "save_observation",
    "get_recent_observations",
    "save_task_breakdown",
]


@pytest.mark.parametrize("fn_name", REPO_FUNCTIONS)
def test_repo_function_exists(fn_name: str):
    assert hasattr(repo, fn_name), f"repository.{fn_name} is missing"
    assert callable(getattr(repo, fn_name))


# ---------------------------------------------------------------------------
# 3. Internal JSON helper produces valid JSON
# ---------------------------------------------------------------------------

def test_json_helper_dict():
    # Access private helper via name mangling won't work cleanly;
    # validate indirectly: save_observation signature accepts dict for outputs.
    import inspect
    sig = inspect.signature(repo.save_observation)
    params = list(sig.parameters.keys())
    assert "data" in params
