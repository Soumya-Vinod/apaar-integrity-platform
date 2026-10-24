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
