# Owner: Dev B
"""Seat Ledger: approved intake per programme, academic year and pool. Placeholders until
implemented.
"""

from __future__ import annotations


def get_ledger(institution_id: str, academic_year: str) -> dict:
    """Join seat_pools with committed admissions to compute admitted, available and overrun per
    pool.
    """
    raise NotImplementedError


def consume_seat(programme_id: str, academic_year: str, pool: str) -> bool:
    """Consume one seat at commit; return False on overrun so the caller opens an intake_overrun
    review case.
    """
    raise NotImplementedError
