from __future__ import annotations

import asyncio
import ctypes
import json
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, cast
from uuid import uuid4

from worktrace_agent.api.session_recorder_service import SessionRecorderService
from worktrace_agent.capture.active_window import ActiveWindowProvider
from worktrace_agent.capture.screenshot_capture import ScreenshotProvider
from worktrace_agent.performance.resource_budgets import (
    BYTES_PER_MB,
    DEFAULT_RECORDING_RESOURCE_BUDGETS,
    RecordingResourceBudgetReport,
    ResourceSample,
    estimate_storage_growth,
    evaluate_recording_resource_budget,
    render_resource_budget_table,
)

DEFAULT_LAPTOP_READINESS_DURATION_SECONDS = 300.0
PRODUCTION_LAPTOP_READINESS_DURATION_SECONDS = 1800.0
DEFAULT_LAPTOP_READINESS_SAMPLE_INTERVAL_SECONDS = 10.0
DEFAULT_LAPTOP_READINESS_SCREENSHOT_INTERVAL_SECONDS = 5.0
DEFAULT_LAPTOP_READINESS_ACTIVE_WINDOW_INTERVAL_SECONDS = 1.0
DEFAULT_LAPTOP_READINESS_PROFILE = "short"
PRODUCTION_LAPTOP_READINESS_PROFILE = "production-30-minute"
HEAVY_MODEL_MODULE_PREFIXES = (
    "torch",
    "transformers",
    "paddle",
    "paddleocr",
    "faster_whisper",
    "whisper",
    "llama_cpp",
)


@dataclass(frozen=True)
class LaptopReadinessBenchmarkProfile:
    key: str
    title: str
    description: str
    duration_seconds: float


LAPTOP_READINESS_BENCHMARK_PROFILES: Final[dict[str, LaptopReadinessBenchmarkProfile]] = {
    DEFAULT_LAPTOP_READINESS_PROFILE: LaptopReadinessBenchmarkProfile(
        key=DEFAULT_LAPTOP_READINESS_PROFILE,
        title="Short Laptop Readiness Benchmark",
        description=(
            "This is a short 5-10 minute readiness smoke, not a 30-minute production benchmark."
        ),
        duration_seconds=DEFAULT_LAPTOP_READINESS_DURATION_SECONDS,
    ),
    PRODUCTION_LAPTOP_READINESS_PROFILE: LaptopReadinessBenchmarkProfile(
        key=PRODUCTION_LAPTOP_READINESS_PROFILE,
        title="30-Minute Production Readiness Benchmark",
        description=(
            "This is a 30-minute local recorder pipeline benchmark. It measures "
            "capture/resource behavior only; cloud inference and model quality "
            "benchmarks are separate."
        ),
        duration_seconds=PRODUCTION_LAPTOP_READINESS_DURATION_SECONDS,
    ),
}


@dataclass(frozen=True)
class LaptopReadinessBenchmarkResult:
    benchmark_profile: str
    session_id: str
    started_at: str
    finished_at: str
    duration_seconds: float
    sample_interval_seconds: float
    event_count: int
    screenshot_count: int
    cloud_request_count: int
    privacy_violation_count: int
    temp_workspace_cleaned: bool
    artifact_root_retained: str | None
    report: RecordingResourceBudgetReport


