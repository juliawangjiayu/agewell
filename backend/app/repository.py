"""
Repository: all database read/write operations.

All functions accept a psycopg3 connection so callers can control transactions.
"""
from __future__ import annotations

from typing import Any
import psycopg


# ---------------------------------------------------------------------------
# Family
# ---------------------------------------------------------------------------

def get_family_by_slug(conn: psycopg.Connection, slug: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM families WHERE slug = %s", (slug,)
    ).fetchone()
    return dict(row) if row else None


def create_family(conn: psycopg.Connection, slug: str) -> dict:
    row = conn.execute(
        "INSERT INTO families (slug) VALUES (%s) RETURNING *", (slug,)
    ).fetchone()
    conn.commit()
    return dict(row)


def get_or_create_family(conn: psycopg.Connection, slug: str) -> dict:
    fam = get_family_by_slug(conn, slug)
    if fam:
        return fam
    return create_family(conn, slug)


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

def upsert_employer_profile(
    conn: psycopg.Connection, family_id: int, data: dict[str, Any]
) -> dict:
    """Insert or replace the employer profile for a family."""
    conn.execute(
        "DELETE FROM employer_profiles WHERE family_id = %s", (family_id,)
    )
    row = conn.execute(
        """
        INSERT INTO employer_profiles
            (family_id, name, language, relation, work_schedule, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            family_id,
            data["name"],
            data.get("language", "zh"),
            data.get("relation"),
            data.get("work_schedule"),
            data.get("notes"),
        ),
    ).fetchone()
    conn.commit()
    return dict(row)


def upsert_elder_profile(
    conn: psycopg.Connection, family_id: int, data: dict[str, Any]
) -> dict:
    conn.execute(
        "DELETE FROM elder_profiles WHERE family_id = %s", (family_id,)
    )
    row = conn.execute(
        """
        INSERT INTO elder_profiles
            (family_id, name, age, conditions, baseline_notes,
             medications, followups, last_med_change_date)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
        RETURNING *
        """,
        (
            family_id,
            data["name"],
            data.get("age"),
            data.get("conditions", []),
            data.get("baseline_notes"),
            __json(data.get("medications", [])),
            __json(data.get("followups", {})),
            data.get("last_med_change_date"),
        ),
    ).fetchone()
    conn.commit()
    return dict(row)


def upsert_caregiver_profile(
    conn: psycopg.Connection, family_id: int, data: dict[str, Any]
) -> dict:
    conn.execute(
        "DELETE FROM caregiver_profiles WHERE family_id = %s", (family_id,)
    )
    row = conn.execute(
        """
        INSERT INTO caregiver_profiles
            (family_id, name, home_country, mother_tongue, care_abilities)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            family_id,
            data["name"],
            data.get("home_country"),
            data.get("mother_tongue"),
            data.get("care_abilities"),
        ),
    ).fetchone()
    conn.commit()
    return dict(row)


def get_profiles(conn: psycopg.Connection, family_id: int) -> dict:
    """Return all three profile dicts for a family (may be None if not set)."""
    employer = conn.execute(
        "SELECT * FROM employer_profiles WHERE family_id = %s", (family_id,)
    ).fetchone()
    elder = conn.execute(
        "SELECT * FROM elder_profiles WHERE family_id = %s", (family_id,)
    ).fetchone()
    caregiver = conn.execute(
        "SELECT * FROM caregiver_profiles WHERE family_id = %s", (family_id,)
    ).fetchone()
    return {
        "employer": dict(employer) if employer else None,
        "elder": dict(elder) if elder else None,
        "caregiver": dict(caregiver) if caregiver else None,
    }


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------

def save_observation(
    conn: psycopg.Connection, family_id: int, data: dict[str, Any]
) -> dict:
    row = conn.execute(
        """
        INSERT INTO observations
            (family_id, raw_text, restored_text, grade, notify,
             reason, outputs, skill_on)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
        RETURNING *
        """,
        (
            family_id,
            data["raw_text"],
            data.get("restored_text"),
            data.get("grade"),
            data.get("notify", []),
            data.get("reason"),
            __json(data.get("outputs", {})),
            data.get("skill_on", True),
        ),
    ).fetchone()
    conn.commit()
    return dict(row)


def get_recent_observations(
    conn: psycopg.Connection, family_id: int, limit: int = 10
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT * FROM observations
        WHERE family_id = %s
        ORDER BY observed_at DESC
        LIMIT %s
        """,
        (family_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Task Breakdowns
# ---------------------------------------------------------------------------

def save_task_breakdown(
    conn: psycopg.Connection, family_id: int, data: dict[str, Any]
) -> dict:
    row = conn.execute(
        """
        INSERT INTO task_breakdowns
            (family_id, raw_instruction, understood, tasks,
             helper_message, confirmation_items, skill_on)
        VALUES (%s, %s, %s, %s::jsonb, %s, %s::jsonb, %s)
        RETURNING *
        """,
        (
            family_id,
            data["raw_instruction"],
            data.get("understood"),
            __json(data.get("tasks", [])),
            data.get("helper_message"),
            __json(data.get("confirmation_items", [])),
            data.get("skill_on", True),
        ),
    ).fetchone()
    conn.commit()
    return dict(row)


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

def reset_family_observations(conn: psycopg.Connection, family_id: int) -> int:
    """Delete all observations and task_breakdowns for a family, return count deleted."""
    r1 = conn.execute(
        "DELETE FROM observations WHERE family_id = %s", (family_id,)
    )
    r2 = conn.execute(
        "DELETE FROM task_breakdowns WHERE family_id = %s", (family_id,)
    )
    conn.commit()
    return (r1.rowcount or 0) + (r2.rowcount or 0)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def __json(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)
