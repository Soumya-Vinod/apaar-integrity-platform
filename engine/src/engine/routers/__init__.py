# Owner: Dev A
"""FastAPI router for engine endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/engine", tags=["engine"])


@router.get("")
def get_engine() -> dict[str, str]:
    """Engine info endpoint."""
    from engine import __version__

    return {
        "status": "ok",
        "name": "Integrity Intelligence Engine",
        "version": __version__,
    }


@router.get("/health")
def get_engine_health() -> dict[str, str]:
    """Engine health endpoint."""
    from engine import __version__

    return {
        "status": "ok",
        "engine": "active",
        "version": __version__,
    }


@router.post("/blind-match")
def post_blind_match(body: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Standalone in-memory blind match endpoint."""
    from engine.blind_match import BlindMatchService

    records = body.get("records") if isinstance(body, dict) else body
    threshold = body.get("threshold") if isinstance(body, dict) else None
    service = BlindMatchService()
    matches = service.run_blind_match(records or [], threshold=threshold)
    return [
        {
            "case_id": m.case_id,
            "institution_a": m.institution_a,
            "institution_b": m.institution_b,
            "student_a_id": m.student_a_id,
            "student_b_id": m.student_b_id,
            "similarity_score": m.similarity_score,
            "confidence": m.confidence,
            "matched_fields": m.matched_fields,
            "status": m.status,
            "created_at": m.created_at.isoformat(),
        }
        for m in matches
    ]
