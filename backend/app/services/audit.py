# Owner: Dev B
"""Audit log persistence on top of app.core.audit. Placeholders until implemented."""

from __future__ import annotations


def record(actor: str, action: str, entity_type: str, entity_id: str, payload: dict) -> dict:
    """Lock the latest row, chain the new event with append_event and insert it."""
    raise NotImplementedError


def load_chain() -> list[dict]:
    """Read audit_events ordered by id for verify_chain."""
    raise NotImplementedError