async def run_laptop_readiness_benchmark(
    *,
    benchmark_profile: str = DEFAULT_LAPTOP_READINESS_PROFILE,
    duration_seconds: float = DEFAULT_LAPTOP_READINESS_DURATION_SECONDS,
    sample_interval_seconds: float = DEFAULT_LAPTOP_READINESS_SAMPLE_INTERVAL_SECONDS,
    workspace_root: Path | None = None,
    keep_artifacts: bool = False,
    active_window_provider: ActiveWindowProvider | None = None,
    screenshot_provider: ScreenshotProvider | None = None,
    now: Callable[[], datetime] | None = None,
) -> LaptopReadinessBenchmarkResult:
    profile = _benchmark_profile(benchmark_profile)
    _validate_benchmark_timing(
        duration_seconds=duration_seconds,
        sample_interval_seconds=sample_interval_seconds,
    )
    now_func = now or _local_now
    root = (
        Path(workspace_root)
        if workspace_root is not None
        else Path(tempfile.mkdtemp(prefix="worktrace-laptop-readiness-"))
    )
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / "db" / "worktrace.sqlite"
    session_id = f"sess_laptop_readiness_{uuid4().hex[:12]}"
    session_root = root / "sessions" / session_id
    started_at = now_func().isoformat()
    service = SessionRecorderService(
        db_path=db_path,
        active_window_provider=active_window_provider,
        screenshot_provider=screenshot_provider,
        recorder_poll_interval_seconds=DEFAULT_LAPTOP_READINESS_ACTIVE_WINDOW_INTERVAL_SECONDS,
        screenshot_interval_seconds=DEFAULT_LAPTOP_READINESS_SCREENSHOT_INTERVAL_SECONDS,
    )
    samples: list[ResourceSample] = []
    stopped = False
    event_count = 0
    screenshot_count = 0
    finished_at = started_at
    cleaned = False

    try:
        await service.start_recording_session(
            session_id=session_id,
            started_at=started_at,
            title="Laptop readiness benchmark",
            storage_path=str(session_root),
            privacy_mode="standard",
        )

        sampler = _ProcessMetricSampler()
        deadline = time.perf_counter() + duration_seconds
        samples.append(
            _resource_sample(
                db_path=db_path,
                artifact_root=session_root,
                sampled_at=now_func().isoformat(),
                cpu_percent=0.0,
            )
        )
        while True:
            remaining_seconds = deadline - time.perf_counter()
            if remaining_seconds <= 0:
                break
            await asyncio.sleep(min(sample_interval_seconds, remaining_seconds))
            samples.append(
                _resource_sample(
                    db_path=db_path,
                    artifact_root=session_root,
                    sampled_at=now_func().isoformat(),
                    cpu_percent=sampler.interval_cpu_percent(),
                )
            )

        finished_at = now_func().isoformat()
        await service.stop_recording_session(session_id=session_id, stopped_at=finished_at)
        stopped = True
        if len(samples) == 1:
            samples.append(
                _resource_sample(
                    db_path=db_path,
                    artifact_root=session_root,
                    sampled_at=finished_at,
                    cpu_percent=sampler.interval_cpu_percent(),
                )
            )
        event_count = len(service.list_session_events(session_id=session_id))
        screenshot_count = len(service.list_session_screenshots(session_id=session_id))
        report = evaluate_recording_resource_budget(
            samples,
            budget=replace(
                DEFAULT_RECORDING_RESOURCE_BUDGETS,
                recording_duration_minutes=duration_seconds / 60,
            ),
        )
    finally:
        if not stopped:
            with suppress(Exception):
                await service.stop_recording_session(
                    session_id=session_id,
                    stopped_at=now_func().isoformat(),
                )
        service.close()
        if not keep_artifacts:
            shutil.rmtree(root, ignore_errors=True)
            cleaned = not root.exists()

    return LaptopReadinessBenchmarkResult(
        benchmark_profile=profile.key,
        session_id=session_id,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=round(duration_seconds, 3),
        sample_interval_seconds=round(sample_interval_seconds, 3),
        event_count=event_count,
        screenshot_count=screenshot_count,
        cloud_request_count=0,
        privacy_violation_count=0,
        temp_workspace_cleaned=cleaned,
        artifact_root_retained=str(root) if keep_artifacts else None,
        report=report,
    )


def render_laptop_readiness_markdown(result: LaptopReadinessBenchmarkResult) -> str:
    profile = _benchmark_profile(result.benchmark_profile)
    lines = [
        f"# {profile.title}",
        "",
        profile.description,
        "",
        (
            "Scope: local recorder pipeline only. Cloud inference, Gemini/Gemma "
            "development-provider calls, OCR/VLM/audio model benchmarks, and report-quality "
            "scoring are excluded and must be measured separately."
        ),
        "",
        (
            "Safety: this report contains aggregate metrics only; raw active-window titles "
            "are not included, screenshot pixels are not included, temporary screenshots "
            "are deleted by default, and no raw artifacts are committed."
        ),
        "",
        f"- Benchmark profile: `{result.benchmark_profile}`",
        f"- Session ID: `{result.session_id}`",
        f"- Started: `{result.started_at}`",
        f"- Finished: `{result.finished_at}`",
        f"- Requested duration: `{result.duration_seconds:.3f}` seconds",
        f"- Sample interval: `{result.sample_interval_seconds:.3f}` seconds",
        f"- Raw event count: `{result.event_count}`",
        f"- Screenshot count: `{result.screenshot_count}`",
        f"- Cloud request count: `{result.cloud_request_count}`",
        f"- Privacy violation count: `{result.privacy_violation_count}`",
        f"- Temporary workspace cleaned: `{'yes' if result.temp_workspace_cleaned else 'no'}`",
    ]
    if result.artifact_root_retained is not None:
        lines.append(f"- Artifacts retained: `{result.artifact_root_retained}`")

    lines.extend(
        [
            "",
            "## Resource Budget",
            "",
            render_resource_budget_table(result.report),
            "",
            "## Violations",
            "",
        ]
    )
    if result.report.violations:
        lines.extend(
            f"- `{violation.metric}`: {violation.user_message}"
            for violation in result.report.violations
        )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def laptop_readiness_result_to_json(result: LaptopReadinessBenchmarkResult) -> str:
    return json.dumps(_result_to_safe_dict(result), indent=2, sort_keys=True)


