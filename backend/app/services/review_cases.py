# Owner: Dev B
"""Review cases raised by validation, Blind Match, disputes and engine signals. Placeholders until
implemented.
"""

from __future__ import annotations


def list_cases(kind: str | None, status: str | None) -> list[dict]:
    """Query review cases."""
    raise NotImplementedError


def resolve_case(case_id: str, status: str, note: str) -> dict:
    """Set the outcome, store the reviewer note, emit review_case.updated on `platform`."""
    raise NotImplementedError
