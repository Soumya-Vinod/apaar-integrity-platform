# Owner: Dev B
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.mocks import mock, not_found
from app.models.institutions import ApiKeyCreated, Institution, InstitutionDetail

router = APIRouter(prefix="/institutions", tags=["institutions"])

READERS = require_roles("aicte_admin", "auditor", "institution_admin", "institution_operator")


@router.get("", response_model=list[Institution], dependencies=[Depends(READERS)])
def list_institutions() -> list[dict]:
    return mock("institutions")


@router.get("/{institution_id}", response_model=InstitutionDetail, dependencies=[Depends(READERS)])
def get_institution(institution_id: str) -> dict:
    for item in mock("institutions"):
        if item["id"] == institution_id:
            return item
    raise not_found("Institution", institution_id)


@router.post(
    "/{institution_id}/api-keys",
    response_model=ApiKeyCreated,
    status_code=201,
    dependencies=[Depends(require_roles("institution_admin", "aicte_admin"))],
)
def create_api_key(institution_id: str) -> dict:
    key = mock("api_key")
    key["institution_id"] = institution_id
    return key
