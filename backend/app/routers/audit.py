# Owner: Dev B
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.audit import verify_chain
from app.core.security import require_roles
from app.mocks import mock
from app.models.audit import AuditVerifyResult

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/verify",
    response_model=AuditVerifyResult,
    dependencies=[Depends(require_roles("aicte_admin", "auditor"))],
)
def verify_audit_chain() -> AuditVerifyResult:
    events = mock("audit_events")
    broken = verify_chain(events)
    return AuditVerifyResult(ok=broken is None, first_broken_index=broken, checked=len(events))
