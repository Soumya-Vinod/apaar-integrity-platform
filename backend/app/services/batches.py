# Owner: Dev B
"""Batch pipeline on Postgres: upload, mapping, validation and the Seat Ledger commit."""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

import psycopg
from fastapi import HTTPException, status
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.core.rule_codes import RuleCode
from app.core.security import scoped_institution
from app.models.auth import User
from app.services import audit_store
from app.services.ingestion import (
    NormalizedRow,
    check_mapping,
    missing_required,
    normalize_row,
    parse_upload,
    sanitize_raw,
    suggest_mapping,
)
from app.services.validation import (
    Finding,
    ValidationContext,
    count_findings,
    error_rows,
    validate_rows,
)

Event = tuple[str, dict[str, Any]]
PoolKey = tuple[str, str, str]  # (programme_id, academic_year, pool)


# ---------------------------------------------------------------------------- helpers
def as_uuid(value: str | None) -> str | None:
    """Demo users have non-UUID ids; those are stored as NULL in uuid columns."""
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return None


def require_secret(settings: Settings) -> str:
    if not settings.pseudonym_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "PSEUDONYM_SECRET is not configured; contacts cannot be hashed",
        )
    return settings.pseudonym_secret


def batch_out(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "institution_id": str(row["institution_id"]),
        "uploaded_by": str(row["uploaded_by"]) if row["uploaded_by"] else "demo-user",
        "file_name": row["file_name"],
        "file_hash": row["file_hash"],
        "status": row["status"],
        "counts": row["counts"] or {},
        "created_at": row["created_at"],
    }


def upload_result(row: dict[str, Any], duplicate: bool) -> dict[str, Any]:
    headers = row["header"] or []
    mapping = row["column_mapping"] or {}
    return {
        "batch": batch_out(row),
        "suggested_mapping": mapping,
        "unmapped_columns": [h for h in headers if h not in mapping],
        "missing_required": missing_required(mapping),
        "duplicate_upload": duplicate,
    }


