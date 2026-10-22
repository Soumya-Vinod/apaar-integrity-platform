# Owner: Dev A
"""Shared dataclasses passed between engine modules and the backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["error", "warning", "review", "info"]


@dataclass(frozen=True)
class EncodedRecord:
    """A student identity reduced to a Bloom-filter encoding. No raw identity fields."""

    record_id: str
    institution_id: str
    bloom: bytes
    birth_year_hash: str
    apaar_id: str | None = None


@dataclass(frozen=True)
class MatchCandidate:
    """A pair of encoded records that probably refer to the same person."""

    record_a: str
    record_b: str
    dice: float
    same_institution: bool = False


@dataclass
class Signal:
    """A rule-based integrity signal raised against an institution."""

    code: str
    institution_id: str
    severity: Severity
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class InstitutionFeatures:
    """Per-institution feature vector used for anomaly ranking."""

    institution_id: str
    features: dict[str, float] = field(default_factory=dict)


@dataclass
class AnomalyResult:
    """Isolation Forest output for one institution. Higher score means more anomalous."""

    institution_id: str
    score: float
    top_features: list[str] = field(default_factory=list)


@dataclass
class IntegrityScore:
    """Integrity Score from 0 (worst) to 100 (clean), with the deduction for each component."""

    institution_id: str
    score: float
    components: dict[str, float] = field(default_factory=dict)
