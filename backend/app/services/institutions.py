# Owner: Dev B
"""Institutions, programmes and integration API keys. Placeholders until implemented."""

from __future__ import annotations


def list_institutions() -> list[dict]:
    """Read institutions visible to the current user."""
    raise NotImplementedError


def create_api_key(institution_id: str) -> dict:
    """Generate a key, store only its SHA-256 hash in api_keys, return the key once."""
    raise NotImplementedError
