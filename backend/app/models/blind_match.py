# Owner: Dev B (contract consumed by Dev A's blind-match router)
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.models.common import CaseStatus


class EncodeRequest(BaseModel):
    fields: dict[str, str]


class EncodeResponse(BaseModel):
    demo_only: Literal[True] = True
    bits: int
    k: int
    set_bits: int
    encoding_b64: str


class BlindMatchCase(BaseModel):
    id: str
    record_a: str
    record_b: str
    institution_a_id: str
    institution_b_id: str
    dice: float
    fields_compared: list[str]
    status: CaseStatus
    review_case_id: str | None = None
