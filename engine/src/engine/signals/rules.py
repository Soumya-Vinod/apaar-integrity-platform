# Owner: Dev A
"""Rule-based integrity signals computed over committed admissions.

This module provides backward-compatible functional wrappers around the modular
signals implemented in engine.signals.
"""

from __future__ import annotations

from typing import Any

from engine.signals.backdated import backdated_signal
from engine.signals.eligibility import eligibility_signal
from engine.signals.shared_contacts import shared_contacts_signal
from engine.types import Signal

Row = dict[str, Any]


def eligibility(admissions: list[Row]) -> list[Signal]:
    """Flag admissions whose qualifying percentage or age breaks programme norms."""
    return eligibility_signal(admissions)


def shared_contact_clusters(admissions: list[Row], min_size: int = 5) -> list[Signal]:
    """Flag clusters of students sharing the same hashed phone or email."""
    return shared_contacts_signal(admissions, min_cluster_size=min_size)


def backdating(admissions: list[Row]) -> list[Signal]:
    """Flag admissions entered long after their stated admission date."""
    return backdated_signal(admissions)


def cap_filling(admissions: list[Row], seat_pools: list[Row]) -> list[Signal]:
    """Flag pools filled beyond approved intake."""
    return eligibility_signal(admissions, seat_pools=seat_pools)
