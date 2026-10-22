# Owner: Dev A
"""Unsupervised ranking of institutions by how anomalous their admission profile looks."""

from __future__ import annotations

from engine.types import AnomalyResult, InstitutionFeatures


def rank_institutions(features: list[InstitutionFeatures]) -> list[AnomalyResult]:
    """Rank institutions with an Isolation Forest, most anomalous first.

    Intended algorithm: build a matrix from each institution's feature dict (fixed column
    order, missing values as 0), standardise it, fit ``sklearn.ensemble.IsolationForest``
    with a fixed random_state, map ``score_samples`` to a 0-1 anomaly score, and explain each
    result with the features whose z-scores deviate most.
    """
    raise NotImplementedError
