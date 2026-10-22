# Owner: Dev B
from __future__ import annotations

from pydantic import BaseModel


class Health(BaseModel):
    status: str
    mock_mode: bool
    engine_import_ok: bool
    engine_version: str | None = None
    version: str
