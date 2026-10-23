# Owner: Dev B
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query

from app.core.datasource import source
from app.core.db import transaction
from app.core.security import require_roles
from app.mocks import mock, not_found
from app.models.admissions import Admission, EditDecision, EditRequest, EditRequestCreate
from app.models.auth import User
from app.models.common import AdmissionStatus, SeatPool
from app.services import admissions as service

router = APIRouter(tags=["admissions"])

READERS = require_roles("aicte_admin", "auditor", "institution_admin", "institution_operator")
EDITORS = require_roles("institution_admin", "institution_operator")
DECIDERS = require_roles("aicte_admin")
REAL = source("admissions")


@router.get("/admissions", response_model=list[Admission])
def list_admissions(
    institution_id: str | None = None,
    programme_id: str | None = None,
    academic_year: str | None = None,
    status: AdmissionStatus | None = None,
    seat_pool: SeatPool | None = None,
    limit: int = Query(50, ge=1, le=service.MAX_LIMIT),
    offset: int = Query(0, ge=0),
    user: User = Depends(READERS),
    real: bool = Depends(REAL),
) -> list[dict]:
    """List admissions. APAAR IDs are always masked as XXXX-XXXX-1234."""
    filters = {
        "institution_id": institution_id,
        "programme_id": programme_id,
        "academic_year": academic_year,
        "status": status,
        "seat_pool": seat_pool,
    }
    if real:
        with transaction() as conn:
            return service.list_admissions(conn, user, filters, limit, offset)
    rows = mock("admissions")
    matching = [r for r in rows if all(v is None or r[k] == v for k, v in filters.items())]
    return matching[offset : offset + limit]


@router.post(
    "/admissions/{admission_id}/edit-requests", response_model=EditRequest, status_code=201
)
def create_edit_request(
    admission_id: str,
    body: EditRequestCreate,
    user: User = Depends(EDITORS),
    real: bool = Depends(REAL),
) -> dict:
    if real:
        with transaction() as conn:
            return service.create_edit_request(conn, admission_id, body.model_dump(), user)
    admission = next((a for a in mock("admissions") if a["id"] == admission_id), None)
    if admission is None:
        raise not_found("Admission", admission_id)
    request = mock("edit_requests")[0]
    old = admission.get(body.field)
    request.update(
        admission_id=admission_id,
        field=body.field,
        old_value=None if old is None else str(old),
        new_value=body.new_value,
        reason=body.reason,
        requested_by=user.id,
        created_at=datetime.now(UTC).isoformat(),
    )
    return request


@router.post("/edit-requests/{edit_request_id}/decision", response_model=EditRequest)
def decide_edit_request(
    edit_request_id: str,
    body: EditDecision,
    user: User = Depends(DECIDERS),
    real: bool = Depends(REAL),
) -> dict:
    if real:
        with transaction() as conn:
            return service.decide_edit_request(
                conn, edit_request_id, body.decision, body.note, user
            )
    request = next((r for r in mock("edit_requests") if r["id"] == edit_request_id), None)
    if request is None:
        raise not_found("Edit request", edit_request_id)
    request.update(
        status=body.decision,
        decided_by=user.id,
        decision_note=body.note,
        decided_at=datetime.now(UTC).isoformat(),
    )
    return request
