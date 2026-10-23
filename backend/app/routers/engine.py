# Owner: Dev A
"""Engine endpoints for metadata, health, and blind match."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.engine import (
    BlindMatchRequest,
    BlindMatchStudentInput,
    EngineHealth,
    EngineInfo,
    MatchCase,
    Signal,
    SignalsRequest,
)

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


@router.post("/blind-match", response_model=list[MatchCase])
def post_blind_match(
    body: BlindMatchRequest | list[BlindMatchStudentInput],
    settings: Settings = Depends(get_settings),
) -> list[MatchCase]:
    """Execute in-memory privacy-preserving blind match and exact APAAR duplicate detection."""
    from engine.blind_match import BlindMatchService, StudentRecord

    raw_records = body.records if isinstance(body, BlindMatchRequest) else body
    threshold = (
        body.threshold
        if isinstance(body, BlindMatchRequest) and body.threshold is not None
        else settings.match_threshold
    )

    students = [
        StudentRecord(
            student_id=r.student_id,
            institution_id=r.institution_id,
            student_name=r.student_name,
            dob=r.dob,
            father_name=r.father_name,
            mother_name=r.mother_name,
            apaar_id=r.apaar_id,
        )
        for r in raw_records
    ]

    service = BlindMatchService(
        secret=settings.blind_match_secret or None,
        threshold=threshold,
    )
    matches = service.run_blind_match(students, threshold=threshold)

    return [
        MatchCase(
            case_id=m.case_id,
            institution_a=m.institution_a,
            institution_b=m.institution_b,
            student_a_id=m.student_a_id,
            student_b_id=m.student_b_id,
            similarity_score=m.similarity_score,
            confidence=m.confidence,
            matched_fields=m.matched_fields,
            status=m.status,
            created_at=m.created_at,
        )
        for m in matches
    ]


@router.post("/signals", response_model=list[Signal])
def post_signals(
    body: SignalsRequest | dict[str, Any] | list[dict[str, Any]],
) -> list[Signal]:
    """Execute rule-based integrity signals against institution data."""
    from engine.signals import execute_signals

    if isinstance(body, SignalsRequest):
        payload: dict[str, Any] = body.model_dump()
    elif isinstance(body, (dict, list)):
        payload = body
    else:
        payload = {}

    signals = execute_signals(payload)

    return [
        Signal(
            signal_id=s.signal_id,
            institution_id=s.institution_id,
            signal_name=s.signal_name,
            severity=s.severity,
            score=s.score,
            evidence=s.evidence,
            description=s.description,
            created_at=s.created_at,
        )
        for s in signals
    ]
