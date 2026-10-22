# Owner: Dev B
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.rule_codes import RuleCode
from app.models.common import BatchStatus, IssueSeverity


class BatchCounts(BaseModel):
    rows_total: int = 0
    errors: int = 0
    warnings: int = 0
    review: int = 0
    info: int = 0


class Batch(BaseModel):
    id: str
    institution_id: str
    uploaded_by: str
    file_name: str
    file_hash: str
    status: BatchStatus
    counts: BatchCounts
    created_at: datetime


class BatchUploadResult(BaseModel):
    batch: Batch
    suggested_mapping: dict[str, str] = Field(
        description="Uploaded column name -> admissions-template column name"
    )
    unmapped_columns: list[str]


class MappingRequest(BaseModel):
    mapping: dict[str, str]


class ValidationIssue(BaseModel):
    id: int
    batch_id: str
    row_number: int
    rule_code: RuleCode
    severity: IssueSeverity
    message: str
    details: dict[str, Any] = {}
    resolved: bool = False


class CommitResult(BaseModel):
    batch_id: str
    status: BatchStatus
    rows_committed: int
    rows_rejected: int
    review_cases_created: list[str]
