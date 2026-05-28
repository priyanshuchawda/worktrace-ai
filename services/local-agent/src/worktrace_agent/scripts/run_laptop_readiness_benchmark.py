from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from worktrace_agent.performance.laptop_readiness import (
    DEFAULT_LAPTOP_READINESS_PROFILE,
    DEFAULT_LAPTOP_READINESS_SAMPLE_INTERVAL_SECONDS,
    benchmark_profile_choices,
    benchmark_profile_duration_seconds,
    laptop_readiness_result_to_json,
    render_laptop_readiness_markdown,
    run_laptop_readiness_benchmark,
)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    duration_seconds = (
        benchmark_profile_duration_seconds(args.profile)
        if args.duration_seconds is None
        else args.duration_seconds
    )
    result = asyncio.run(
        run_laptop_readiness_benchmark(
            benchmark_profile=args.profile,
            duration_seconds=duration_seconds,
            sample_interval_seconds=args.sample_interval_seconds,
            keep_artifacts=args.keep_artifacts,
        )
    )
    output_text = (
        laptop_readiness_result_to_json(result)
        if args.json
        else render_laptop_readiness_markdown(result)
    )
    if args.output is None:
        sys.stdout.write(output_text)
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text, encoding="utf-8")
        print(f"Wrote laptop readiness benchmark: {output_path}")
    return 0 if result.report.passed else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Run a local WorkTrace recorder benchmark and emit a safe aggregate report.")
    )
    parser.add_argument(
        "--profile",
        choices=benchmark_profile_choices(),
        default=DEFAULT_LAPTOP_READINESS_PROFILE,
        help=(
            "Benchmark profile. Use production-30-minute for release-readiness evidence; "
            "cloud/model inference remains out of scope."
        ),
    )
    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=None,
        help="Override benchmark duration in seconds. Defaults to the selected profile.",
    )
    parser.add_argument(
        "--sample-interval-seconds",
        type=float,
        default=DEFAULT_LAPTOP_READINESS_SAMPLE_INTERVAL_SECONDS,
        help="Seconds between resource samples.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional Markdown or JSON report output path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of Markdown.",
    )
    parser.add_argument(
        "--keep-artifacts",
        action="store_true",
        help="Keep the temporary recorder workspace for manual debugging.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
