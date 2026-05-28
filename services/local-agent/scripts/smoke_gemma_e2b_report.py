from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main() -> int:
    from worktrace_agent.scripts.smoke_gemma_e2b_report import main as smoke_main

    return smoke_main()


if __name__ == "__main__":
    raise SystemExit(main())
