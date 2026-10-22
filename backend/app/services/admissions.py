# Owner: Dev B
"""Committed admissions and edit requests. Placeholders until implemented."""

from __future__ import annotations


def list_admissions(filters: dict) -> list[dict]:
    """Query admissions with filters; always mask APAAR IDs in output."""
    raise NotImplementedError


def create_edit_request(admission_id: str, field: str, new_value: str, reason: str) -> dict:
    """Record a pending edit request and an audit event."""
    raise NotImplementedError


def decide_edit_request(edit_request_id: str, decision: str, note: str | None) -> dict:
    """Apply or reject an edit request and write an audit event."""
    raise NotImplementedError
