# Owner: Dev B
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.security import require_roles
from app.mocks import mock, not_found
from app.models.auth import User
from app.models.batches import (
    Batch,
    BatchUploadResult,
    CommitResult,
    MappingRequest,
    ValidationIssue,
)
from app.services.batches import read_header, suggest_mapping

router = APIRouter(prefix="/batches", tags=["batches"])

UPLOADERS = require_roles("institution_admin", "institution_operator")
READERS = require_roles("institution_admin", "institution_operator", "aicte_admin", "auditor")


def _batch(batch_id: str) -> dict:
    batch = mock("batch")
    if batch["id"] != batch_id:
        raise not_found("Batch", batch_id)
    return batch


@router.post("", response_model=BatchUploadResult, status_code=201)
async def upload_batch(file: UploadFile = File(...), user: User = Depends(UPLOADERS)) -> dict:
    """Upload a CSV or XLSX of admissions; returns the batch and a suggested column mapping."""
    name = file.filename or "upload.csv"
    if not name.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(415, "Upload a .csv or .xlsx file")
    batch = mock("batch")
    content = await file.read()
    mapping, unmapped = suggest_mapping(read_header(name, content))
    batch.update(
        file_name=name,
        file_hash=hashlib.sha256(content).hexdigest(),
        status="uploaded",
        uploaded_by=user.id,
    )
    if user.institution_id:
        batch["institution_id"] = user.institution_id
    return {"batch": batch, "suggested_mapping": mapping, "unmapped_columns": unmapped}


@router.post("/{batch_id}/mapping", response_model=Batch, dependencies=[Depends(UPLOADERS)])
def set_mapping(batch_id: str, body: MappingRequest) -> dict:
    batch = _batch(batch_id)
    batch["status"] = "mapped"
    return batch


@router.get("/{batch_id}", response_model=Batch, dependencies=[Depends(READERS)])
def get_batch(batch_id: str) -> dict:
    return _batch(batch_id)


@router.get(
    "/{batch_id}/issues", response_model=list[ValidationIssue], dependencies=[Depends(READERS)]
)
def get_issues(batch_id: str) -> list[dict]:
    _batch(batch_id)
    return mock("batch_issues")


@router.post("/{batch_id}/commit", response_model=CommitResult, dependencies=[Depends(UPLOADERS)])
def commit_batch(batch_id: str) -> dict:
    _batch(batch_id)
    return mock("commit_result")
