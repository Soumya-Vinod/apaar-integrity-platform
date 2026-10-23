# Owner: Dev A
"""Engine endpoints for metadata and health."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.engine import EngineHealth, EngineInfo

router = APIRouter(prefix="/engine", tags=["engine"])


@router.get("", response_model=EngineInfo)
def get_engine(settings: Settings = Depends(get_settings)) -> EngineInfo:
    """Return engine metadata and configuration."""
    return EngineInfo(
        name="Integrity Intelligence Engine",
        version=settings.model_version,
        status="active",
        match_threshold=settings.match_threshold,
        model_version=settings.model_version,
    )


@router.get("/health", response_model=EngineHealth)
def get_engine_health(settings: Settings = Depends(get_settings)) -> EngineHealth:
    """Return engine health and import status."""
    try:
        import engine

        engine_ok = True
        version = getattr(engine, "__version__", settings.model_version)
    except ImportError:
        engine_ok = False
        version = settings.model_version

    return EngineHealth(
        status="ok",
        version=version,
        engine_ok=engine_ok,
    )
