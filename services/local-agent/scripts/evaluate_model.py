from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main() -> None:
    from worktrace_agent.evals.ai_report_benchmark import (
        evaluate_ai_report_benchmark,
        render_ai_report_benchmark_table,
    )
    from worktrace_agent.evals.golden_sessions import (
        evaluate_golden_sessions,
        render_benchmark_table,
    )

    print(render_benchmark_table(evaluate_golden_sessions()))
    print()
    print(render_ai_report_benchmark_table(evaluate_ai_report_benchmark()))


if __name__ == "__main__":
    main()
