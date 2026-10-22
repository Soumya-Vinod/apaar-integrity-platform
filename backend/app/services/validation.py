# Owner: Dev B
"""Row-level validation rules for uploaded admissions."""

from __future__ import annotations

import re

from app.core.rule_codes import RuleCode

_APAAR_RE = re.compile(r"\d{12}")


def validate_apaar(value: str | None, opted_out: bool) -> RuleCode | None:
    """Check an APAAR ID. Format only: no checksum is applied because none is published.

    12 digits passes (None). Blank with ``opted_out`` is APAAR_OPTED_OUT (info, not an
    error). Blank without opt-out is APAAR_MISSING. Anything else is APAAR_FORMAT.
    """
    cleaned = (value or "").strip()
    if not cleaned:
        return RuleCode.APAAR_OPTED_OUT if opted_out else RuleCode.APAAR_MISSING
    if _APAAR_RE.fullmatch(cleaned):
        return None
    return RuleCode.APAAR_FORMAT


def mask_apaar(value: str | None) -> str | None:
    """Mask an APAAR ID as XXXX-XXXX-1234."""
    if not value:
        return None
    return f"XXXX-XXXX-{value[-4:]}"
