# Owner: Dev B
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.security import require_roles
from app.mocks import mock, not_found
from app.models.seat_ledger import SeatLedger

router = APIRouter(tags=["seat-ledger"])


@router.get(
    "/institutions/{institution_id}/seat-ledger",
    response_model=SeatLedger,
    dependencies=[
        Depends(
            require_roles("aicte_admin", "auditor", "institution_admin", "institution_operator")
        )
    ],
)
def get_seat_ledger(institution_id: str, academic_year: str = Query("2026-27")) -> dict:
    ledger = mock("seat_ledger").get(institution_id)
    if ledger is None or ledger["academic_year"] != academic_year:
        raise not_found("Seat ledger", f"{institution_id}/{academic_year}")
    return ledger
