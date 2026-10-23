# Owner: Dev B
"""FastAPI application: CORS, mock-mode header and every router."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import (
    admissions,
    audit,
    auth,
    batches,
    blind_match,
    certificates,
    credentials,
    engine,
    health,
    institutions,
    integrations,
    integrity,
    reports,
    review_cases,
    seat_ledger,
    students,
    webhooks,
)

settings = get_settings()

app = FastAPI(
    title="APAAR Integrity Platform",
    description="Verifiable, consent-first student records for AICTE-approved institutions.",
    version=health.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Mock"],
)


@app.middleware("http")
async def mock_header(request: Request, call_next):
    response = await call_next(request)
    if get_settings().mock_mode:
        response.headers["X-Mock"] = "true"
    return response


for module in (
    health,
    engine,
    auth,
    institutions,
    seat_ledger,
    batches,
    admissions,
    review_cases,
    audit,
    integrations,
    integrity,
    blind_match,
    reports,
    certificates,
    credentials,
    students,
    webhooks,
):
    app.include_router(module.router)

