# Owner: Dev A
"""Integrity Score: one 0-100 number per institution."""

from __future__ import annotations

from engine.types import AnomalyResult, IntegrityScore, Signal


def integrity_score(signals: list[Signal], anomaly: AnomalyResult | None) -> IntegrityScore:
    """Combine signals and the anomaly result into a score from 0 (worst) to 100 (clean).

    Intended algorithm: start at 100; subtract a capped, weighted penalty per signal by
    severity (review > warning > info); subtract a penalty proportional to the anomaly
    score; clamp to [0, 100]; record each deduction in ``components``.
    """
    raise NotImplementedError
