# Owner: Dev A
"""Rule-based integrity signals computed over committed admissions."""

from __future__ import annotations

from typing import Any

from engine.types import Signal

Row = dict[str, Any]


def eligibility(admissions: list[Row]) -> list[Signal]:
    """Flag admissions whose qualifying percentage or age breaks programme norms.

    Intended algorithm: compare ``qualifying_exam_pct`` with the AICTE minimum for the
    programme level and category, and age at admission with the plausible range; group
    violations per institution and emit one Signal per institution with counts as evidence.
    """
    raise NotImplementedError


def shared_contact_clusters(admissions: list[Row], min_size: int = 5) -> list[Signal]:
    """Flag clusters of students sharing the same hashed phone or email.

    Intended algorithm: group by ``contact_hash``; any group of at least ``min_size``
    distinct students raises SHARED_CONTACT_CLUSTER against each institution involved.
    """
    raise NotImplementedError


def backdating(admissions: list[Row]) -> list[Signal]:
    """Flag admissions entered long after their stated admission date.

    Intended algorithm: compare ``admission_date`` with the batch upload time and the
    institution's usual admission window; outliers raise BACKDATED_ENTRY.
    """
    raise NotImplementedError


def cap_filling(admissions: list[Row], seat_pools: list[Row]) -> list[Signal]:
    """Flag pools filled to or beyond approved intake, especially late management fills.

    Intended algorithm: count admissions per (programme, academic_year, pool) and compare
    with ``approved_seats``; overruns raise INTAKE_OVERRUN; pools filled exactly to cap by a
    late surge of management or spot admissions raise a review signal.
    """
    raise NotImplementedError
