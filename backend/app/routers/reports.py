# Owner: Dev C
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.security import require_roles
from app.mocks import mock, not_found
from app.models.common import ReportFormat
from app.models.reports import AccreditationReport, EnrolmentReport, GroupBy
from app.services.reports import to_pdf, to_xlsx

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(require_roles("aicte_admin", "auditor", "institution_admin"))],
)

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


@router.get("/enrolment", response_model=EnrolmentReport, responses=FILE_RESPONSES)
def enrolment(group_by: GroupBy = Query("state"), format: ReportFormat = Query("json")):
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
def accreditation(institution_id: str, format: ReportFormat = Query("json")):
    report = mock("accreditation").get(institution_id)
    if report is None:
        raise not_found("Institution", institution_id)
    if format == "json":
        return report
    title = f"Accreditation summary: {report['institution_name']}"
    return _file(f"accreditation-{institution_id}", format, title, report["programmes"])
