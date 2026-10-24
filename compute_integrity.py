# Owner: Dev A
"""Compatibility wrapper delegating to canonical backend/scripts/compute_integrity.py.

shared/integrity-results.md:
Dev A's compute job (compute_integrity.py) scores each institution for an academic year
and stores the results with app.services.integrity_store.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parent
    backend_dir = root / "backend"
    engine_src = root / "engine" / "src"

    env = dict(os.environ)
    curr_pp = env.get("PYTHONPATH", "")
    paths = [str(backend_dir), str(engine_src)]
    if curr_pp:
        paths.append(curr_pp)
    env["PYTHONPATH"] = os.pathsep.join(paths)

    args = sys.argv[1:] if argv is None else argv
    cmd = [sys.executable, "-m", "scripts.compute_integrity", *args]
    return subprocess.run(cmd, cwd=str(backend_dir), env=env).returncode


if __name__ == "__main__":
    sys.exit(main())
