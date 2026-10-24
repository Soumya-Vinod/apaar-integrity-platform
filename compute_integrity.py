# Owner: Dev A
"""Compute job scoring institutions for an academic year and storing results via integrity_store.

shared/integrity-results.md:
Dev A's compute job (compute_integrity.py) scores each institution for an academic year
and stores the results with app.services.integrity_store. routers/integrity.py reads them back.

Usage:
    python compute_integrity.py
    python compute_integrity.py --year 2026-27
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure backend and engine/src are importable
ROOT = Path(__file__).resolve().parent
if (ROOT / "backend").exists() and str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))
if (ROOT / "engine" / "src").exists() and str(ROOT / "engine" / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "engine" / "src"))

from app.core.config import get_settings  # noqa: E402
from app.core.db import close_pool, transaction  # noqa: E402
from app.services.integrity import (  # noqa: E402
    compute_and_save_integrity,
    compute_institution_results,
    compute_rankings,
)
from app.services.integrity_store import save_results  # noqa: E402

__all__ = [
    "compute_and_save_integrity",
    "compute_institution_results",
    "compute_rankings",
    "main",
    "save_results",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute and persist institution integrity scores.")
    parser.add_argument("--year", default="2026-27", help="Academic year (default 2026-27)")
    parser.add_argument(
        "--institutions",
        nargs="*",
        default=None,
        help="Optional list of institution UUIDs to compute scores for",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL must be set in backend/.env", file=sys.stderr)
        return 2

    with transaction() as conn:
        results = compute_institution_results(
            conn, academic_year=args.year, institution_ids=args.institutions
        )
        saved = save_results(conn, results)
        print(f"Computed integrity scores for {len(results)} institutions; persisted {saved} rows.")

    close_pool()
    return 0


if __name__ == "__main__":
    sys.exit(main())
