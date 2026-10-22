# Owner: Dev B
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Programme(BaseModel):
    id: str
    code: str
    name: str
    level: str
    duration_years: int


class Institution(BaseModel):
    id: str
    aicte_code: str
    name: str
    state: str
    parent_trust: str | None = None
    integrity_score: float | None = None


class InstitutionDetail(Institution):
    programmes: list[Programme]


class ApiKeyCreated(BaseModel):
    key_id: str
    institution_id: str
    api_key: str
    created_at: datetime
    note: str = "Shown once. Only a hash is stored."
