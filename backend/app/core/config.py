# Owner: Dev B
"""Application settings loaded from environment variables or backend/.env."""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Domains that can be switched from mock fixtures to Postgres with REAL_DOMAINS.
DOMAINS = ("institutions", "seat_ledger", "batches", "admissions", "review_cases", "audit")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    database_url: str = ""
    cors_origins: str = "http://localhost:5173"
    mock_mode: bool = True
    real_domains: str = ""
    max_upload_mb: int = 5
    max_upload_rows: int = 20000
    admission_cutoff_date: date = date(2026, 9, 30)
    shared_contact_threshold: int = 5
    blind_match_secret: str = ""
    pseudonym_secret: str = ""
    credential_signing_key: str = ""
    telegram_webhook_secret: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def real_domain_set(self) -> frozenset[str]:
        names = {d.strip() for d in self.real_domains.split(",") if d.strip()}
        unknown = names - set(DOMAINS)
        if unknown:
            raise ValueError(f"Unknown REAL_DOMAINS {sorted(unknown)}; use {DOMAINS}")
        return frozenset(names)

    def is_real(self, domain: str) -> bool:
        return domain in self.real_domain_set


@lru_cache
def get_settings() -> Settings:
    return Settings()
