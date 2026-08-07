"""
Database connection and schema management.

Uses psycopg3 (psycopg package). Connection string comes from the DATABASE_URL
environment variable (Railway provides this automatically).
"""
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row


def get_conn_str() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    return url


def get_connection() -> psycopg.Connection:
    """Return a new psycopg3 connection with dict_row factory."""
    return psycopg.connect(get_conn_str(), row_factory=dict_row)


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS families (
    id          SERIAL PRIMARY KEY,
    slug        TEXT UNIQUE NOT NULL,          -- e.g. "ah-ma"
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS employer_profiles (
    id          SERIAL PRIMARY KEY,
    family_id   INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    language    TEXT NOT NULL DEFAULT 'zh',
    relation    TEXT,                          -- e.g. "女儿"
    work_schedule TEXT,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS elder_profiles (
    id                  SERIAL PRIMARY KEY,
    family_id           INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    age                 INTEGER,
    conditions          TEXT[],                -- e.g. ARRAY['高血压','2型糖尿病']
    baseline_notes      TEXT,
    medications         JSONB NOT NULL DEFAULT '[]',
    followups           JSONB NOT NULL DEFAULT '{}',
    last_med_change_date DATE,
    last_med_change     JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS caregiver_profiles (
    id              SERIAL PRIMARY KEY,
    family_id       INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    home_country    TEXT,
    mother_tongue   TEXT,
    care_abilities  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS observations (
    id              SERIAL PRIMARY KEY,
    family_id       INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    observed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_text        TEXT NOT NULL,
    restored_text   TEXT,
    grade           TEXT CHECK (grade IN ('record','routine','escalate')),
    notify          TEXT[],                    -- e.g. ARRAY['family','doctor']
    reason          TEXT,
    outputs         JSONB NOT NULL DEFAULT '{}',
    skill_on        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS task_breakdowns (
    id              SERIAL PRIMARY KEY,
    family_id       INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    raw_instruction TEXT NOT NULL,
    understood      TEXT,
    tasks           JSONB NOT NULL DEFAULT '[]',
    helper_message  TEXT,
    confirmation_items JSONB NOT NULL DEFAULT '[]',
    skill_on        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


# CREATE TABLE IF NOT EXISTS 不会给已存在的表补列，线上库需要单独迁移。
MIGRATION_SQL = """
ALTER TABLE elder_profiles
    ADD COLUMN IF NOT EXISTS last_med_change JSONB NOT NULL DEFAULT '{}';
"""


def apply_schema() -> None:
    """Create all tables if they don't exist. Safe to run repeatedly."""
    with get_connection() as conn:
        conn.execute(SCHEMA_SQL)
        conn.execute(MIGRATION_SQL)
        conn.commit()


if __name__ == "__main__":
    apply_schema()
    print("Schema applied successfully.")
