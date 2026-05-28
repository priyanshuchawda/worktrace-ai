from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from statistics import median
from typing import Final

from worktrace_agent.capture.screenshot_sampler import (
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_MAX_CPU_AVERAGE_PERCENT,
    DEFAULT_MAX_HOURLY_BYTES,
)
from worktrace_agent.privacy.redaction import redact_text

BYTES_PER_MB: Final = 1024 * 1024
DEFAULT_MAX_RAM_MB: Final = 800.0
DEFAULT_MAX_DB_GROWTH_MB: Final = 100.0
DEFAULT_RECORDING_DURATION_MINUTES: Final = 30.0


class ResourceBudgetViolationCode(StrEnum):
    CPU_AVERAGE_EXCEEDED = "cpu_average_exceeded"
    RAM_LIMIT_EXCEEDED = "ram_limit_exceeded"
    DB_GROWTH_EXCEEDED = "db_growth_exceeded"
    SCREENSHOT_STORAGE_EXCEEDED = "screenshot_storage_exceeded"
    MODEL_LOADED_DURING_RECORDING = "model_loaded_during_recording"


@dataclass(frozen=True)
class RecordingResourceBudgetConfig:
    max_average_cpu_percent: float = DEFAULT_MAX_CPU_AVERAGE_PERCENT
    max_ram_mb: float = DEFAULT_MAX_RAM_MB
    max_db_growth_mb: float = DEFAULT_MAX_DB_GROWTH_MB
    max_screenshot_mb_per_hour: float = DEFAULT_MAX_HOURLY_BYTES / BYTES_PER_MB
    screenshot_interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    recording_duration_minutes: float = DEFAULT_RECORDING_DURATION_MINUTES
    allow_model_loaded_during_recording: bool = False


@dataclass(frozen=True)
class ResourceSample:
    sampled_at: str
    cpu_percent: float
    ram_mb: float
    db_bytes: int
    screenshot_bytes: int
    model_loaded: bool
    ai_status: str = "unknown"


@dataclass(frozen=True)
class ResourceBudgetViolation:
    code: ResourceBudgetViolationCode
    metric: str
    actual: float
    budget: float
    user_message: str


@dataclass(frozen=True)
class StorageGrowthEstimate:
    db_bytes: int
    screenshot_bytes: int


@dataclass(frozen=True)
class RecordingResourceBudgetReport:
    duration_minutes: float
    average_cpu_percent: float
    peak_ram_mb: float
    db_growth_mb: float
    screenshot_mb_per_hour: float
    model_loaded_during_recording: bool
    violations: tuple[ResourceBudgetViolation, ...]
    passed: bool
    budget: RecordingResourceBudgetConfig = RecordingResourceBudgetConfig()


DEFAULT_RECORDING_RESOURCE_BUDGETS: Final = RecordingResourceBudgetConfig()


def evaluate_recording_resource_budget(
    samples: tuple[ResourceSample, ...] | list[ResourceSample],
    *,
    budget: RecordingResourceBudgetConfig = DEFAULT_RECORDING_RESOURCE_BUDGETS,
) -> RecordingResourceBudgetReport:
    sample_tuple = tuple(samples)
    if not sample_tuple:
        raise ValueError("resource budget evaluation requires at least one sample")

    _validate_budget(budget)
    _validate_samples(sample_tuple)

    duration_minutes = _duration_minutes(sample_tuple)
    average_cpu_percent = sum(sample.cpu_percent for sample in sample_tuple) / len(sample_tuple)
    peak_ram_mb = max(sample.ram_mb for sample in sample_tuple)
    db_growth_mb = _growth_mb(sample.db_bytes for sample in sample_tuple)
    screenshot_growth_mb = _growth_mb(sample.screenshot_bytes for sample in sample_tuple)
    screenshot_mb_per_hour = screenshot_growth_mb / (duration_minutes / 60)
    model_loaded = any(sample.model_loaded for sample in sample_tuple)

    violations = _budget_violations(
        samples=sample_tuple,
        budget=budget,
        average_cpu_percent=average_cpu_percent,
        peak_ram_mb=peak_ram_mb,
        db_growth_mb=db_growth_mb,
        screenshot_mb_per_hour=screenshot_mb_per_hour,
        model_loaded=model_loaded,
    )
    return RecordingResourceBudgetReport(
        duration_minutes=round(duration_minutes, 2),
        average_cpu_percent=round(average_cpu_percent, 2),
        peak_ram_mb=round(peak_ram_mb, 2),
        db_growth_mb=round(db_growth_mb, 2),
        screenshot_mb_per_hour=round(screenshot_mb_per_hour, 2),
        model_loaded_during_recording=model_loaded,
        violations=violations,
        passed=not violations,
        budget=budget,
    )


