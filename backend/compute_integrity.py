# Owner: Dev A
"""Compute job scoring institutions for an academic year and storing results via integrity_store.

Run from backend/:
    python compute_integrity.py
    python -m scripts.compute_integrity
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if (ROOT / "engine" / "src").exists() and str(ROOT / "engine" / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "engine" / "src"))

from app.services.integrity import (  # noqa: E402
    compute_and_save_integrity,
    compute_institution_results,
    compute_rankings,
)
from app.services.integrity_store import save_results  # noqa: E402
from compute_integrity import main  # noqa: E402

__all__ = [
    "compute_and_save_integrity",
    "compute_institution_results",
    "compute_rankings",
    "main",
    "save_results",
]

if __name__ == "__main__":
    sys.exit(main())
