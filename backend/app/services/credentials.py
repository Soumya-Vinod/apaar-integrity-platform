# Owner: Dev B
"""Ed25519-signed credentials with per-verifier pseudonyms. Placeholders until implemented."""

from __future__ import annotations


def issue_credential(
    student_id: str, verifier_id: str, fields: list[str], expires_in_days: int
) -> dict:
    """Pseudonym = HMAC(PSEUDONYM_SECRET, student_id|verifier_id); sign canonical payload with
    CREDENTIAL_SIGNING_KEY.
    """
    raise NotImplementedError


def revoke_credential(credential_id: str, reason: str) -> dict:
    """Insert into credential_revocations."""
    raise NotImplementedError
