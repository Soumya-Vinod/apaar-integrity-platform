# Owner: Dev A
"""Engine configuration defaults reading from environment variables."""

from __future__ import annotations

import os

MATCH_THRESHOLD: float = float(os.getenv("MATCH_THRESHOLD", "0.85"))
MODEL_VERSION: str = os.getenv("MODEL_VERSION", "0.1.0")
