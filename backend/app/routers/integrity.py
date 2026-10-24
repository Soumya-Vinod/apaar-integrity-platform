# Owner: Dev A
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.datasource import source
from app.core.db import transaction
from app.core.security import require_roles
from app.mocks import mock, not_found
from app.models.integrity import IntegrityDetail, IntegrityRanking
from app.services import integrity_store

router = APIRouter(
    prefix="/integrity",
    tags=["integrity"],
    dependencies=[Depends(require_roles("aicte_admin", "auditor"))],
)

REAL = source("integrity")


def _format_detail(row: dict[str, Any]) -> dict[str, Any]:
    comps = row.get("components") or {}
    anomaly_score = float(
        comps.get("anomaly_score")
        or (
            comps.get("anomaly")
            if (0.0 <= float(comps.get("anomaly", 0.0)) <= 1.0)
            else 0.0
        )
        or 0.0
    )

    raw_features = row.get("top_features") or []
    top_features = []
    for f in raw_features:
        if isinstance(f, dict):
            name = str(f.get("name") or f.get("feature") or "")
            val = float(f.get("value", 0.0))
            med = float(f.get("peer_median") or f.get("median") or f.get("contribution") or 0.0)
            top_features.append({"name": name, "value": val, "peer_median": med})

    raw_signals = row.get("signals") or []
    signals = []
    for s in raw_signals:
        if isinstance(s, dict):
            signals.append(
                {
                    "code": str(s.get("code") or s.get("signal_name") or ""),
                    "severity": s.get("severity") or "review",
                    "evidence": s.get("evidence") if isinstance(s.get("evidence"), dict) else {},
                }
            )

    formatted_components: dict[str, float] = {}
    for k, v in comps.items():
        try:
            formatted_components[k] = float(v)
        except (ValueError, TypeError):
            continue

    return {
        "institution_id": str(row["institution_id"]),
        "integrity_score": float(row["score"]),
        "components": formatted_components,
        "signals": signals,
        "anomaly": {
            "score": round(anomaly_score, 2),
            "top_features": top_features,
        },
    }


@router.get("/institutions", response_model=list[IntegrityRanking])
def ranked_institutions(real: bool = Depends(REAL)) -> list[dict]:
    """Institutions ranked most anomalous first."""
    if real:
        with transaction() as conn:
            return integrity_store.latest_rankings(conn)
    return mock("integrity_ranking")


@router.get("/institutions/{institution_id}", response_model=IntegrityDetail)
def institution_integrity(institution_id: str, real: bool = Depends(REAL)) -> dict:
    """Signals and anomaly explanation for one institution."""
    if real:
        with transaction() as conn:
            row = integrity_store.latest_for(conn, institution_id)
        if row is None:
            raise not_found("Institution", institution_id)
        return _format_detail(row)
    detail = mock("integrity_details").get(institution_id)
    if detail is None:
        raise not_found("Institution", institution_id)
    return detail

