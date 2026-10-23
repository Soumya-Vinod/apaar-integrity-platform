# Owner: Dev A
"""Base definitions, severity helpers, and evidence builders for integrity signals."""

from __future__ import annotations

from typing import Any, Literal

SeverityLevel = Literal["info", "warning", "review", "error"]


class SignalSeverity:
    """Configurable severity mapping from business impact to platform severity."""

    LOW: SeverityLevel = "info"
    MEDIUM: SeverityLevel = "warning"
    HIGH: SeverityLevel = "review"
    CRITICAL: SeverityLevel = "error"

    @classmethod
    def calculate(
        cls,
        base_importance: str = "medium",
        affected_count: int = 1,
        institution_wide: bool = False,
    ) -> SeverityLevel:
        """Determine signal severity based on rule importance, affected students, and impact.

        - Critical: high importance + large student count or institution-wide impact.
        - High (Review): high importance or moderate count of affected students.
        - Medium (Warning): standard rule violation.
        - Low (Info): informational or borderline observation.
        """
        importance = base_importance.lower()

        if importance in ("critical", "error"):
            return cls.CRITICAL if affected_count > 3 or institution_wide else cls.HIGH

        if importance in ("high", "review"):
            if institution_wide or affected_count >= 5:
                return cls.CRITICAL
            return cls.HIGH

        if importance in ("medium", "warning"):
            if affected_count >= 10:
                return cls.HIGH
            return cls.MEDIUM

        return cls.LOW


def build_evidence(
    student_id: str | None = None,
    institution_id: str | None = None,
    reason: str = "",
    details: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Format structured evidence according to the integrity platform contract."""
    evidence: dict[str, Any] = {}
    if student_id:
        evidence["student_id"] = student_id
    if institution_id:
        evidence["institution_id"] = institution_id
    if reason:
        evidence["reason"] = reason

    evidence["details"] = details or {}
    for k, v in extra.items():
        if v is not None:
            evidence[k] = v

    return evidence
