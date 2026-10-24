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
    conn: psycopg.Connection, institution_id: str, academic_year: str = "2026-27"
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


def latest_rankings(
    conn: psycopg.Connection, academic_year: str = "2026-27"
) -> list[dict[str, Any]]:
    """Institutions ranked most anomalous first, from the latest computed integrity scores."""
    rows = conn.execute(
        """
        select distinct on (s.institution_id)
            s.institution_id,
            i.name as institution_name,
            i.aicte_code,
            s.score as integrity_score,
            s.tier,
            s.components,
            s.top_features,
            s.signals,
            s.computed_at
        from public.integrity_scores s
        join public.institutions i on i.id = s.institution_id
        where s.academic_year = %s
        order by s.institution_id, s.computed_at desc
        """,
        (academic_year,),
    ).fetchall()
    if not rows:
        return []

    def _extract_anomaly(r: dict[str, Any]) -> float:
        comps = r.get("components") or {}
        if isinstance(comps, dict):
            if "anomaly_score" in comps:
                return float(comps["anomaly_score"])
            if "anomaly" in comps and 0.0 <= float(comps["anomaly"]) <= 1.0:
                return float(comps["anomaly"])
        return 0.0

    sorted_rows = sorted(
        rows,
        key=lambda r: (_extract_anomaly(r), -float(r["integrity_score"])),
        reverse=True,
    )

    rankings: list[dict[str, Any]] = []
    for rank, r in enumerate(sorted_rows, start=1):
        signals = r.get("signals") or []
        top_signals: list[str] = []
        for s in signals:
            if isinstance(s, dict) and "code" in s:
                code = str(s["code"])
                if code not in top_signals:
                    top_signals.append(code)
            elif isinstance(s, str) and s not in top_signals:
                top_signals.append(s)

        rankings.append(
            {
                "rank": rank,
                "institution_id": str(r["institution_id"]),
                "institution_name": r["institution_name"],
                "aicte_code": r["aicte_code"],
                "integrity_score": float(r["integrity_score"]),
                "anomaly_score": round(_extract_anomaly(r), 2),
                "top_signals": top_signals,
            }
        )
    return rankings

