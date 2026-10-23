# Owner: Dev A
"""FastAPI router for engine endpoints."""

from __future__ import annotations

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
