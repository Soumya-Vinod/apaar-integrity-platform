# Owner: Dev A
"""Unit tests for /integrity router and integrity persistence integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tests.conftest import as_role

SHADOW = "10000000-0000-4000-8000-000000000003"
NARMADA = "10000000-0000-4000-8000-000000000002"


def test_integrity_endpoints_in_mock_mode(client):
    """Fixture/demo mode returns mock fixtures with X-Mock: true."""
    # 1. Rankings
    res = client.get("/integrity/institutions", headers=as_role("aicte_admin"))
    assert res.status_code == 200
    assert res.headers["X-Mock"] == "true"
    rankings = res.json()
    assert len(rankings) == 3
    assert rankings[0]["institution_id"] == SHADOW
    assert rankings[0]["rank"] == 1
    assert rankings[0]["integrity_score"] == 38.0

    # 2. Detail
    detail_res = client.get(f"/integrity/institutions/{SHADOW}", headers=as_role("aicte_admin"))
    assert detail_res.status_code == 200
    assert detail_res.headers["X-Mock"] == "true"
    detail = detail_res.json()
    assert detail["institution_id"] == SHADOW
    assert detail["integrity_score"] == 38.0
    assert "signals" in detail
    assert "anomaly" in detail
    assert detail["anomaly"]["score"] == 0.81

    # 3. 404 for unknown institution
    not_found_res = client.get(
        "/integrity/institutions/00000000-0000-0000-0000-000000000000",
        headers=as_role("aicte_admin"),
    )
    assert not_found_res.status_code == 404


def test_integrity_role_guard(client):
    """Students and unauthenticated callers cannot access integrity endpoints."""
    assert client.get("/integrity/institutions", headers=as_role("student")).status_code == 403
    url = f"/integrity/institutions/{SHADOW}"
    assert client.get(url, headers=as_role("student")).status_code == 403
    assert client.get("/integrity/institutions", headers=as_role("auditor")).status_code == 200



def test_integrity_endpoints_in_real_mode(client, settings_override):
    """When REAL_DOMAINS contains 'integrity', retrieves persisted results with X-Mock: false."""
    settings_override(real_domains="integrity", database_url="postgresql://fake:fake@localhost/fake")

    persisted_rankings = [
        {
            "rank": 1,
            "institution_id": SHADOW,
            "institution_name": "Shadow Institute of Technology",
            "aicte_code": "1-9999003",
            "integrity_score": 42.5,
            "anomaly_score": 0.78,
            "top_signals": ["INTAKE_OVERRUN", "BACKDATED_ENTRY"],
        },
        {
            "rank": 2,
            "institution_id": NARMADA,
            "institution_name": "Narmada Valley College of Technology",
            "aicte_code": "1-9999002",
            "integrity_score": 88.0,
            "anomaly_score": 0.25,
            "top_signals": [],
        },
    ]

    persisted_detail = {
        "institution_id": SHADOW,
        "academic_year": "2026-27",
        "score": 42.5,
        "tier": "high",
        "components": {
            "signals_deduction": 30.0,
            "anomaly_deduction": 20.0,
            "blind_match_deduction": 7.5,
            "total_deduction": 57.5,
            "anomaly_score": 0.78,
        },
        "top_features": [
            {"name": "management_quota_share", "value": 0.45, "peer_median": 0.12},
            {"name": "late_admission_share", "value": 0.30, "peer_median": 0.05},
        ],
        "signals": [
            {
                "code": "INTAKE_OVERRUN",
                "severity": "review",
                "evidence": {"programme_code": "UG-CSE", "overrun": 11},
            },
            {
                "code": "BACKDATED_ENTRY",
                "severity": "review",
                "evidence": {"count": 6},
            },
        ],
        "model_version": "0.1.0",
        "computed_at": "2026-10-24T06:00:00Z",
    }

    mock_conn = MagicMock()
    with (
        patch("app.routers.integrity.transaction") as mock_tx,
        patch("app.services.integrity_store.latest_rankings", return_value=persisted_rankings),
        patch("app.services.integrity_store.latest_for") as mock_latest_for,
    ):
        mock_tx.return_value.__enter__.return_value = mock_conn

        def side_effect_latest_for(conn, inst_id, year="2026-27"):
            if inst_id == SHADOW:
                return persisted_detail
            return None

        mock_latest_for.side_effect = side_effect_latest_for

        # 1. Test rankings in real mode
        res = client.get("/integrity/institutions", headers=as_role("aicte_admin"))
        assert res.status_code == 200
        assert res.headers["X-Mock"] == "false"
        data = res.json()
        assert len(data) == 2
        assert data[0]["institution_id"] == SHADOW
        assert data[0]["integrity_score"] == 42.5
        assert data[0]["anomaly_score"] == 0.78
        assert data[0]["top_signals"] == ["INTAKE_OVERRUN", "BACKDATED_ENTRY"]

        # 2. Test detail in real mode
        res_detail = client.get(f"/integrity/institutions/{SHADOW}", headers=as_role("aicte_admin"))
        assert res_detail.status_code == 200
        assert res_detail.headers["X-Mock"] == "false"
        detail_data = res_detail.json()
        assert detail_data["institution_id"] == SHADOW
        assert detail_data["integrity_score"] == 42.5
        assert detail_data["components"]["total_deduction"] == 57.5
        assert detail_data["anomaly"]["score"] == 0.78
        assert len(detail_data["anomaly"]["top_features"]) == 2
        assert len(detail_data["signals"]) == 2

        # 3. Test unknown institution in real mode raises 404
        res_unknown = client.get(
            "/integrity/institutions/00000000-0000-0000-0000-000000000000",
            headers=as_role("aicte_admin"),
        )
        assert res_unknown.status_code == 404


def test_compute_integrity_persistence():
    """Verify compute_and_save_integrity calls integrity_store.save_results."""
    from app.services.integrity import compute_and_save_integrity

    sample_results = [
        {
            "institution_id": SHADOW,
            "academic_year": "2026-27",
            "score": 40.0,
            "tier": "high",
            "model_version": "0.1.0",
            "components": {"anomaly": 0.8},
            "top_features": [],
            "signals": [],
        }
    ]

    mock_conn = MagicMock()
    with patch("app.services.integrity_store.save_results", return_value=1) as mock_save:
        count = compute_and_save_integrity(mock_conn, results=sample_results)
        assert count == 1
        mock_save.assert_called_once_with(mock_conn, sample_results)
