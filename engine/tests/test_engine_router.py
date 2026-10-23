# Owner: Dev A
"""Comprehensive tests for engine router endpoints (F16 Anomaly & F17 Integrity Score)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engine.anomaly.features import FEATURE_NAMES
from engine.routers import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_post_anomaly_endpoint_batch() -> None:
    # 10 normal institutions + 1 outlier
    payload = [
        {
            "institution_id": f"inst-{i}",
            "features": {name: 0.1 for name in FEATURE_NAMES},
        }
        for i in range(10)
    ]
    payload.append(
        {
            "institution_id": "inst-outlier",
            "features": {
                "seat_utilisation": 2.5,
                "intake_growth": 1.5,
                "eligibility_violation_count": 40.0,
                "backdated_admission_rate": 0.8,
            },
        }
    )

    response = client.post("/engine/anomaly", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 11

    outlier_res = next(r for r in data if r["institution_id"] == "inst-outlier")
    assert outlier_res["prediction"] == "anomalous"
    assert outlier_res["score"] > 0.5
    assert len(outlier_res["top_features"]) > 0
    assert "feature_vector" in outlier_res


def test_post_anomaly_endpoint_single_institution() -> None:
    payload = {
        "institution_id": "inst-single",
        "features": {
            "seat_utilisation": 0.85,
            "intake_growth": 0.05,
            "duplicate_rate": 0.0,
        },
    }
    response = client.post("/engine/anomaly", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["institution_id"] == "inst-single"
    assert "score" in data
    assert "prediction" in data
    assert "top_features" in data
    assert "feature_vector" in data


def test_post_anomaly_empty_and_malformed() -> None:
    # Empty list should return empty list
    res_list = client.post("/engine/anomaly", json=[])
    assert res_list.status_code == 200
    assert res_list.json() == []

    # Empty dict should return empty list
    res_dict = client.post("/engine/anomaly", json={})
    assert res_dict.status_code == 200
    assert res_dict.json() == []

    # Non-dict/non-list malformed payload
    res_malformed = client.post(
        "/engine/anomaly",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert res_malformed.status_code == 422


def test_post_integrity_score_endpoint_single() -> None:
    payload = {
        "institution_id": "inst-apex",
        "signals": [
            {
                "signal_name": "ELIGIBILITY_VIOLATION",
                "severity": "review",
                "score": 75.0,
            }
        ],
        "anomaly_score": 0.35,
        "blind_matches": [
            {
                "institution_a": "inst-apex",
                "institution_b": "inst-other",
                "student_a_id": "s1",
                "student_b_id": "s2",
                "similarity_score": 0.95,
                "confidence": 0.90,
            }
        ],
    }

    response = client.post("/engine/integrity-score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["institution_id"] == "inst-apex"
    assert 0.0 <= data["score"] <= 100.0
    assert data["risk_level"] in ("low", "medium", "high", "critical")
    assert "components" in data
    assert len(data["signals"]) == 1
    assert "generated_at" in data


def test_post_integrity_score_endpoint_batch() -> None:
    payload = [
        {
            "institution_id": "inst-1",
            "anomaly_score": 0.1,
            "signals": [],
        },
        {
            "institution_id": "inst-2",
            "anomaly_score": 0.8,
            "signals": [
                {
                    "signal_name": "BACKDATED_ADMISSIONS",
                    "severity": "error",
                    "score": 90.0,
                }
            ],
        },
    ]

    response = client.post("/engine/integrity-score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["institution_id"] == "inst-1"
    assert data[1]["institution_id"] == "inst-2"
    assert data[0]["score"] > data[1]["score"]


def test_post_integrity_score_empty_and_malformed() -> None:
    # Empty dict payload
    res_empty = client.post("/engine/integrity-score", json={})
    assert res_empty.status_code == 400

    # Malformed non-JSON
    res_malformed = client.post(
        "/engine/integrity-score",
        content="raw-string-bad",
        headers={"Content-Type": "application/json"},
    )
    assert res_malformed.status_code == 422
