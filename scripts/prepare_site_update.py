from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "data/site-workflow"
GIT = r"C:\Program Files\Git\cmd\git.exe"


def prepare_checkout() -> dict[str, str]:
    state_path = RUNTIME / "state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if (
            state["status"] == "published"
            and state["date"] == datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
        ):
            return {"checkout_path": str(ROOT), "status": "published", "runtime_dir": str(RUNTIME)}
        if state["status"] == "ready":
            checkout = Path(state["checkout_path"])
            if checkout.is_dir():
                return {
                    "checkout_path": str(checkout),
                    "status": "ready",
                    "runtime_dir": str(RUNTIME),
                }
    checkout = RUNTIME / "checkouts" / datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    checkout.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [GIT, "worktree", "add", "--detach", str(checkout), "codex/site-live"],
        cwd=ROOT,
        stdout=sys.stderr,
        check=True,
    )
    return {"checkout_path": str(checkout), "status": "new", "runtime_dir": str(RUNTIME)}


if __name__ == "__main__":
    print(json.dumps(prepare_checkout(), ensure_ascii=False))
