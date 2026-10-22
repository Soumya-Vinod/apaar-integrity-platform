# Owner: Dev A
"""Evaluation of engine output against datagen ground truth."""

from __future__ import annotations

from typing import Any


def evaluate(predictions: list[dict[str, Any]], ground_truth: list[dict[str, Any]]) -> dict:
    """Return precision, recall and F1 per signal type.

    Intended algorithm: key both lists by (record_id, anomaly_type); per type count true
    positives, false positives and false negatives; return
    ``{type: {"precision": p, "recall": r, "f1": f1, "support": n}}``.
    """
    raise NotImplementedError