def load_batch(
    conn: psycopg.Connection, batch_id: str, user: User, lock: bool = False
) -> dict[str, Any]:
    if as_uuid(batch_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Batch '{batch_id}' not found")
    sql = "select * from public.batches where id = %s" + (" for update" if lock else "")
    row = conn.execute(sql, (batch_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Batch '{batch_id}' not found")
    scoped_institution(user, str(row["institution_id"]))
    return row


# ---------------------------------------------------------------------------- upload
def upload(
    conn: psycopg.Connection, user: User, file_name: str, content: bytes, settings: Settings
) -> tuple[dict[str, Any], bool]:
    """Store a new batch, or return the existing one for the same institution and file."""
    institution_id = scoped_institution(user)
    if institution_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only institution users upload batches")
    secret = require_secret(settings)
    parsed = parse_upload(
        file_name, content, max_mb=settings.max_upload_mb, max_rows=settings.max_upload_rows
    )
    existing = conn.execute(
        "select * from public.batches where institution_id = %s and file_hash = %s",
        (institution_id, parsed.file_hash),
    ).fetchone()
    if existing is not None:
        return upload_result(existing, duplicate=True), True

    suggestion = suggest_mapping(parsed.headers)
    raw = sanitize_raw(parsed.rows, suggestion.mapping, secret)
    batch = conn.execute(
        """
        insert into public.batches
          (institution_id, uploaded_by, file_name, file_hash, status, column_mapping, header,
           counts, rows_total)
        values (%s, %s, %s, %s, 'uploaded', %s, %s, %s, %s)
        returning *
        """,
        (
            institution_id,
            as_uuid(user.id),
            file_name,
            parsed.file_hash,
            Jsonb(suggestion.mapping),
            Jsonb(parsed.headers),
            Jsonb({"rows_total": len(raw)}),
            len(raw),
        ),
    ).fetchone()
    conn.execute(
        """
        insert into public.batch_rows (batch_id, row_number, raw)
        select %s, x.row_number, x.raw
        from jsonb_to_recordset(%s) as x(row_number int, raw jsonb)
        """,
        (batch["id"], Jsonb([{"row_number": i, "raw": r} for i, r in enumerate(raw, 1)])),
    )
    audit_store.append_event(
        conn,
        user.id,
        "batch.uploaded",
        "batch",
        batch["id"],
        {"file_hash": parsed.file_hash, "rows": len(raw)},
    )
    if not suggestion.missing_required:
        batch = validate(conn, batch, settings, user)
    return upload_result(batch, duplicate=False), False


def apply_mapping(
    conn: psycopg.Connection,
    batch_id: str,
    mapping: dict[str, str],
    user: User,
    settings: Settings,
) -> dict[str, Any]:
    batch = load_batch(conn, batch_id, user, lock=True)
    if batch["status"] == "committed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Batch is already committed")
    check_mapping(mapping, batch["header"] or [])
    missing = missing_required(mapping)
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Required columns not mapped: {missing}"
        )
    secret = require_secret(settings)
    # Re-sanitise with the new mapping so a column newly mapped as a contact gets hashed.
    stored = conn.execute(
        "select row_number, raw from public.batch_rows where batch_id = %s order by row_number",
        (batch_id,),
    ).fetchall()
    clean = sanitize_raw([r["raw"] for r in stored], mapping, secret)
    conn.execute(
        """
        update public.batch_rows b set raw = x.raw
        from jsonb_to_recordset(%s) as x(row_number int, raw jsonb)
        where b.batch_id = %s and b.row_number = x.row_number
        """,
        (
            Jsonb(
                [
                    {"row_number": s["row_number"], "raw": c}
                    for s, c in zip(stored, clean, strict=True)
                ]
            ),
            batch_id,
        ),
    )
    batch = conn.execute(
        "update public.batches set column_mapping = %s, status = 'mapped' where id = %s"
        " returning *",
        (Jsonb(mapping), batch_id),
    ).fetchone()
    audit_store.append_event(
        conn, user.id, "batch.mapped", "batch", batch_id, {"columns": len(mapping)}
    )
    return validate(conn, batch, settings, user)


# ---------------------------------------------------------------------------- validate
def validation_context(
    conn: psycopg.Connection, institution_id: str, settings: Settings
) -> ValidationContext:
    institution = conn.execute(
        "select aicte_code from public.institutions where id = %s", (institution_id,)
    ).fetchone()
    codes = {
        r["code"]
        for r in conn.execute(
            "select code from public.programmes where institution_id = %s", (institution_id,)
        ).fetchall()
    }

    def lookup(apaar_ids: list[str]) -> dict[str, str]:
        rows = conn.execute(
            """
            select distinct on (s.apaar_id) s.apaar_id, i.aicte_code
            from public.admissions a
            join public.students s on s.id = a.student_id
            join public.programmes p on p.id = a.programme_id
            join public.institutions i on i.id = p.institution_id
            where a.active and s.apaar_id = any(%s) and p.institution_id <> %s
            order by s.apaar_id, i.aicte_code
            """,
            (apaar_ids, institution_id),
        ).fetchall()
        return {r["apaar_id"]: r["aicte_code"] for r in rows}

    return ValidationContext(
        cutoff=settings.admission_cutoff_date,
        shared_contact_threshold=settings.shared_contact_threshold,
        institution_code=institution["aicte_code"] if institution else None,
        programme_codes=codes,
        cross_institution_lookup=lookup,
    )


def _normalized(
    conn: psycopg.Connection, batch: dict[str, Any], secret: str
) -> list[NormalizedRow]:
    stored = conn.execute(
        "select row_number, raw from public.batch_rows where batch_id = %s order by row_number",
        (batch["id"],),
    ).fetchall()
    mapping = batch["column_mapping"] or {}
    return [normalize_row(r["raw"], mapping, r["row_number"], secret) for r in stored]


def _store_findings(conn: psycopg.Connection, batch_id: Any, findings: list[Finding]) -> None:
    conn.execute("delete from public.validation_issues where batch_id = %s", (batch_id,))
    if not findings:
        return
    records = [
        {
            "row_number": f.row_number,
            "rule_code": f.rule_code.value,
            "severity": f.severity,
            "details": f.evidence,
            "message": f.message,
        }
        for f in findings
    ]
    conn.execute(
        """
        insert into public.validation_issues
          (batch_id, row_number, rule_code, severity, details, message)
        select %s, x.row_number, x.rule_code, x.severity::public.issue_severity, x.details,
               x.message
        from jsonb_to_recordset(%s)
          as x(row_number int, rule_code text, severity text, details jsonb, message text)
        """,
        (batch_id, Jsonb(records)),
    )


def _store_rows(
    conn: psycopg.Connection, batch_id: Any, rows: list[NormalizedRow], statuses: dict[int, str]
) -> None:
    records = [
        {"row_number": r.row_number, "normalized": r.to_json(), "status": statuses[r.row_number]}
        for r in rows
    ]
    conn.execute(
        """
        update public.batch_rows b set normalized = x.normalized, status = x.status
        from jsonb_to_recordset(%s) as x(row_number int, normalized jsonb, status text)
        where b.batch_id = %s and b.row_number = x.row_number
        """,
        (Jsonb(records), batch_id),
    )


def _save_counts(
    conn: psycopg.Connection,
    batch_id: Any,
    counts: dict[str, int],
    extra: str = "",
    extra_params: tuple = (),
) -> dict[str, Any]:
    return conn.execute(
        f"""
        update public.batches set counts = %s, rows_total = %s, rows_error = %s,
          rows_warning = %s, rows_review = %s, rows_info = %s{extra}
        where id = %s returning *
        """,
        (
            Jsonb(counts),
            counts["rows_total"],
            counts["errors"],
            counts["warnings"],
            counts["review"],
            counts["info"],
            *extra_params,
            batch_id,
        ),
    ).fetchone()


def validate(
    conn: psycopg.Connection, batch: dict[str, Any], settings: Settings, user: User
) -> dict[str, Any]:
    """Normalise every stored row, run all rules and store the findings."""
    secret = require_secret(settings)
    rows = _normalized(conn, batch, secret)
    ctx = validation_context(conn, str(batch["institution_id"]), settings)
    findings = validate_rows(rows, ctx, settings.blind_match_secret)
    errors = error_rows(findings)
    statuses = {r.row_number: "error" if r.row_number in errors else "valid" for r in rows}
    _store_rows(conn, batch["id"], rows, statuses)
    _store_findings(conn, batch["id"], findings)
    counts = count_findings(len(rows), findings)
    batch = _save_counts(conn, batch["id"], counts, ", status = 'validated'")
    audit_store.append_event(
        conn, user.id, "batch.validated", "batch", batch["id"], {"counts": counts}
    )
    return batch


def issues(conn: psycopg.Connection, batch_id: str, user: User) -> list[dict[str, Any]]:
    load_batch(conn, batch_id, user)
    rows = conn.execute(
        """
        select id, batch_id, row_number, rule_code, severity::text as severity,
               coalesce(message, '') as message, details, resolved
        from public.validation_issues where batch_id = %s order by row_number, rule_code
        """,
        (batch_id,),
    ).fetchall()
    return [{**r, "batch_id": str(r["batch_id"])} for r in rows]


# ---------------------------------------------------------------------------- commit
_STUDENT_COLUMNS = (
    "apaar_id text, provisional_id text, full_name text, dob date, gender text, category text,"
    " pwd boolean, nationality text, oci_status boolean, fn_status boolean, contact_hash text,"
    " email_hash text, opted_out boolean, guardian_name text, domicile_state text"
)


def _student_record(row: NormalizedRow) -> dict[str, Any]:
    v = row.to_json()["values"]
    apaar = v.get("apaar_id") or None
    return {
        "apaar_id": apaar,
        "provisional_id": None if apaar else v.get("provisional_id"),
        "full_name": v["student_name"],
        "dob": v["dob"],
        "gender": v["gender"],
        "category": v["category"],
        "pwd": bool(v.get("pwd")),
        "nationality": v.get("nationality") or "IN",
        "oci_status": bool(v.get("oci_status")),
        "fn_status": bool(v.get("fn_status")),
        "contact_hash": v.get("contact_phone"),
        "email_hash": v.get("contact_email"),
        "opted_out": bool(v.get("apaar_opt_out")),
        "guardian_name": v.get("guardian_name"),
        "domicile_state": v.get("domicile_state"),
    }


def _upsert_students(conn: psycopg.Connection, rows: list[NormalizedRow]) -> dict[int, str]:
    """Insert new students (existing ones are left unchanged); return row -> student id."""
    records = [_student_record(r) for r in rows]
    if not records:
        return {}
    conn.execute(
        f"""
        insert into public.students
          (apaar_id, provisional_id, full_name, dob, gender, category, pwd, nationality,
           oci_status, fn_status, contact_hash, email_hash, opted_out, guardian_name,
           domicile_state)
        select apaar_id, provisional_id, full_name, dob, gender, category, pwd, nationality,
               oci_status, fn_status, contact_hash, email_hash, opted_out, guardian_name,
               domicile_state
        from jsonb_to_recordset(%s) as x({_STUDENT_COLUMNS})
        on conflict do nothing
        """,
        (Jsonb(records),),
    )
    apaars = [r["apaar_id"] for r in records if r["apaar_id"]]
    provisionals = [r["provisional_id"] for r in records if r["provisional_id"]]
    found = conn.execute(
        "select id, apaar_id, provisional_id from public.students"
        " where apaar_id = any(%s) or provisional_id = any(%s)",
        (apaars, provisionals),
    ).fetchall()
    by_apaar = {f["apaar_id"]: str(f["id"]) for f in found if f["apaar_id"]}
    by_prov = {f["provisional_id"]: str(f["id"]) for f in found if f["provisional_id"]}
    return {
        row.row_number: by_apaar[rec["apaar_id"]]
        if rec["apaar_id"]
        else by_prov[rec["provisional_id"]]
        for row, rec in zip(rows, records, strict=True)
    }


def lock_pools(
    conn: psycopg.Connection, institution_id: str, years: list[str]
) -> dict[PoolKey, dict[str, Any]]:
    """Lock the institution's seat pools for these years; the latest rule_version wins."""
    conn.execute("select pg_advisory_xact_lock(hashtext('seat_ledger:' || %s))", (institution_id,))
    rows = conn.execute(
        """
        select sp.id, sp.programme_id, sp.academic_year, sp.pool::text as pool,
               sp.approved_seats, sp.rule_version
        from public.seat_pools sp
        join public.programmes p on p.id = sp.programme_id
        where p.institution_id = %s and sp.academic_year = any(%s)
        order by sp.rule_version
        for update of sp
        """,
        (institution_id, years),
    ).fetchall()
    return {(str(r["programme_id"]), r["academic_year"], r["pool"]): r for r in rows}


def used_seats(
    conn: psycopg.Connection, programme_ids: list[str], years: list[str]
) -> Counter[PoolKey]:
    rows = conn.execute(
        """
        select programme_id, academic_year, pool::text as pool, count(*) as used
        from public.admissions
        where active and programme_id = any(%s::uuid[]) and academic_year = any(%s)
        group by 1, 2, 3
        """,
        (programme_ids, years),
    ).fetchall()
    return Counter(
        {(str(r["programme_id"]), r["academic_year"], r["pool"]): r["used"] for r in rows}
    )


def _create_case(
    conn: psycopg.Connection, kind: str, institution_id: str, title: str, evidence: dict
) -> dict[str, Any]:
    return conn.execute(
        """
        insert into public.review_cases (kind, institution_id, title, evidence)
        values (%s, %s, %s, %s) returning id, kind, institution_id, status, created_at
        """,
        (kind, institution_id, title, Jsonb(evidence)),
    ).fetchone()


def case_created_event(case: dict[str, Any]) -> Event:
    return (
        "review_case.created",
        {
            "case_id": str(case["id"]),
            "kind": case["kind"],
            "institution_id": str(case["institution_id"]),
            "status": case["status"],
            "created_at": case["created_at"].isoformat(),
        },
    )


def _overrun_case(
    conn: psycopg.Connection,
    user: User,
    institution_id: str,
    key: PoolKey,
    evidence: dict[str, Any],
    created: list[str],
) -> Event:
    """Open one intake_overrun case per pool, or refresh the pool's open case."""
    existing = conn.execute(
        """
        select id from public.review_cases
        where kind = 'intake_overrun' and status = 'open' and institution_id = %s
          and evidence->>'programme_id' = %s and evidence->>'academic_year' = %s
          and evidence->>'pool' = %s
        for update
        """,
        (institution_id, *key),
    ).fetchone()
    if existing:
        updated = conn.execute(
            "update public.review_cases set evidence = %s, updated_at = now()"
            " where id = %s returning id, status, updated_at",
            (Jsonb(evidence), existing["id"]),
        ).fetchone()
        audit_store.append_event(
            conn,
            user.id,
            "review_case.updated",
            "review_case",
            updated["id"],
            {"overrun_by": evidence["overrun_by"]},
        )
        return (
            "review_case.updated",
            {
                "case_id": str(updated["id"]),
                "status": updated["status"],
                "updated_at": updated["updated_at"].isoformat(),
            },
        )
    title = (
        f"{evidence['programme']} {key[2]} pool overrun: {evidence['used']} admitted against"
        f" {evidence['approved']} approved ({key[1]})"
    )
    case = _create_case(conn, "intake_overrun", institution_id, title, evidence)
    created.append(str(case["id"]))
    audit_store.append_event(
        conn,
        user.id,
        "review_case.created",
        "review_case",
        case["id"],
        {"kind": "intake_overrun", "overrun_by": evidence["overrun_by"]},
    )
    return case_created_event(case)


def commit(
    conn: psycopg.Connection, batch_id: str, user: User, settings: Settings
) -> tuple[dict[str, Any], list[Event]]:
    """Commit a validated batch inside the caller's transaction. Idempotent."""
    batch = load_batch(conn, batch_id, user, lock=True)
    if batch["status"] == "committed":
        return batch["commit_result"], []
    if batch["status"] != "validated":
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Batch is '{batch['status']}'; map and validate it first"
        )
    institution_id = str(batch["institution_id"])
    secret = require_secret(settings)

    # Re-validate inside the transaction so cross-institution checks see current data.
    rows = _normalized(conn, batch, secret)
    findings = validate_rows(
        rows, validation_context(conn, institution_id, settings), settings.blind_match_secret
    )
    errors = error_rows(findings)
    good = [r for r in rows if r.row_number not in errors]

    programmes = {
        r["code"]: str(r["id"])
        for r in conn.execute(
            "select id, code from public.programmes where institution_id = %s",
            (institution_id,),
        ).fetchall()
    }
    years = sorted({r.values["academic_year"] for r in good})
    pools = lock_pools(conn, institution_id, years)
    used = used_seats(conn, list(programmes.values()), years)

    student_ids = _upsert_students(conn, good)
    admissions = []
    for row in good:
        v = row.to_json()["values"]
        admissions.append(
            {
                "row_number": row.row_number,
                "student_id": student_ids[row.row_number],
                "programme_id": programmes[v["programme_code"]],
                "academic_year": v["academic_year"],
                "pool": v["seat_pool"],
                "admission_mode": v["admission_mode"],
                "admission_date": v["admission_date"],
                "qualifying_exam_pct": v["qualifying_exam_pct"],
                "qualifying_exam": v.get("qualifying_exam"),
            }
        )
    inserted = conn.execute(
        """
        insert into public.admissions
          (student_id, programme_id, academic_year, pool, admission_mode, admission_date,
           qualifying_exam_pct, qualifying_exam, status, batch_id)
        select x.student_id, x.programme_id, x.academic_year, x.pool::public.seat_pool,
               x.admission_mode, x.admission_date, x.qualifying_exam_pct, x.qualifying_exam,
               'submitted', %s
        from jsonb_to_recordset(%s) as x(row_number int, student_id uuid, programme_id uuid,
             academic_year text, pool text, admission_mode text, admission_date date,
             qualifying_exam_pct numeric, qualifying_exam text)
        order by x.row_number
        on conflict (student_id, programme_id, academic_year) where active do nothing
        returning student_id, programme_id, academic_year
        """,
        (batch["id"], Jsonb(admissions)),
    ).fetchall()
    inserted_keys = {
        (str(r["student_id"]), str(r["programme_id"]), r["academic_year"]) for r in inserted
    }
    committed = [
        a
        for a in admissions
        if (a["student_id"], a["programme_id"], a["academic_year"]) in inserted_keys
    ]
    committed_numbers = {a["row_number"] for a in committed}
    skipped = {a["row_number"] for a in admissions} - committed_numbers

    # Seat Ledger: admissions are recorded and flagged, never dropped. Every row past the
    # approved seats of its pool gets INTAKE_OVERRUN, and each such pool one review case.
    running = Counter(used)
    overrun_rows: dict[PoolKey, list[int]] = defaultdict(list)
    for a in committed:
        key = (a["programme_id"], a["academic_year"], a["pool"])
        running[key] += 1
        if running[key] > (pools[key]["approved_seats"] if key in pools else 0):
            overrun_rows[key].append(a["row_number"])

    events: list[Event] = []
    created: list[str] = []
    code_by_id = {pid: code for code, pid in programmes.items()}
    for key, numbers in overrun_rows.items():
        pool = pools.get(key)
        approved = pool["approved_seats"] if pool else 0
        evidence = {
            "programme": code_by_id[key[0]],
            "programme_id": key[0],
            "academic_year": key[1],
            "pool": key[2],
            "approved": approved,
            "used": running[key],
            "overrun_by": running[key] - approved,
            "rule_version": pool["rule_version"] if pool else None,
            "batch_id": str(batch["id"]),
        }
        findings += [
            Finding(
                n,
                RuleCode.INTAKE_OVERRUN,
                "Committing this row exceeds the approved seats of its pool.",
                {k: evidence[k] for k in ("programme", "academic_year", "pool", "approved")},
            )
            for n in numbers
        ]
        events.append(_overrun_case(conn, user, institution_id, key, evidence, created))

    for f in [f for f in findings if f.rule_code is RuleCode.DUP_CROSS_INSTITUTION]:
        evidence = {
            "rule_code": f.rule_code.value,
            "batch_id": str(batch["id"]),
            "row_number": f.row_number,
            **f.evidence,
        }
        case = _create_case(
            conn, "signal", institution_id, "APAAR ID enrolled at another institution", evidence
        )
        created.append(str(case["id"]))
        audit_store.append_event(
            conn,
            user.id,
            "review_case.created",
            "review_case",
            case["id"],
            {"kind": "signal", "rule_code": f.rule_code.value},
        )
        events.append(case_created_event(case))

    findings.sort(key=lambda f: (f.row_number, f.rule_code.value))
    _store_findings(conn, batch["id"], findings)
    statuses = {
        r.row_number: "committed"
        if r.row_number in committed_numbers
        else ("skipped" if r.row_number in skipped else "error")
        for r in rows
    }
    _store_rows(conn, batch["id"], rows, statuses)
    result = {
        "batch_id": str(batch["id"]),
        "status": "committed",
        "rows_committed": len(committed),
        "rows_rejected": len(errors),
        "rows_skipped_existing": len(skipped),
        "review_cases_created": created,
    }
    committed_at = datetime.now(UTC)
    _save_counts(
        conn,
        batch["id"],
        count_findings(len(rows), findings),
        ", status = 'committed', commit_result = %s, committed_at = %s",
        (Jsonb(result), committed_at),
    )
    audit_store.append_event(
        conn,
        user.id,
        "batch.committed",
        "batch",
        batch["id"],
        {k: result[k] for k in ("rows_committed", "rows_rejected", "rows_skipped_existing")},
    )
    events.insert(
        0,
        (
            "batch.committed",
            {
                "batch_id": str(batch["id"]),
                "institution_id": institution_id,
                "rows_committed": result["rows_committed"],
                "rows_rejected": result["rows_rejected"],
                "committed_at": committed_at.isoformat(),
            },
        ),
    )
    return result, events
