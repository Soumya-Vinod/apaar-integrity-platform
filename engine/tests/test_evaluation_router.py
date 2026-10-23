# Owner: Dev A
"""Comprehensive tests for POST /engine/evaluate router endpoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engine.evaluation.datasets import EvaluationDataset
from engine.routers import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_post_evaluate_endpoint_default() -> None:
    response = client.post("/engine/evaluate", json={})
    assert response.status_code == 200
    data = response.json()

    assert "blind_match" in data
    assert "signals" in data
    assert "anomaly_detection" in data
    assert "integrity_score" in data
    assert "benchmark" in data
    assert "summary" in data
    assert "generated_at" in data

    assert data["summary"]["status"] == "completed"
    assert data["blind_match"]["metrics"]["f1_score"] > 0.0
    assert data["signals"]["f1_score"] > 0.0
    assert data["anomaly_detection"]["metrics"]["f1_score"] > 0.0
    assert data["integrity_score"]["status"] == "passed"


def test_post_evaluate_endpoint_custom_dataset() -> None:
    custom_dataset = EvaluationDataset.create_synthetic_benchmark_dataset(seed=99)
    payload = custom_dataset.to_dict()

    response = client.post("/engine/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["status"] == "completed"
    assert "benchmark" in data


def test_post_evaluate_endpoint_malformed_input() -> None:
    # Malformed non-JSON string
    response = client.post(
        "/engine/evaluate",
        content="raw-malformed-string",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422

    # Malformed list payload when dict expected
    res_list = client.post("/engine/evaluate", json=["not", "a", "dict"])
    assert res_list.status_code in (400, 422)
