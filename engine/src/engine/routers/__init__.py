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


@router.post("/signals")
def post_signals(body: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Standalone in-memory integrity signals endpoint."""
    from engine.signals import execute_signals

    signals = execute_signals(body)
    return [
        {
            "signal_id": s.signal_id,
            "institution_id": s.institution_id,
            "signal_name": s.signal_name,
            "severity": s.severity,
            "score": s.score,
            "evidence": s.evidence,
            "description": s.description,
            "created_at": s.created_at.isoformat(),
        }
        for s in signals
    ]


@router.post("/anomaly")
def post_anomaly(
    body: dict[str, Any] | list[dict[str, Any]],
) -> dict[str, Any] | list[dict[str, Any]]:
    """Standalone in-memory ML anomaly detection endpoint."""
    from fastapi import HTTPException

    from engine.anomaly.service import AnomalyDetectionService

    if not isinstance(body, (list, dict)):
        raise HTTPException(status_code=400, detail="Request body must be a dict or list.")

    if not body:
        return []

    is_single = False
    if isinstance(body, list):
        items: list[dict[str, Any]] = body
    else:
        if "institutions" in body and isinstance(body["institutions"], list):
            items = body["institutions"]
        elif "features" in body and isinstance(body["features"], list):
            items = body["features"]
        else:
            items = [body]
            is_single = True

    if not items:
        return []

    service = AnomalyDetectionService()
    try:
        results = service.fit_predict(items)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Anomaly detection failed: {exc}") from exc

    serialized = [
        {
            "institution_id": r.institution_id,
            "score": r.score,
            "prediction": r.prediction,
            "top_features": r.top_features,
            "feature_vector": r.feature_vector,
        }
        for r in results
    ]

    return serialized[0] if is_single and serialized else serialized


@router.post("/integrity-score")
def post_integrity_score(
    body: dict[str, Any] | list[dict[str, Any]],
) -> dict[str, Any] | list[dict[str, Any]]:
    """Standalone in-memory Institution Integrity Score endpoint."""
    from fastapi import HTTPException

    from engine.scoring.service import IntegrityScoringService

    if not isinstance(body, (list, dict)) or not body:
        raise HTTPException(status_code=400, detail="Institution data cannot be empty.")

    if isinstance(body, list):
        service = IntegrityScoringService()
        return [
            {
                "institution_id": s.institution_id,
                "score": s.score,
                "components": s.components,
                "risk_level": s.risk_level,
                "generated_at": s.generated_at.isoformat(),
                "signals": [
                    {
                        "signal_id": sig.signal_id,
                        "institution_id": sig.institution_id,
                        "signal_name": sig.signal_name,
                        "severity": sig.severity,
                        "score": sig.score,
                        "evidence": sig.evidence,
                        "description": sig.description,
                        "created_at": sig.created_at.isoformat(),
                    }
                    for sig in s.signals
                ],
            }
            for s in service.calculate_batch(body)
        ]

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a dict or list.")

    if not body:
        raise HTTPException(status_code=400, detail="Institution data cannot be empty.")

    service = IntegrityScoringService()
    try:
        score_res = service.calculate_from_data(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Scoring calculation failed: {exc}") from exc

    return {
        "institution_id": score_res.institution_id,
        "score": score_res.score,
        "components": score_res.components,
        "risk_level": score_res.risk_level,
        "generated_at": score_res.generated_at.isoformat(),
        "signals": [
            {
                "signal_id": sig.signal_id,
                "institution_id": sig.institution_id,
                "signal_name": sig.signal_name,
                "severity": sig.severity,
                "score": sig.score,
                "evidence": sig.evidence,
                "description": sig.description,
                "created_at": sig.created_at.isoformat(),
            }
            for sig in score_res.signals
        ],
    }


@router.post("/evaluate")
def post_evaluate(
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute complete in-memory evaluation harness and benchmarking."""
    from fastapi import HTTPException

    from engine.evaluation.datasets import EvaluationDataset
    from engine.evaluation.service import EvaluationService

    if body is not None and not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request payload must be a JSON object.")

    try:
        if not body:
            dataset = EvaluationDataset.create_synthetic_benchmark_dataset()
        else:
            dataset = EvaluationDataset.from_dict(body)

        service = EvaluationService()
        report = service.run_full_evaluation(dataset)
        return report.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Evaluation failed: {exc}") from exc
