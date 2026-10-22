# Owner: Dev B
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.mocks import mock, not_found
from app.models.common import CaseKind, CaseStatus
from app.models.review_cases import ResolveRequest, ReviewCase

router = APIRouter(prefix="/review-cases", tags=["review-cases"])

READERS = require_roles("aicte_admin", "auditor", "institution_admin")


@router.get("", response_model=list[ReviewCase], dependencies=[Depends(READERS)])
def list_review_cases(kind: CaseKind | None = None, status: CaseStatus | None = None) -> list[dict]:
    return [
        c
        for c in mock("review_cases")
        if (kind is None or c["kind"] == kind) and (status is None or c["status"] == status)
    ]


def _case(case_id: str) -> dict:
    case = next((c for c in mock("review_cases") if c["id"] == case_id), None)
    if case is None:
        raise not_found("Review case", case_id)
    return case


@router.get("/{case_id}", response_model=ReviewCase, dependencies=[Depends(READERS)])
def get_review_case(case_id: str) -> dict:
    return _case(case_id)


@router.post(
    "/{case_id}/resolve",
    response_model=ReviewCase,
    dependencies=[Depends(require_roles("aicte_admin"))],
)
def resolve_review_case(case_id: str, body: ResolveRequest) -> dict:
    case = _case(case_id)
    now = datetime.now(UTC).isoformat()
    case.update(status=body.status, reviewer_note=body.note, updated_at=now)
    if body.status in ("confirmed", "dismissed"):
        case["resolved_at"] = now
    return case
