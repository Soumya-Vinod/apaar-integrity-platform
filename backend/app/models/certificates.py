# Owner: Dev B (contract consumed by Dev C's certificates router)
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Certificate(BaseModel):
    certificate_no: str
    student_id: str
    apaar_id: str | None
    provisional_id: str | None = None
    student_name: str
    institution_name: str
    programme_name: str
    academic_year: str
    issued_at: datetime
    verify_url: str
