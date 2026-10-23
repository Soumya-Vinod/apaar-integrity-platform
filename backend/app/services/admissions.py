# Owner: Dev B
"""Committed admissions and edit requests on Postgres. APAAR IDs always leave masked."""

from __future__ import annotations

from typing import Any

import psycopg
from fastapi import HTTPException, status

from app.core.security import scoped_institution
from app.models.auth import User
from app.services import audit_store
from app.services.batches import as_uuid
from app.services.validation import mask_apaar

MAX_LIMIT = 200

_SELECT = """
    select a.id, a.student_id, s.full_name as student_name, s.apaar_id, s.provisional_id,
           s.opted_out, s.dob, p.institution_id, a.programme_id, p.code as programme_code,
           a.academic_year, a.pool::text as seat_pool, a.admission_mode, a.admission_date,
           a.qualifying_exam_pct, a.status::text as status, a.batch_id
    from public.admissions a
    join public.students s on s.id = a.student_id
    join public.programmes p on p.id = a.programme_id
"""

# Fields an institution may ask to correct, mapped to (table alias, column, cast).
EDITABLE = {
    "admission_date": ("admissions", "admission_date", "date"),
    "admission_mode": ("admissions", "admission_mode", "text"),
    "qualifying_exam_pct": ("admissions", "qualifying_exam_pct", "numeric"),
    "student_name": ("students", "full_name", "text"),
    "dob": ("students", "dob", "date"),
}


def _admission(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "student_id": str(row["student_id"]),
        "student_name": row["student_name"],
        "apaar_id_masked": mask_apaar(row["apaar_id"]),
        "provisional_id": row["provisional_id"],
        "apaar_opt_out": row["opted_out"],
        "institution_id": str(row["institution_id"]),
        "programme_id": str(row["programme_id"]),
        "programme_code": row["programme_code"],
        "academic_year": row["academic_year"],
        "seat_pool": row["seat_pool"],
        "admission_mode": row["admission_mode"],
        "admission_date": row["admission_date"],
        "qualifying_exam_pct": float(row["qualifying_exam_pct"] or 0),
        "status": row["status"],
        "batch_id": str(row["batch_id"]) if row["batch_id"] else None,
    }


def list_admissions(
    conn: psycopg.Connection, user: User, filters: dict[str, Any], limit: int, offset: int
) -> list[dict[str, Any]]:
    institution = scoped_institution(user, filters.get("institution_id"))
    clauses, params = ["a.active"], []
    for column, value in (
        ("p.institution_id", institution),
        ("a.programme_id", filters.get("programme_id")),
        ("a.academic_year", filters.get("academic_year")),
        ("a.status::text", filters.get("status")),
        ("a.pool::text", filters.get("seat_pool")),
    ):
        if value is not None:
            if column.endswith("_id") and as_uuid(value) is None:
                return []
            clauses.append(f"{column} = %s")
            params.append(value)
    sql = (
        f"{_SELECT} where {' and '.join(clauses)}"
        " order by a.created_at desc, a.id limit %s offset %s"
    )
    rows = conn.execute(sql, (*params, min(limit, MAX_LIMIT), offset)).fetchall()
    return [_admission(r) for r in rows]


def _load_admission(conn: psycopg.Connection, admission_id: str, user: User) -> dict[str, Any]:
    row = (
        conn.execute(f"{_SELECT} where a.id = %s", (admission_id,)).fetchone()
        if as_uuid(admission_id)
        else None
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Admission '{admission_id}' not found")
    scoped_institution(user, str(row["institution_id"]))
    return row


def _edit_request(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "id": str(row["id"]),
        "admission_id": str(row["admission_id"]),
        "requested_by": str(row["requested_by"]) if row["requested_by"] else "demo-user",
        "decided_by": str(row["decided_by"]) if row["decided_by"] else None,
    }


def create_edit_request(
    conn: psycopg.Connection, admission_id: str, body: dict[str, str], user: User
) -> dict[str, Any]:
    if body["field"] not in EDITABLE:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"field must be one of {sorted(EDITABLE)}"
        )
    admission = _load_admission(conn, admission_id, user)
    old = admission.get(body["field"])
    row = conn.execute(
        """
        insert into public.edit_requests
          (admission_id, field, old_value, new_value, reason, requested_by)
        values (%s, %s, %s, %s, %s, %s) returning *
        """,
        (
            admission_id,
            body["field"],
            None if old is None else str(old),
            body["new_value"],
            body["reason"],
            as_uuid(user.id),
        ),
    ).fetchone()
    audit_store.append_event(
        conn,
        user.id,
        "edit_request.created",
        "edit_request",
        row["id"],
        {"admission_id": admission_id, "field": body["field"]},
    )
    return _edit_request(row)


def decide_edit_request(
    conn: psycopg.Connection, edit_request_id: str, decision: str, note: str | None, user: User
) -> dict[str, Any]:
    """Approve (and apply) or reject a pending edit request."""
    row = (
        conn.execute(
            "select * from public.edit_requests where id = %s for update", (edit_request_id,)
        ).fetchone()
        if as_uuid(edit_request_id)
        else None
    )
    if row is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Edit request '{edit_request_id}' not found"
        )
    if row["status"] != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Edit request is already {row['status']}")
    if decision == "approved":
        table, column, cast = EDITABLE[row["field"]]
        target = (
            "where id = %s"
            if table == "admissions"
            else "where id = (select student_id from public.admissions where id = %s)"
        )
        try:
            conn.execute(
                f"update public.{table} set {column} = %s::{cast} {target}",
                (row["new_value"], row["admission_id"]),
            )
        except psycopg.Error as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "new_value is not valid for this field"
            ) from exc
    row = conn.execute(
        """
        update public.edit_requests
        set status = %s, decided_by = %s, decision_note = %s, decided_at = now()
        where id = %s returning *
        """,
        (decision, as_uuid(user.id), note, edit_request_id),
    ).fetchone()
    audit_store.append_event(
        conn,
        user.id,
        f"edit_request.{decision}",
        "edit_request",
        row["id"],
        {"admission_id": str(row["admission_id"]), "field": row["field"]},
    )
    return _edit_request(row)
