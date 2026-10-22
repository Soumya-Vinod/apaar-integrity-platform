# Owner: Dev A
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.mocks import mock
from app.models.blind_match import BlindMatchCase, EncodeRequest, EncodeResponse

router = APIRouter(prefix="/blind-match", tags=["blind-match"])


@router.post(
    "/encode",
    response_model=EncodeResponse,
    dependencies=[Depends(require_roles("aicte_admin"))],
)
def encode(body: EncodeRequest) -> dict:
    """Demo only: show what a Bloom-filter encoding looks like. Never stores input."""
    return mock("blind_match_encode")


@router.get(
    "/cases",
    response_model=list[BlindMatchCase],
    dependencies=[Depends(require_roles("aicte_admin", "auditor"))],
)
def cases() -> list[dict]:
    return mock("blind_match_cases")
