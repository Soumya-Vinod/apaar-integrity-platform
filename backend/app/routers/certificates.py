# Owner: Dev C
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_roles
from app.mocks import mock, not_found
from app.models.auth import User
from app.models.certificates import Certificate

router = APIRouter(prefix="/certificates", tags=["certificates"])

VIEWERS = require_roles("student", "institution_admin", "aicte_admin")


@router.get("/{student_id}", response_model=Certificate)
def get_certificate(
    student_id: str,
    user: User = Depends(VIEWERS),
) -> dict:
    """Certificate data with the APAAR ID next to the student ID and a verify link."""
    if user.role == "student" and user.id != student_id:
        raise HTTPException(403, "Students can only fetch their own certificate")
    student = mock("students").get(student_id)
    if student is None:
        raise not_found("Student", student_id)
    serial = int(student_id[-6:])
    return {
        "certificate_no": f"CERT-2026-{serial:06d}",
        "student_id": student_id,
        "apaar_id": student["apaar_id"],
        "provisional_id": student["provisional_id"],
        "student_name": student["full_name"],
        "institution_name": student["institution_name"],
        "programme_name": student["programme_name"],
        "academic_year": "2026-27",
        "issued_at": "2026-09-15T00:00:00Z",
        "verify_url": f"/verifier?certificate=CERT-2026-{serial:06d}",
    }
