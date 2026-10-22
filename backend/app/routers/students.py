# Owner: Dev E
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.mocks import mock, not_found
from app.models.auth import User
from app.models.students import AccessLogEntry, Consent, ConsentCreate, StudentRecords

router = APIRouter(prefix="/students/me", tags=["students"])

STUDENT = require_roles("student")


@router.get("/records", response_model=StudentRecords)
def my_records(user: User = Depends(STUDENT)) -> dict:
    student = mock("students").get(user.id)
    if student is None:
        raise not_found("Student", user.id)
    admissions = [a for a in mock("admissions") if a["student_id"] == user.id]
    return {"student": student, "admissions": admissions}


@router.get("/consents", response_model=list[Consent], dependencies=[Depends(STUDENT)])
def my_consents() -> list[dict]:
    return mock("consents")


@router.post("/consents", response_model=Consent, status_code=201, dependencies=[Depends(STUDENT)])
def grant_consent(body: ConsentCreate) -> dict:
    consent = mock("consents")[0]
    now = datetime.now(UTC)
    consent.update(
        verifier_id=body.verifier_id,
        verifier_name=body.verifier_id,
        purpose=body.purpose,
        fields=body.fields,
        granted_at=now.isoformat(),
        expires_at=(now + timedelta(days=body.expires_in_days)).isoformat(),
        revoked_at=None,
    )
    return consent


@router.get("/access-log", response_model=list[AccessLogEntry], dependencies=[Depends(STUDENT)])
def my_access_log() -> list[dict]:
    return mock("access_log")