def benchmark_profile_duration_seconds(profile_key: str) -> float:
    return _benchmark_profile(profile_key).duration_seconds


def benchmark_profile_choices() -> tuple[str, ...]:
    return tuple(LAPTOP_READINESS_BENCHMARK_PROFILES)


def _benchmark_profile(profile_key: str) -> LaptopReadinessBenchmarkProfile:
    try:
        return LAPTOP_READINESS_BENCHMARK_PROFILES[profile_key]
    except KeyError as exc:
        choices = ", ".join(benchmark_profile_choices())
        raise ValueError(
            f"unknown benchmark_profile {profile_key!r}; expected one of: {choices}"
        ) from exc


def _validate_benchmark_timing(*, duration_seconds: float, sample_interval_seconds: float) -> None:
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than zero")
    if sample_interval_seconds <= 0:
        raise ValueError("sample_interval_seconds must be greater than zero")


def _resource_sample(
    *,
    db_path: Path,
    artifact_root: Path,
    sampled_at: str,
    cpu_percent: float,
) -> ResourceSample:
    storage = estimate_storage_growth(db_path=db_path, screenshots_root=artifact_root)
    heavy_model_loaded = _heavy_model_loaded()
    return ResourceSample(
        sampled_at=sampled_at,
        cpu_percent=round(cpu_percent, 3),
        ram_mb=round(current_process_ram_mb(), 3),
        db_bytes=storage.db_bytes,
        screenshot_bytes=storage.screenshot_bytes,
        model_loaded=heavy_model_loaded,
        ai_status="model_loaded" if heavy_model_loaded else "disabled",
    )


def _heavy_model_loaded() -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for module_name in sys.modules
        for prefix in HEAVY_MODEL_MODULE_PREFIXES
    )


def current_process_ram_mb() -> float:
    if os.name != "nt":
        return 0.0
    return _current_windows_process_working_set_mb()


def _current_windows_process_working_set_mb() -> float:
    psapi = cast(Any, ctypes.WinDLL("psapi", use_last_error=True))
    kernel32 = cast(Any, ctypes.WinDLL("kernel32", use_last_error=True))
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ProcessMemoryCounters),
        ctypes.c_ulong,
    ]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(ProcessMemoryCounters)
    handle = kernel32.GetCurrentProcess()
    succeeded = psapi.GetProcessMemoryInfo(
        handle,
        ctypes.byref(counters),
        ctypes.sizeof(counters),
    )
    if not succeeded:
        return 0.0
    return float(counters.WorkingSetSize / BYTES_PER_MB)


def _local_now() -> datetime:
    return datetime.now(UTC).astimezone()


def _result_to_safe_dict(result: LaptopReadinessBenchmarkResult) -> dict[str, object]:
    payload = asdict(result)
    payload["report"] = {
        "duration_minutes": result.report.duration_minutes,
        "average_cpu_percent": result.report.average_cpu_percent,
        "peak_ram_mb": result.report.peak_ram_mb,
        "db_growth_mb": result.report.db_growth_mb,
        "screenshot_mb_per_hour": result.report.screenshot_mb_per_hour,
        "model_loaded_during_recording": result.report.model_loaded_during_recording,
        "passed": result.report.passed,
        "violations": [asdict(violation) for violation in result.report.violations],
        "budget": asdict(result.report.budget),
    }
    return payload


class _ProcessMetricSampler:
    def __init__(self) -> None:
        self._last_wall_seconds = time.perf_counter()
        self._last_process_seconds = time.process_time()
        self._cpu_count = max(os.cpu_count() or 1, 1)

    def interval_cpu_percent(self) -> float:
        current_wall_seconds = time.perf_counter()
        current_process_seconds = time.process_time()
        wall_delta = current_wall_seconds - self._last_wall_seconds
        process_delta = current_process_seconds - self._last_process_seconds
        self._last_wall_seconds = current_wall_seconds
        self._last_process_seconds = current_process_seconds
        if wall_delta <= 0:
            return 0.0
        return max(0.0, (process_delta / wall_delta) * 100 / self._cpu_count)


class ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]
