# Owner: Dev A
"""Compute job scoring institutions for an academic year and storing results via integrity_store.

Run from backend/:
    uv run python -m scripts.compute_integrity
"""

from __future__ import annotations

import sys

from compute_integrity import main

if __name__ == "__main__":
    sys.exit(main())
