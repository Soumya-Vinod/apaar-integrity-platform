# Owner: Dev B
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.datasource import source
from app.core.db import transaction
from app.core.security import require_roles
from app.mocks import mock, not_found
from app.models.auth import User
from app.models.institutions import ApiKeyCreated, Institution, InstitutionDetail
from app.services import institutions as service

router = APIRouter(prefix="/institutions", tags=["institutions"])

READERS = require_roles("aicte_admin", "auditor", "institution_admin", "institution_operator")
KEY_ADMINS = require_roles("institution_admin", "aicte_admin")
REAL = source("institutions")


@router.get("", response_model=list[Institution])
def list_institutions(user: User = Depends(READERS), real: bool = Depends(REAL)) -> list[dict]:
    if real:
        with transaction() as conn:
            return service.list_institutions(conn, user)
    return mock("institutions")


@router.get("/{institution_id}", response_model=InstitutionDetail)
def get_institution(
    institution_id: str, user: User = Depends(READERS), real: bool = Depends(REAL)
) -> dict:
    if real:
        with transaction() as conn:
            return service.get_institution(conn, institution_id, user)
    for item in mock("institutions"):
        if item["id"] == institution_id:
            return item
    raise not_found("Institution", institution_id)


@router.post("/{institution_id}/api-keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(
    institution_id: str, user: User = Depends(KEY_ADMINS), real: bool = Depends(REAL)
) -> dict:
    if real:
        with transaction() as conn:
            return service.create_api_key(conn, institution_id, user)
    key = mock("api_key")
    key["institution_id"] = institution_id
    return key
