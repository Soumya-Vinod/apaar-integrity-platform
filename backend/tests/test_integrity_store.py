# Owner: Dev B
"""Input checks of app.services.integrity_store (the upsert itself is an integration test)."""

from __future__ import annotations

import pytest

from app.services import integrity_store


class NoDb:
    def cursor(self):
        raise AssertionError("nothing should be written")


def test_missing_required_key_writes_nothing():
    result = {"institution_id": "x", "academic_year": "2026-27", "score": 1, "tier": "low"}
    with pytest.raises(ValueError, match="model_version"):
        integrity_store.save_results(NoDb(), [result])


def test_empty_list_writes_nothing():
    assert integrity_store.save_results(NoDb(), []) == 0


def test_latest_rankings_sorting_and_signals():
    class FakeConn:
        def execute(self, query, params=()):
            class FakeCursor:
                def fetchall(self):
                    return [
                        {
                            "institution_id": "inst-1",
                            "institution_name": "Inst Clean",
                            "aicte_code": "1-001",
                            "integrity_score": 95.0,
                            "tier": "low",
                            "components": {"anomaly_score": 0.15},
                            "top_features": [],
                            "signals": [],
                            "computed_at": "2026-10-24T06:00:00Z",
                        },
                        {
                            "institution_id": "inst-2",
                            "institution_name": "Inst Risky",
                            "aicte_code": "1-002",
                            "integrity_score": 35.0,
                            "tier": "critical",
                            "components": {"anomaly": 0.85},
                            "top_features": [],
                            "signals": [
                                {"code": "INTAKE_OVERRUN"},
                                {"code": "SHARED_CONTACT"},
                                {"code": "INTAKE_OVERRUN"},  # duplicate code to test deduplication
                            ],
                            "computed_at": "2026-10-24T06:00:00Z",
                        },
                    ]

            return FakeCursor()

    rankings = integrity_store.latest_rankings(FakeConn(), "2026-27")
    assert len(rankings) == 2
    # Risky institution should be rank 1 (higher anomaly, lower integrity score)
    assert rankings[0]["rank"] == 1
    assert rankings[0]["institution_id"] == "inst-2"
    assert rankings[0]["anomaly_score"] == 0.85
    assert rankings[0]["top_signals"] == ["INTAKE_OVERRUN", "SHARED_CONTACT"]

    # Clean institution should be rank 2
    assert rankings[1]["rank"] == 2
    assert rankings[1]["institution_id"] == "inst-1"
    assert rankings[1]["anomaly_score"] == 0.15
    assert rankings[1]["top_signals"] == []