def estimate_storage_growth(*, db_path: Path, screenshots_root: Path) -> StorageGrowthEstimate:
    resolved_db_path = Path(db_path)
    resolved_screenshots_root = Path(screenshots_root)
    db_bytes = resolved_db_path.stat().st_size if resolved_db_path.exists() else 0
    screenshot_bytes = _sum_file_bytes(resolved_screenshots_root)
    return StorageGrowthEstimate(db_bytes=db_bytes, screenshot_bytes=screenshot_bytes)


def render_resource_budget_table(report: RecordingResourceBudgetReport) -> str:
    rows = [
        "| metric | actual | budget | passed |",
        "| --- | ---: | ---: | --- |",
        _table_row(
            "duration_minutes",
            report.duration_minutes,
            report.budget.recording_duration_minutes,
            report.duration_minutes >= report.budget.recording_duration_minutes,
        ),
        _table_row(
            "average_cpu_percent",
            report.average_cpu_percent,
            report.budget.max_average_cpu_percent,
            report.average_cpu_percent <= report.budget.max_average_cpu_percent,
        ),
        _table_row(
            "peak_ram_mb",
            report.peak_ram_mb,
            report.budget.max_ram_mb,
            report.peak_ram_mb <= report.budget.max_ram_mb,
        ),
        _table_row(
            "db_growth_mb",
            report.db_growth_mb,
            report.budget.max_db_growth_mb,
            report.db_growth_mb <= report.budget.max_db_growth_mb,
        ),
        _table_row(
            "screenshot_mb_per_hour",
            report.screenshot_mb_per_hour,
            report.budget.max_screenshot_mb_per_hour,
            report.screenshot_mb_per_hour <= report.budget.max_screenshot_mb_per_hour,
        ),
        _table_row(
            "model_loaded_during_recording",
            1.0 if report.model_loaded_during_recording else 0.0,
            1.0 if report.budget.allow_model_loaded_during_recording else 0.0,
            not report.model_loaded_during_recording
            or report.budget.allow_model_loaded_during_recording,
        ),
    ]
    return "\n".join(rows)


def _budget_violations(
    *,
    samples: tuple[ResourceSample, ...],
    budget: RecordingResourceBudgetConfig,
    average_cpu_percent: float,
    peak_ram_mb: float,
    db_growth_mb: float,
    screenshot_mb_per_hour: float,
    model_loaded: bool,
) -> tuple[ResourceBudgetViolation, ...]:
    violations: list[ResourceBudgetViolation] = []
    if average_cpu_percent > budget.max_average_cpu_percent:
        violations.append(
            _violation(
                ResourceBudgetViolationCode.CPU_AVERAGE_EXCEEDED,
                metric="average_cpu_percent",
                actual=average_cpu_percent,
                budget=budget.max_average_cpu_percent,
                message=(
                    f"CPU average was {average_cpu_percent:.2f}%, above the "
                    f"{budget.max_average_cpu_percent:.2f}% recording budget."
                ),
            )
        )
    if peak_ram_mb > budget.max_ram_mb:
        violations.append(
            _violation(
                ResourceBudgetViolationCode.RAM_LIMIT_EXCEEDED,
                metric="peak_ram_mb",
                actual=peak_ram_mb,
                budget=budget.max_ram_mb,
                message=(
                    f"RAM peaked at {peak_ram_mb:.2f} MB, above the "
                    f"{budget.max_ram_mb:.2f} MB recording budget."
                ),
            )
        )
    if db_growth_mb > budget.max_db_growth_mb:
        violations.append(
            _violation(
                ResourceBudgetViolationCode.DB_GROWTH_EXCEEDED,
                metric="db_growth_mb",
                actual=db_growth_mb,
                budget=budget.max_db_growth_mb,
                message=(
                    f"Database grew by {db_growth_mb:.2f} MB, above the "
                    f"{budget.max_db_growth_mb:.2f} MB recording budget."
                ),
            )
        )
    if screenshot_mb_per_hour > budget.max_screenshot_mb_per_hour:
        violations.append(
            _violation(
                ResourceBudgetViolationCode.SCREENSHOT_STORAGE_EXCEEDED,
                metric="screenshot_mb_per_hour",
                actual=screenshot_mb_per_hour,
                budget=budget.max_screenshot_mb_per_hour,
                message=(
                    f"Screenshots used {screenshot_mb_per_hour:.2f} MB/hour, above the "
                    f"{budget.max_screenshot_mb_per_hour:.2f} MB/hour recording budget."
                ),
            )
        )
    if model_loaded and not budget.allow_model_loaded_during_recording:
        model_statuses = ", ".join(
            sorted({sample.ai_status for sample in samples if sample.model_loaded})
        )
        violations.append(
            _violation(
                ResourceBudgetViolationCode.MODEL_LOADED_DURING_RECORDING,
                metric="model_loaded_during_recording",
                actual=1,
                budget=0,
                message=(
                    "No local AI model should be loaded during recording. "
                    f"Observed model state: {model_statuses or 'unknown'}."
                ),
            )
        )
    return tuple(violations)


