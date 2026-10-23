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


def test_post_signals_api_eligibility(client):
    payload = {
        "admissions": [
            {
                "student_id": "stud-violator",
                "institution_id": "inst-test",
                "programme_code": "BTECH_CSE",
                "category": "general",
                "qualifying_exam_pct": 35.0,  # Below 45% norm
                "dob": "2005-01-01",
                "admission_date": "2023-08-01",
            }
        ]
    }
    response = client.post("/engine/signals", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    sig = data[0]
    assert sig["institution_id"] == "inst-test"
    assert sig["signal_name"] == "ELIGIBILITY_VIOLATION"
    assert sig["score"] >= 70.0
    assert "evidence" in sig
    assert sig["evidence"]["violated_rule"] == "QUALIFYING_BELOW_NORM"


def test_post_signals_api_shared_contacts(client):
    payload = {
        "records": [
            {
                "student_id": "s1",
                "institution_id": "inst-1",
                "contact_phone": "9876543210",
            },
            {
                "student_id": "s2",
                "institution_id": "inst-2",
                "contact_phone": "9876543210",
            },
        ]
    }
    response = client.post("/engine/signals", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(s["signal_name"] == "SHARED_CONTACT_CLUSTER" for s in data)


def test_post_signals_api_backdated(client):
    payload = {
        "admissions": [
            {
                "student_id": "s-delayed",
                "institution_id": "inst-delay",
                "admission_date": "2023-01-01",
                "upload_date": "2023-04-15",
            }
        ]
    }
    response = client.post("/engine/signals", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["signal_name"] == "BACKDATED_ADMISSIONS"
    assert data[0]["evidence"]["delay"] > 30


def test_post_signals_api_zero_attrition(client):
    payload = {
        "historical_stats": [
            {
                "institution_id": "inst-full",
                "academic_year": "2021-22",
                "approved_seats": 100,
                "enrolled_students": 100,
                "attrition_count": 0,
            },
            {
                "institution_id": "inst-full",
                "academic_year": "2022-23",
                "approved_seats": 100,
                "enrolled_students": 100,
                "attrition_count": 0,
            },
        ]
    }
    response = client.post("/engine/signals", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["signal_name"] == "ZERO_ATTRITION_CAP_FILLING"
    assert data[0]["evidence"]["utilisation"] == 1.0


def test_post_signals_api_clean_admissions(client):
    payload = {
        "admissions": [
            {
                "student_id": "s-clean",
                "institution_id": "inst-clean",
                "programme_code": "BTECH",
                "category": "general",
                "qualifying_exam_pct": 78.0,
                "seat_pool": "regular",
                "dob": "2005-01-01",
                "admission_date": "2023-08-01",
                "upload_date": "2023-08-05",
                "contact_phone": "9998881111",
            }
        ]
    }
    response = client.post("/engine/signals", json=payload)
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_post_signals_api_empty_and_direct_list(client):
    # Empty payload
    res1 = client.post("/engine/signals", json={})
    assert res1.status_code == 200
    assert res1.json() == []

    # Direct list input
    res2 = client.post("/engine/signals", json=[])
    assert res2.status_code == 200
    assert res2.json() == []


def test_post_anomaly_api(client):
    payload = {
        "institutions": [
            {
                "institution_id": f"inst-{i}",
                "seat_utilisation": 0.8,
                "duplicate_rate": 0.01,
            }
            for i in range(10)
        ]
        + [
            {
                "institution_id": "inst-extreme",
                "seat_utilisation": 2.5,
                "duplicate_rate": 0.8,
                "backdated_admission_rate": 0.9,
            }
        ]
    }
    response = client.post("/engine/anomaly", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 11
    outlier = next(r for r in data if r["institution_id"] == "inst-extreme")
    assert outlier["prediction"] == "anomalous"
    assert outlier["score"] > 0.5


def test_post_integrity_score_api(client):
    payload = {
        "institution_id": "inst-score-test",
        "signals": [
            {
                "signal_name": "ELIGIBILITY_VIOLATION",
                "severity": "review",
                "score": 75.0,
            }
        ],
        "anomaly_score": 0.40,
    }
    response = client.post("/engine/integrity-score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["institution_id"] == "inst-score-test"
    assert 0.0 <= data["score"] <= 100.0
    assert data["risk_level"] in ("low", "medium", "high", "critical")
    assert "components" in data


def test_post_evaluate_api(client):
    response = client.post("/engine/evaluate", json={})
    assert response.status_code == 200
    data = response.json()
    assert "blind_match" in data
    assert "signals" in data
    assert "anomaly_detection" in data
    assert "integrity_score" in data
    assert "benchmark" in data
    assert "summary" in data
    assert data["summary"]["status"] == "completed"
