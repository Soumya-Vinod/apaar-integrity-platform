# Owner: Dev E
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.mocks import mock, require_mock
from app.models.credentials import (
    Credential,
    CredentialRequest,
    PublicKey,
    Revocation,
    RevocationList,
    RevokeRequest,
)

router = APIRouter(prefix="/credentials", tags=["credentials"])


@router.post(
    "",
    response_model=Credential,
    status_code=201,
    dependencies=[Depends(require_roles("student"))],
)
def issue_credential(body: CredentialRequest) -> dict:
    """Issue an Ed25519-signed credential for one verifier. Mock returns a pre-signed demo."""
    return mock("credential")


@router.post(
    "/{credential_id}/revoke",
    response_model=Revocation,
    dependencies=[Depends(require_roles("student", "aicte_admin"))],
)
def revoke_credential(credential_id: str, body: RevokeRequest) -> Revocation:
    require_mock()
    return Revocation(credential_id=credential_id, reason=body.reason, revoked_at=datetime.now(UTC))


@router.get("/revocations", response_model=RevocationList)
def revocations() -> dict:
    """Public: offline verifiers sync this list."""
    return mock("revocations")


@router.get("/public-key", response_model=PublicKey)
def public_key() -> dict:
    """Public: the Ed25519 key verifiers use to check credential signatures."""
    return mock("public_key")
