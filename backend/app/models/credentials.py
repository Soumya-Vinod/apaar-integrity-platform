# Owner: Dev B (contract consumed by Dev E's credentials router)
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CredentialRequest(BaseModel):
    verifier_id: str
    purpose: str
    fields: list[str]
    expires_in_days: int = Field(30, ge=1, le=365)


class Credential(BaseModel):
    credential_id: str
    pseudonym: str = Field(description="Per-verifier pseudonym for the student")
    payload: dict[str, Any]
    signature_b64: str
    key_id: str
    qr_payload: str = Field(description="base64url(canonical payload) + '.' + base64url(signature)")
    expires_at: datetime


class RevokeRequest(BaseModel):
    reason: str = Field(min_length=1)


class Revocation(BaseModel):
    credential_id: str
    reason: str
    revoked_at: datetime


class RevocationList(BaseModel):
    updated_at: datetime
    revoked: list[Revocation]


class PublicKey(BaseModel):
    algorithm: Literal["Ed25519"] = "Ed25519"
    key_id: str
    public_key_b64: str
