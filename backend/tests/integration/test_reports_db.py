# Owner: Dev B
"""Reports against the loaded demo data. Read-only: no rows are written.
Run: RUN_DB_TESTS=1 uv run pytest tests/integration/test_reports_db.py"""

from __future__ import annotations

import pytest

from app.core.db import transaction
from tests.integration.conftest import AICTE

pytestmark = pytest.mark.db

SHADOW = "10000000-0000-4000-8000-000000000003"
YEAR = "2026-27"


def test_shadow_accreditation_cse_is_71_against_60(client):
    r = client.get(f"/reports/accreditation/{SHADOW}", headers=AICTE)
    assert r.status_code == 200, r.text
    assert r.headers["X-Mock"] != "true"
    cse = next(p for p in r.json()["programmes"] if p["programme_code"] == "UG-CSE")
    assert (cse["admitted_total"], cse["approved_total"], cse["overrun"]) == (71, 60, 11)


@pytest.mark.parametrize("group_by", ["state", "programme", "category", "gender"])
def test_enrolment_total_equals_active_admissions(client, group_by):
    r = client.get("/reports/enrolment", params={"group_by": group_by}, headers=AICTE)
    assert r.status_code == 200, r.text
    assert r.headers["X-Mock"] != "true"
    body = r.json()
    with transaction() as conn:
        active = conn.execute(
            "select count(*) as n from public.admissions where active and academic_year = %s",
            (YEAR,),
        ).fetchone()["n"]
    assert body["total"] == active
    assert sum(row["admissions"] for row in body["rows"]) == active
