# Owner: Dev B
"""Bridges committed data to the engine for signals, anomaly ranking and Integrity Score."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import psycopg
from engine.anomaly.features import InstitutionFeatureExtractor
from engine.anomaly.service import AnomalyDetectionService
from engine.scoring.service import IntegrityScoringService
from engine.types import MatchCase, Signal

from app.core.config import get_settings
from app.core.db import transaction
from app.services import integrity_store


def compute_institution_results(
    conn: psycopg.Connection,
    academic_year: str = "2026-27",
    institution_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Compute integrity scores for institutions from committed database data."""
    settings = get_settings()

    if institution_ids:
        inst_rows = conn.execute(
            "select id, aicte_code, name, state from public.institutions where id = any(%s::uuid[])"
            " order by aicte_code",
            (institution_ids,),
        ).fetchall()
    else:
        inst_rows = conn.execute(
            "select id, aicte_code, name, state from public.institutions order by aicte_code"
        ).fetchall()

    if not inst_rows:
        return []

    institutions_data: list[dict[str, Any]] = []
    for inst in inst_rows:
        inst_id = str(inst["id"])

        admissions = conn.execute(
            """
            select * from public.admissions
            where institution_id = %s and academic_year = %s and active
            """,
            (inst_id, academic_year),
        ).fetchall()

        review_cases = conn.execute(
            "select * from public.review_cases where institution_id = %s",
            (inst_id,),
        ).fetchall()

        seat_pools = conn.execute(
            """
            select sp.pool, sp.approved_seats, sp.academic_year
            from public.seat_pools sp
            join public.programmes p on p.id = sp.programme_id
            where p.institution_id = %s and sp.academic_year = %s
            """,
            (inst_id, academic_year),
        ).fetchall()

        blind_match_rows = conn.execute(
            """
            select * from public.blind_match_pairs
            where institution_a = %s or institution_b = %s
            """,
            (inst_id, inst_id),
        ).fetchall()

        signals: list[Signal] = []
        for rc in review_cases:
            ev = rc.get("evidence") if isinstance(rc.get("evidence"), dict) else {}
            code = str(ev.get("rule_code") or rc.get("kind", "").upper())
            signals.append(
                Signal(
                    code=code,
                    institution_id=inst_id,
                    severity="review"
                    if rc.get("kind") in ("overrun", "blind_match")
                    else "warning",
                    evidence=ev,
                    description=str(rc.get("title") or ""),
                )
            )

        blind_matches: list[MatchCase] = []
        for bm in blind_match_rows:
            blind_matches.append(
                MatchCase(
                    institution_a=str(bm["institution_a"]),
                    institution_b=str(bm["institution_b"]),
                    student_a_id=str(bm["student_a_id"]),
                    student_b_id=str(bm["student_b_id"]),
                    similarity_score=float(bm.get("similarity_score") or 1.0),
                    confidence=float(bm.get("similarity_score") or 1.0),
                )
            )

        institutions_data.append(
            {
                "institution_id": inst_id,
                "inst": inst,
                "admissions": [dict(a) for a in admissions],
                "signals": signals,
                "seat_pools": [dict(sp) for sp in seat_pools],
                "blind_matches": blind_matches,
            }
        )

    extractor = InstitutionFeatureExtractor()
    feature_vectors = [
        extractor.extract(d["institution_id"], d) for d in institutions_data
    ]

    anomaly_service = AnomalyDetectionService()
    try:
        anomaly_service.fit(feature_vectors)
        anomaly_results = anomaly_service.predict(feature_vectors)
        anomaly_by_id = {a.institution_id: a for a in anomaly_results}
    except Exception:
        anomaly_by_id = {}

    scoring_service = IntegrityScoringService()
    computed_results: list[dict[str, Any]] = []
    now = datetime.now(UTC)

    for idx, item in enumerate(institutions_data):
        inst_id = item["institution_id"]
        anomaly_res = anomaly_by_id.get(inst_id)
        score_res = scoring_service.calculate(
            institution_id=inst_id,
            signals=item["signals"],
            anomaly=anomaly_res,
            blind_matches=item["blind_matches"],
        )

        anomaly_score = float(anomaly_res.score) if anomaly_res else 0.0

        top_features: list[dict[str, Any]] = []
        if anomaly_res and getattr(anomaly_res, "top_features", None):
            feat_dict = feature_vectors[idx].to_dict()
            for feat_name in anomaly_res.top_features:
                val = float(feat_dict.get(feat_name, 0.0))
                top_features.append(
                    {
                        "name": feat_name,
                        "value": val,
                        "peer_median": val,
                    }
                )

        signals_out = [
            {
                "code": s.code,
                "severity": s.severity,
                "evidence": s.evidence,
            }
            for s in item["signals"]
        ]

        computed_results.append(
            {
                "institution_id": inst_id,
                "academic_year": academic_year,
                "score": float(score_res.score),
                "tier": str(score_res.risk_level),
                "model_version": settings.model_version,
                "components": {
                    **{k: float(v) for k, v in score_res.components.items()},
                    "anomaly_score": round(anomaly_score, 2),
                    "anomaly": round(anomaly_score, 2),
                },
                "top_features": top_features,
                "signals": signals_out,
                "computed_at": now,
            }
        )

    return computed_results


def compute_and_save_integrity(
    conn: psycopg.Connection,
    results: list[dict[str, Any]] | None = None,
    academic_year: str = "2026-27",
) -> int:
    """Store computed results via integrity_store.save_results (computing if not provided)."""
    if results is None:
        results = compute_institution_results(conn, academic_year=academic_year)
    return integrity_store.save_results(conn, results)


def compute_rankings(
    conn: psycopg.Connection | None = None,
    academic_year: str = "2026-27",
) -> list[dict[str, Any]]:
    """Build InstitutionFeatures, call engine.anomaly and engine.scoring, persist results."""
    if conn is not None:
        results = compute_institution_results(conn, academic_year=academic_year)
        compute_and_save_integrity(conn, results=results, academic_year=academic_year)
        return integrity_store.latest_rankings(conn, academic_year=academic_year)
    with transaction() as c:
        results = compute_institution_results(c, academic_year=academic_year)
        compute_and_save_integrity(c, results=results, academic_year=academic_year)
        return integrity_store.latest_rankings(c, academic_year=academic_year)

