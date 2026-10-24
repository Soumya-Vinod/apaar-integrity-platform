# Owner: Dev B
"""Integrity results table for Dev A's compute job (shared/integrity-results.md).

save_results upserts one row per (institution_id, academic_year, model_version);
latest_for reads the most recently computed row for an institution and year.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

REQUIRED = ("institution_id", "academic_year", "score", "tier", "model_version")
_COLUMNS = (
    "institution_id, academic_year, score, tier, components, top_features, signals,"
    " model_version, computed_at"
)


def _check(result: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED if result.get(k) in (None, "")]
    if missing:
        raise ValueError(f"integrity result is missing {missing}")


def save_results(conn: psycopg.Connection, results: list[dict[str, Any]]) -> int:
    """Upsert results inside the caller's transaction. Returns the number of rows written."""
    for result in results:
        _check(result)
    now = datetime.now(UTC)
    rows = [
        (
            str(r["institution_id"]),
            r["academic_year"],
            r["score"],
            r["tier"],
            Jsonb(r.get("components") or {}),
            Jsonb(r.get("top_features") or []),
            Jsonb(r.get("signals") or []),
            r["model_version"],
            r.get("computed_at") or now,
        )
        for r in results
    ]
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            f"""
            insert into public.integrity_scores ({_COLUMNS})
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (institution_id, academic_year, model_version) do update set
              score = excluded.score, tier = excluded.tier, components = excluded.components,
              top_features = excluded.top_features, signals = excluded.signals,
              computed_at = excluded.computed_at
            """,
            rows,
        )
    return len(rows)


def latest_for(
    conn: psycopg.Connection, institution_id: str, academic_year: str
) -> dict[str, Any] | None:
    """The most recently computed result for this institution and year, any model version."""
    row = conn.execute(
        f"""
        select {_COLUMNS} from public.integrity_scores
        where institution_id = %s and academic_year = %s
        order by computed_at desc limit 1
        """,
        (institution_id, academic_year),
    ).fetchone()
    if row is None:
        return None
    return {**row, "institution_id": str(row["institution_id"]), "score": float(row["score"])}
