# Owner: Dev A
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.mocks import mock, not_found
from app.models.integrity import IntegrityDetail, IntegrityRanking

router = APIRouter(
    prefix="/integrity",
    tags=["integrity"],
    dependencies=[Depends(require_roles("aicte_admin", "auditor"))],
)


@router.get("/institutions", response_model=list[IntegrityRanking])
def ranked_institutions() -> list[dict]:
    """Institutions ranked most anomalous first."""
    return mock("integrity_ranking")


@router.get("/institutions/{institution_id}", response_model=IntegrityDetail)
def institution_integrity(institution_id: str) -> dict:
    """Signals and anomaly explanation for one institution."""
    detail = mock("integrity_details").get(institution_id)
    if detail is None:
        raise not_found("Institution", institution_id)
    return detail
