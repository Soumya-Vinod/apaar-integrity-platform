# Owner: Dev A
from datetime import datetime

from app.core.config import Settings
from app.models.engine import IntegrityScore, MatchCase, Signal


def test_engine_info_endpoint(client):
    response = client.get("/engine")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Integrity Intelligence Engine"
    assert data["status"] == "active"
    assert "version" in data
    assert "match_threshold" in data
    assert "model_version" in data


def test_engine_health_endpoint(client):
    response = client.get("/engine/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["engine_ok"] is True
    assert "version" in data


def test_settings_engine_defaults():
    settings = Settings()
    assert settings.match_threshold == 0.85
    assert settings.model_version == "0.1.0"


def test_match_case_pydantic_model():
    case = MatchCase(
        institution_a="inst-a",
        institution_b="inst-b",
        student_a_id="stud-a",
        student_b_id="stud-b",
        similarity_score=0.95,
        confidence=0.90,
        matched_fields=["name", "father_name", "dob"],
        status="open",
    )
    assert case.institution_a == "inst-a"
    assert case.similarity_score == 0.95
    assert case.confidence == 0.90
    assert case.case_id is not None
    assert isinstance(case.created_at, datetime)


def test_signal_pydantic_model():
    sig = Signal(
        institution_id="inst-a",
        signal_name="CROSS_INSTITUTION_DUPLICATE",
        severity="error",
        score=90.0,
        evidence={"details": "same student in two institutions"},
        description="Duplicate enrolment across institutions",
    )
    assert sig.institution_id == "inst-a"
    assert sig.signal_name == "CROSS_INSTITUTION_DUPLICATE"
    assert sig.severity == "error"
    assert sig.score == 90.0
    assert sig.signal_id is not None
    assert isinstance(sig.created_at, datetime)


def test_integrity_score_pydantic_model():
    sig = Signal(
        institution_id="inst-a",
        signal_name="INTAKE_OVERRUN",
        severity="review",
    )
    score = IntegrityScore(
        institution_id="inst-a",
        score=85.0,
        risk_level="medium",
        signals=[sig],
    )
    assert score.institution_id == "inst-a"
    assert score.score == 85.0
    assert score.risk_level == "medium"
    assert len(score.signals) == 1
    assert isinstance(score.generated_at, datetime)
