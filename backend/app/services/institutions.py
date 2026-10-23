# Owner: Dev B
"""Institutions, programmes and integration API keys on Postgres."""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

import psycopg
from fastapi import HTTPException, status

from app.core.security import scoped_institution
from app.models.auth import User
from app.services import audit_store
from app.services.batches import as_uuid


def _institution(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "aicte_code": row["aicte_code"],
        "name": row["name"],
        "state": row["state"],
        "parent_trust": row["parent_trust"],
        "integrity_score": None,  # filled by Dev A's integrity pipeline later
    }


def list_institutions(conn: psycopg.Connection, user: User) -> list[dict[str, Any]]:
    only = scoped_institution(user)
    rows = conn.execute(
        "select * from public.institutions where %s::uuid is null or id = %s::uuid"
        " order by aicte_code",
        (only, only),
    ).fetchall()
    return [_institution(r) for r in rows]


def get_institution(conn: psycopg.Connection, institution_id: str, user: User) -> dict[str, Any]:
    scoped_institution(user, institution_id)
    row = (
        conn.execute(
            "select * from public.institutions where id = %s", (institution_id,)
        ).fetchone()
        if as_uuid(institution_id)
        else None
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Institution '{institution_id}' not found")
    programmes = conn.execute(
        "select id, code, name, level, duration_years from public.programmes"
        " where institution_id = %s order by code",
        (institution_id,),
    ).fetchall()
    return {**_institution(row), "programmes": [{**p, "id": str(p["id"])} for p in programmes]}


def create_api_key(conn: psycopg.Connection, institution_id: str, user: User) -> dict[str, Any]:
    """Generate a key, store only its SHA-256 hash, return the key once."""
    get_institution(conn, institution_id, user)
    key = "apaar_" + secrets.token_urlsafe(32)
    row = conn.execute(
        "insert into public.api_keys (institution_id, key_hash) values (%s, %s)"
        " returning id, created_at",
        (institution_id, hashlib.sha256(key.encode()).hexdigest()),
    ).fetchone()
    audit_store.append_event(
        conn, user.id, "api_key.created", "api_key", row["id"], {"institution_id": institution_id}
    )
    return {
        "key_id": str(row["id"]),
        "institution_id": institution_id,
        "api_key": key,
        "created_at": row["created_at"],
    }
