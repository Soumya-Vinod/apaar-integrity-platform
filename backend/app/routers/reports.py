# Owner: Dev C
from __future__ import annotations

from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.datasource import source
from app.core.db import transaction
from app.core.security import require_roles, scoped_institution
from app.mocks import mock, not_found
from app.models.auth import User
from app.models.common import ReportFormat
from app.models.reports import AccreditationReport, EnrolmentReport, GroupBy
from app.services.reports import to_pdf, to_xlsx

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)
READERS = require_roles("aicte_admin", "auditor", "institution_admin")
REAL = source("reports")
ACADEMIC_YEAR = "2026-27"

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FILE_RESPONSES = {
    200: {
        "content": {"application/pdf": {}, XLSX: {}},
        "description": "JSON, or the file when format=pdf or format=xlsx",
    }
}


def _file(name: str, fmt: str, title: str, rows: list[dict]) -> Response:
    if fmt == "xlsx":
        body, media = to_xlsx(rows), XLSX
    else:
        lines = [", ".join(f"{k}: {v}" for k, v in r.items()) for r in rows]
        body, media = to_pdf(title, lines), "application/pdf"
    return Response(
        body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{name}.{fmt}"'},
    )


@lru_cache
def _aggregations():
    """Load Dev C's workspace data layer without importing or changing other backend modules."""
    path = Path(__file__).resolve().parents[3] / "reports" / "aggregations.py"
    spec = spec_from_file_location("apaar_report_aggregations", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Report aggregation module is unavailable")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _frame(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame([dict(row) for row in rows], columns=columns)


def _enrolment_report(conn, group_by: GroupBy, institution_id: str | None) -> dict:
    rows = conn.execute(
        """
        select a.id as admission_id, a.programme_id, p.code as programme_code,
               i.state, s.category, s.gender, s.opted_out, a.active
        from public.admissions a
        join public.students s on s.id = a.student_id
        join public.programmes p on p.id = a.programme_id
        join public.institutions i on i.id = p.institution_id
        where a.academic_year = %s
          and (%s::uuid is null or p.institution_id = %s::uuid)
        """,
        (ACADEMIC_YEAR, institution_id, institution_id),
    ).fetchall()
    admissions = _frame(
        rows,
        [
            "admission_id",
            "programme_id",
            "programme_code",
            "state",
            "category",
            "gender",
            "opted_out",
            "active",
        ],
    )
    grouped = _aggregations().enrolment_rows(admissions, group_by)
    report_rows = grouped.to_dict("records")
    return {
        "academic_year": ACADEMIC_YEAR,
        "group_by": group_by,
        "total": int(grouped["admissions"].sum()) if not grouped.empty else 0,
        "rows": report_rows,
    }


def _accreditation_report(conn, institution_id: str) -> dict:
    institution = conn.execute(
        "select id as institution_id, name as institution_name from public.institutions where id = %s",
        (institution_id,),
    ).fetchone()
    if institution is None:
        raise not_found("Institution", institution_id)
    admissions_rows = conn.execute(
        """
        select a.id as admission_id, a.programme_id, p.code as programme_code,
               s.category, s.gender, s.opted_out, s.apaar_id, a.active
        from public.admissions a
        join public.students s on s.id = a.student_id
        join public.programmes p on p.id = a.programme_id
        where p.institution_id = %s and a.academic_year = %s
        """,
        (institution_id, ACADEMIC_YEAR),
    ).fetchall()
    intake_rows = conn.execute(
        """
        select sp.programme_id, p.code as programme_code, sp.pool::text as pool,
               sp.approved_seats, sp.rule_version
        from public.seat_pools sp
        join public.programmes p on p.id = sp.programme_id
        where p.institution_id = %s and sp.academic_year = %s
        """,
        (institution_id, ACADEMIC_YEAR),
    ).fetchall()
    score = conn.execute(
        """
        select score from public.integrity_scores
        where institution_id = %s and academic_year = %s
        order by computed_at desc limit 1
        """,
        (institution_id, ACADEMIC_YEAR),
    ).fetchone()
    if score is None:
        raise not_found("Integrity score", f"{institution_id}/{ACADEMIC_YEAR}")
    review_cases = conn.execute(
        """
        select count(*) as n from public.review_cases
        where institution_id = %s and status = 'open'
          and (evidence->>'academic_year' = %s or evidence->>'academic_year' is null)
        """,
        (institution_id, ACADEMIC_YEAR),
    ).fetchone()
    admissions = _frame(
        admissions_rows,
        [
            "admission_id",
            "programme_id",
            "programme_code",
            "category",
            "gender",
            "opted_out",
            "apaar_id",
            "active",
        ],
    )
    intake = _frame(
        intake_rows,
        ["programme_id", "programme_code", "pool", "approved_seats", "rule_version"],
    )
    active = admissions.loc[admissions["active"].fillna(False).astype(bool)]
    apaar_coverage = 0.0
    if not active.empty:
        has_apaar = active["apaar_id"].fillna("").astype(str).str.strip().ne("")
        apaar_coverage = round(100 * int(has_apaar.sum()) / len(active), 1)
    return _aggregations().accreditation_report(
        dict(institution),
        admissions,
        intake,
        academic_year=ACADEMIC_YEAR,
        integrity_score=float(score["score"]),
        apaar_coverage_pct=apaar_coverage,
        open_review_cases=int(review_cases["n"]),
    )


@router.get("/enrolment", response_model=EnrolmentReport, responses=FILE_RESPONSES)
def enrolment(
    group_by: GroupBy = Query("state"),
    format: ReportFormat = Query("json"),
    user: User = Depends(READERS),
    real: bool = Depends(REAL),
):
    if real:
        with transaction() as conn:
            report = _enrolment_report(conn, group_by, scoped_institution(user))
    else:
        if user.role == "institution_admin":
            from fastapi import HTTPException

            raise HTTPException(403, "Institution enrolment reports are unavailable in mock mode")
        report = mock("enrolment_report")[group_by]
    if format == "json":
        return report
    title = f"Enrolment {report['academic_year']} by {group_by}"
    return _file(f"enrolment-{group_by}", format, title, report["rows"])


@router.get(
    "/accreditation/{institution_id}",
    response_model=AccreditationReport,
    responses=FILE_RESPONSES,
)
def accreditation(
    institution_id: str,
    format: ReportFormat = Query("json"),
    user: User = Depends(READERS),
    real: bool = Depends(REAL),
):
    scoped_id = scoped_institution(user, institution_id)
    if real:
        with transaction() as conn:
            report = _accreditation_report(conn, scoped_id or institution_id)
    else:
        report = mock("accreditation").get(scoped_id or institution_id)
        if report is None:
            raise not_found("Institution", institution_id)
    if format == "json":
        return report
    title = f"Accreditation summary: {report['institution_name']}"
    return _file(f"accreditation-{institution_id}", format, title, report["programmes"])