def _violation(
    code: ResourceBudgetViolationCode,
    *,
    metric: str,
    actual: float,
    budget: float,
    message: str,
) -> ResourceBudgetViolation:
    return ResourceBudgetViolation(
        code=code,
        metric=metric,
        actual=round(actual, 2),
        budget=round(budget, 2),
        user_message=redact_text(message),
    )


def _validate_budget(budget: RecordingResourceBudgetConfig) -> None:
    if budget.max_average_cpu_percent <= 0:
        raise ValueError("max_average_cpu_percent must be greater than zero")
    if budget.max_ram_mb <= 0:
        raise ValueError("max_ram_mb must be greater than zero")
    if budget.max_db_growth_mb < 0:
        raise ValueError("max_db_growth_mb must not be negative")
    if budget.max_screenshot_mb_per_hour < 0:
        raise ValueError("max_screenshot_mb_per_hour must not be negative")
    if budget.screenshot_interval_seconds <= 0:
        raise ValueError("screenshot_interval_seconds must be greater than zero")
    if budget.recording_duration_minutes <= 0:
        raise ValueError("recording_duration_minutes must be greater than zero")


def _validate_samples(samples: tuple[ResourceSample, ...]) -> None:
    previous_timestamp: datetime | None = None
    for sample in samples:
        timestamp = _parse_offset_datetime(sample.sampled_at)
        if previous_timestamp is not None and timestamp <= previous_timestamp:
            raise ValueError("resource samples must be ordered by increasing sampled_at")
        previous_timestamp = timestamp
        if sample.cpu_percent < 0:
            raise ValueError("cpu_percent must not be negative")
        if sample.ram_mb < 0:
            raise ValueError("ram_mb must not be negative")
        if sample.db_bytes < 0:
            raise ValueError("db_bytes must not be negative")
        if sample.screenshot_bytes < 0:
            raise ValueError("screenshot_bytes must not be negative")
        if not sample.ai_status.strip():
            raise ValueError("ai_status must be a non-empty string")


def _duration_minutes(samples: tuple[ResourceSample, ...]) -> float:
    if len(samples) == 1:
        return 1.0

    timestamps = [_parse_offset_datetime(sample.sampled_at) for sample in samples]
    intervals = [
        (current - previous).total_seconds() / 60
        for previous, current in zip(timestamps[:-1], timestamps[1:], strict=True)
    ]
    return (timestamps[-1] - timestamps[0]).total_seconds() / 60 + median(intervals)


def _growth_mb(values: Iterable[int]) -> float:
    typed_values = tuple(int(value) for value in values)
    if not typed_values:
        return 0.0
    return (max(typed_values) - min(typed_values)) / BYTES_PER_MB


def _sum_file_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    if root.is_file():
        return root.stat().st_size
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _parse_offset_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("sampled_at must include a timezone offset")
    return parsed


def _table_row(metric: str, actual: float, budget: float, passed: bool) -> str:
    return f"| {metric} | {actual:.2f} | {budget:.2f} | {'yes' if passed else 'no'} |"
