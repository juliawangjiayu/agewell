"""
Seed script: pre-populate the Ah Ma / Rosa / 丽珍 demo family.

Run once after Railway Postgres is up:
    python -m app.seed

Day3 = last_med_change_date (Amlodipine 5→10mg, i.e. 3 days before demo Day5).
Pre-inserts 2 'record' observations so Day5 escalate has context.
"""
from __future__ import annotations

from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

from app import repository as repo
from app.db import apply_schema, get_connection

# ---------------------------------------------------------------------------
# Demo dates (relative to today = Day5 = demo day)
# ---------------------------------------------------------------------------

TODAY = date.today()
DAY1 = TODAY - timedelta(days=4)   # 周一
DAY3 = TODAY - timedelta(days=2)   # 周三 (med change)
DAY4 = TODAY - timedelta(days=1)   # 周四

FAMILY_SLUG = "ah-ma"

ELDER = {
    "name": "陈亚妹 (Ah Ma)",
    "age": 82,
    "conditions": ["高血压", "2型糖尿病"],
    "baseline_notes": "独自住在自己的 HDB，与 Rosa（住家女佣）同住；平时三餐正常，能自己走动，晚饭后爱看电视",
    "medications": [
        {"drug": "Amlodipine（氨氯地平）", "timing": "早饭后", "time": "08:00", "note": "降压"},
        {"drug": "Metformin（二甲双胍）", "timing": "早、晚饭后", "time": "08:00/19:00", "note": "降糖，可能引起肠胃不适"},
        {"drug": "Losartan（氯沙坦）", "timing": "早饭后", "time": "08:00", "note": "降压"},
    ],
    "followups": {
        "clinic": "Polyclinic",
        "interval": "每3个月",
        "next_date": str(TODAY),  # 今天复诊（也是丽珍来接的日子）
        "last_date": str(DAY3),
    },
    "last_med_change_date": str(DAY3),
}

EMPLOYER = {
    "name": "丽珍",
    "language": "zh",
    "relation": "女儿",
    "work_schedule": "与 Ah Ma 不同住。工作日各自生活；一般周五晚上接 Ah Ma 一起吃饭，周六、周日一起吃午饭和晚饭。周一到周四不在 Ah Ma 身边。",
    "notes": "主要照护决策者，但每周只有周五晚到周日在场；工作日老人身边只有 Rosa 一双眼睛，全靠 Rosa 转达。",
}

CAREGIVER = {
    "name": "Rosa",
    "home_country": "菲律宾",
    "mother_tongue": "Tagalog（常英菲混说，'eat small small'式）",
    "care_abilities": "照顾过长辈、会量血压、会做简单中餐/菲式家常菜",
}

# Pre-seeded observations (both 'record', to give Day5 context)
SEED_OBSERVATIONS = [
    {
        "raw_text": "Ah Ma today lunch eat small only",
        "restored_text": "午饭进食量减少约 50%",
        "grade": "record",
        "notify": [],
        "reason": "单次轻微波动，无持续性，不构成信号",
        "outputs": {
            "family": None,
            "doctor": None,
            "helper": "好的 Rosa，我记下了，先观察就好，不用担心。",
        },
        "skill_on": True,
        "observed_at_offset": DAY1,
    },
    {
        "raw_text": "still no mood to eat, half bowl only",
        "restored_text": "仍进食减少，本周多次",
        "grade": "record",
        "notify": [],
        "reason": "持续性但单一症状，暂记录观察",
        "outputs": {
            "family": None,
            "doctor": None,
            "helper": "好的 Rosa，记下了，继续留意她吃多少。",
        },
        "skill_on": True,
        "observed_at_offset": DAY4,
    },
]


def seed(skip_if_exists: bool = False) -> None:
    apply_schema()
    with get_connection() as conn:
        # 幂等：family 已存在时，skip_if_exists=True 则跳过 observations 写入
        existing = repo.get_family_by_slug(conn, FAMILY_SLUG)
        if skip_if_exists and existing:
            obs_count = conn.execute(
                "SELECT COUNT(*) FROM observations WHERE family_id = %s",
                (existing["id"],),
            ).fetchone()[0]
            if obs_count > 0:
                print(f"[seed] Family '{FAMILY_SLUG}' already seeded ({obs_count} obs), skipping.")
                return

        fam = repo.get_or_create_family(conn, FAMILY_SLUG)
        fid = fam["id"]
        print(f"[seed] Family '{FAMILY_SLUG}' id={fid}")

        repo.upsert_employer_profile(conn, fid, EMPLOYER)
        print("  ✓ employer_profile")

        repo.upsert_elder_profile(conn, fid, ELDER)
        print("  ✓ elder_profile")

        repo.upsert_caregiver_profile(conn, fid, CAREGIVER)
        print("  ✓ caregiver_profile")

        import copy
        for obs in copy.deepcopy(SEED_OBSERVATIONS):
            offset = obs.pop("observed_at_offset")
            saved = repo.save_observation(conn, fid, obs)
            conn.execute(
                "UPDATE observations SET observed_at = %s WHERE id = %s",
                (offset, saved["id"]),
            )
            conn.commit()
            print(f"  ✓ observation [{obs['grade']}] {obs['restored_text'][:30]}")

    print("[seed] Demo family 'ah-ma' is ready.")


if __name__ == "__main__":
    seed()
