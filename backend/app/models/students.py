# Owner: Dev B (contract consumed by Dev E's students router)
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.admissions import Admission


class StudentProfile(BaseModel):
    id: str
    full_name: str
    apaar_id: str | None
    provisional_id: str | None = None
    opted_out: bool
    dob: date
    telegram_linked: bool


class StudentRecords(BaseModel):
    student: StudentProfile
    admissions: list[Admission]


class ConsentCreate(BaseModel):
    verifier_id: str
    purpose: str
    fields: list[str]
    expires_in_days: int = Field(30, ge=1, le=365)


class Consent(BaseModel):
    id: str
    verifier_id: str
    verifier_name: str
    purpose: str
    fields: list[str]
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


class AccessLogEntry(BaseModel):
    id: str
    accessor: str
    accessor_role: str
    purpose: str
    fields: list[str]
    consent_id: str | None
    accessed_at: datetime
