# Owner: Dev B
"""JSON fixtures returned in mock mode, plus the mock-or-501 helper used by every router."""

from __future__ import annotations

import copy
import json
from functools import cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.core.config import get_settings

MOCK_DIR = Path(__file__).parent


@cache
def _read(name: str) -> Any:
    return json.loads((MOCK_DIR / f"{name}.json").read_text(encoding="utf-8"))


def load(name: str) -> Any:
    """Return a deep copy of fixture ``<name>.json`` so callers can modify it freely."""
    return copy.deepcopy(_read(name))


def require_mock() -> None:
    """Raise 501 when mock mode is off and the real implementation does not exist yet."""
    if not get_settings().mock_mode:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Not implemented outside mock mode")


def mock(name: str) -> Any:
    require_mock()
    return load(name)


def not_found(what: str, key: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} '{key}' not found")
