from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tomllib
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from worktrace_agent.capture.active_window import ActiveWindowSnapshot
from worktrace_agent.capture.screenshot_capture import ScreenshotProvider
from worktrace_agent.capture.screenshot_sampler import ScreenshotFrame
from worktrace_agent.performance.laptop_readiness import (
    PRODUCTION_LAPTOP_READINESS_PROFILE,
    LaptopReadinessBenchmarkResult,
    current_process_ram_mb,
    render_laptop_readiness_markdown,
    run_laptop_readiness_benchmark,
)
from worktrace_agent.performance.resource_budgets import (
    RecordingResourceBudgetConfig,
    ResourceSample,
    evaluate_recording_resource_budget,
)


class StaticActiveWindowProvider:
    def get_active_window(self) -> ActiveWindowSnapshot:
        return ActiveWindowSnapshot(
            app="VS Code",
            window_title="screen-ai - App.tsx",
            process_name="Code.exe",
            timestamp=datetime.now(UTC).astimezone().isoformat(),
            confidence=0.98,
        )


class StaticScreenshotProvider(ScreenshotProvider):
    def __init__(self) -> None:
        self._value = 0

    def capture_frame(self, *, session_id: str, timestamp: str) -> ScreenshotFrame:
        self._value += 24
        return ScreenshotFrame(
            session_id=session_id,
            timestamp=timestamp,
            width=8,
            height=8,
            rgb_bytes=bytes([self._value, self._value, self._value]) * 8 * 8,
        )


def test_laptop_readiness_markdown_is_safe_and_honest() -> None:
    result = benchmark_result_fixture(passed=True, cleaned=True)

    markdown = render_laptop_readiness_markdown(result)

    assert "Short Laptop Readiness Benchmark" in markdown
    assert (
        "This is a short 5-10 minute readiness smoke, not a 30-minute production benchmark."
        in markdown
    )
    assert "Scope: local recorder pipeline only" in markdown
    assert "- Cloud request count: `0`" in markdown
    assert "- Privacy violation count: `0`" in markdown
    assert "raw active-window titles are not included" in markdown
    assert "| average_cpu_percent | 4.00 | 15.00 | yes |" in markdown
    assert "C:\\Users" not in markdown


def test_production_laptop_readiness_markdown_separates_cloud_and_model_benchmarks() -> None:
    result = replace(
        benchmark_result_fixture(passed=True, cleaned=True),
        benchmark_profile=PRODUCTION_LAPTOP_READINESS_PROFILE,
        duration_seconds=1800,
    )

    markdown = render_laptop_readiness_markdown(result)

    assert "30-Minute Production Readiness Benchmark" in markdown
    assert "30-minute local recorder pipeline benchmark" in markdown
    assert "Cloud inference" in markdown
    assert "Gemini/Gemma development-provider calls" in markdown
    assert "screenshot pixels are not included" in markdown
    assert "- Cloud request count: `0`" in markdown
    assert "- Privacy violation count: `0`" in markdown


def test_laptop_readiness_markdown_reports_retained_workspace_only_when_requested() -> None:
    retained = benchmark_result_fixture(passed=True, cleaned=False)

    markdown = render_laptop_readiness_markdown(
        replace(retained, artifact_root_retained="C:\\Users\\Admin\\AppData\\Local\\Temp\\bench")
    )

    assert "Artifacts retained:" in markdown
    assert "C:\\Users\\Admin\\AppData\\Local\\Temp\\bench" in markdown


def test_laptop_readiness_benchmark_runs_with_fake_capture_and_cleans_workspace(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "bench"

    result = asyncio.run(
        run_laptop_readiness_benchmark(
            duration_seconds=0.05,
            sample_interval_seconds=0.01,
            workspace_root=workspace,
            active_window_provider=StaticActiveWindowProvider(),
            screenshot_provider=StaticScreenshotProvider(),
        )
    )

    assert result.event_count >= 1
    assert result.screenshot_count >= 1
    assert result.temp_workspace_cleaned is True
    assert not workspace.exists()
    assert result.report.budget.recording_duration_minutes == 0.05 / 60
    assert result.artifact_root_retained is None


def test_laptop_readiness_benchmark_can_keep_artifacts_for_manual_debug(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "bench"

    result = asyncio.run(
        run_laptop_readiness_benchmark(
            duration_seconds=0.05,
            sample_interval_seconds=0.01,
            workspace_root=workspace,
            active_window_provider=StaticActiveWindowProvider(),
            screenshot_provider=StaticScreenshotProvider(),
            keep_artifacts=True,
        )
    )

    assert result.temp_workspace_cleaned is False
    assert workspace.exists()
    assert result.artifact_root_retained == str(workspace)


def test_current_process_ram_reports_nonzero_on_windows() -> None:
    ram_mb = current_process_ram_mb()

    if os.name == "nt":
        assert ram_mb > 0
    else:
        assert ram_mb >= 0


def test_laptop_readiness_cli_help_lists_duration_option() -> None:
    package_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(package_root / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "worktrace_agent.scripts.run_laptop_readiness_benchmark",
            "--help",
        ],
        cwd=package_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--profile" in result.stdout
    assert "production-30-minute" in result.stdout
    assert "--duration-seconds" in result.stdout
    assert "--keep-artifacts" in result.stdout


def test_local_agent_project_installs_console_scripts_with_uv() -> None:
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert pyproject["project"]["scripts"]["worktrace-laptop-readiness"] == (
        "worktrace_agent.scripts.run_laptop_readiness_benchmark:main"
    )
    assert pyproject["tool"]["uv"]["package"] is True


def benchmark_result_fixture(
    *,
    passed: bool,
    cleaned: bool,
) -> LaptopReadinessBenchmarkResult:
    report = evaluate_recording_resource_budget(
        (
            ResourceSample(
                sampled_at="2026-05-13T09:00:00+05:30",
                cpu_percent=4,
                ram_mb=120,
                db_bytes=1024,
                screenshot_bytes=2048,
                model_loaded=False,
                ai_status="disabled",
            ),
            ResourceSample(
                sampled_at="2026-05-13T09:05:00+05:30",
                cpu_percent=4,
                ram_mb=128,
                db_bytes=4096,
                screenshot_bytes=10_240,
                model_loaded=False,
                ai_status="disabled",
            ),
        ),
        budget=RecordingResourceBudgetConfig(recording_duration_minutes=5),
    )
    if not passed:
        raise AssertionError("fixture currently supports passed=True only")
    return LaptopReadinessBenchmarkResult(
        benchmark_profile="short",
        session_id="sess_laptop_readiness_001",
        started_at="2026-05-13T09:00:00+05:30",
        finished_at="2026-05-13T09:05:00+05:30",
        duration_seconds=300,
        sample_interval_seconds=10,
        event_count=7,
        screenshot_count=42,
        cloud_request_count=0,
        privacy_violation_count=0,
        temp_workspace_cleaned=cleaned,
        artifact_root_retained=None,
        report=report,
    )
