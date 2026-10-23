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


def test_post_blind_match_api_exact_apaar(client):
    payload = {
        "records": [
            {
                "student_id": "stud-1",
                "institution_id": "inst-1",
                "student_name": "Aarav Sharma",
                "dob": "2004-05-15",
                "apaar_id": "999900001111",
            },
            {
                "student_id": "stud-2",
                "institution_id": "inst-2",
                "student_name": "Aarav Sharma",
                "dob": "2004-05-15",
                "apaar_id": "999900001111",
            },
        ]
    }
    response = client.post("/engine/blind-match", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    match = data[0]
    assert match["institution_a"] == "inst-1"
    assert match["institution_b"] == "inst-2"
    assert match["similarity_score"] == 1.0
    assert match["confidence"] == 1.0
    assert "apaar_id" in match["matched_fields"]


def test_post_blind_match_api_fuzzy_matching(client):
    payload = {
        "records": [
            {
                "student_id": "stud-a",
                "institution_id": "inst-1",
                "student_name": "Priyanka Joshi",
                "dob": "2004-07-20",
                "father_name": "Kailash Joshi",
                "mother_name": "Meena Joshi",
            },
            {
                "student_id": "stud-b",
                "institution_id": "inst-2",
                "student_name": "Priyanka Joshi",
                "dob": "2004-07-20",
                "father_name": "Kailash Joshi",
                "mother_name": "Meena Joshi",
            },
            {
                "student_id": "stud-c",
                "institution_id": "inst-3",
                "student_name": "Harsh Patel",
                "dob": "2004-07-20",
                "father_name": "Nitin Patel",
                "mother_name": "Rita Patel",
            },
        ],
        "threshold": 0.85,
    }
    response = client.post("/engine/blind-match", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["student_a_id"] == "stud-a"
    assert data[0]["student_b_id"] == "stud-b"
    assert data[0]["similarity_score"] >= 0.85


def test_post_blind_match_api_direct_list(client):
    records = [
        {
            "student_id": "stud-x",
            "institution_id": "inst-1",
            "student_name": "Vikram Seth",
            "dob": "2004-03-12",
            "apaar_id": "999955554444",
        },
        {
            "student_id": "stud-y",
            "institution_id": "inst-2",
            "student_name": "Vikram Seth",
            "dob": "2004-03-12",
            "apaar_id": "999955554444",
        },
    ]
    response = client.post("/engine/blind-match", json=records)
    assert response.status_code == 200
    assert len(response.json()) == 1
