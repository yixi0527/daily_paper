from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "apps" / "api" / "alembic.ini"
    args = sys.argv[1:] or ["upgrade", "head"]

    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(config_path), *args],
        cwd=repo_root,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())