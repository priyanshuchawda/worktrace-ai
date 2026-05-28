from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol, cast

from worktrace_agent.privacy.redaction import redact_json_value, redact_text

CORE_WORKFLOWS = ("recording", "timeline", "export")
DEFAULT_TIMEOUT_MS = 30_000


class ModelStatus(StrEnum):
    NOT_INSTALLED = "not_installed"
    LOADING = "loading"
    READY = "ready"
    UNAVAILABLE = "unavailable"
    TOO_SLOW = "too_slow"
    FAILED = "failed"
    DISABLED = "disabled"


class ModelProvider(StrEnum):
    LOCAL_FILE = "local_file"
    FAKE = "fake"


class ModelFailureCategory(StrEnum):
    NOT_INSTALLED = "not_installed"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    PROBE_FAILED = "probe_failed"


@dataclass(frozen=True)
class ModelAvailabilityConfig:
    model_name: str
    provider: ModelProvider
    model_path: Path | None = None
    timeout_ms: int = DEFAULT_TIMEOUT_MS


@dataclass(frozen=True)
class ModelProbeResult:
    status: ModelStatus
    latency_ms: int | None = None
    model_version: str | None = None
    safe_message: str | None = None
    failure_category: ModelFailureCategory | None = None

    @classmethod
    def ready(
        cls,
        *,
        latency_ms: int | None = None,
        model_version: str | None = None,
    ) -> ModelProbeResult:
        return cls(
            status=ModelStatus.READY,
            latency_ms=latency_ms,
            model_version=model_version,
            safe_message="Local AI model is available for manual report generation.",
        )

    @classmethod
    def unavailable(
        cls,
        *,
        category: ModelFailureCategory,
        safe_message: str,
        latency_ms: int | None = None,
    ) -> ModelProbeResult:
        return cls(
            status=ModelStatus.UNAVAILABLE,
            latency_ms=latency_ms,
            safe_message=safe_message,
            failure_category=category,
        )


class ModelProbe(Protocol):
    def check(self, config: ModelAvailabilityConfig) -> ModelProbeResult:
        """Return local model availability without loading heavy model runtimes."""
        ...


@dataclass(frozen=True)
class ModelAvailability:
    model_name: str
    provider: ModelProvider
    status: ModelStatus
    checked_at: str
    user_message: str
    can_record: bool
    can_build_timeline: bool
    can_export: bool
    can_generate_report: bool
    failure_category: ModelFailureCategory | None = None
    latency_ms: int | None = None
    model_version: str | None = None

    def allowed_core_workflows(self) -> tuple[str, ...]:
        allowed: list[str] = []
        if self.can_record:
            allowed.append("recording")
        if self.can_build_timeline:
            allowed.append("timeline")
        if self.can_export:
            allowed.append("export")
        return tuple(allowed)

    def to_debug_summary(self) -> dict[str, object]:
        summary: dict[str, object] = {
            "model_name": self.model_name,
            "provider": self.provider.value,
            "status": self.status.value,
            "checked_at": self.checked_at,
            "user_message": self.user_message,
            "can_generate_report": self.can_generate_report,
        }
        if self.failure_category is not None:
            summary["failure_category"] = self.failure_category.value
        if self.latency_ms is not None:
            summary["latency_ms"] = self.latency_ms
        if self.model_version is not None:
            summary["model_version"] = self.model_version
        return cast(dict[str, object], redact_json_value(summary))


def check_model_availability(
    config: ModelAvailabilityConfig,
    *,
    probe: ModelProbe | None = None,
    checked_at: str | None = None,
) -> ModelAvailability:
    _validate_config(config)
    timestamp = checked_at or _utc_now_iso()

    if config.provider is ModelProvider.LOCAL_FILE and not _model_path_exists(config.model_path):
        return _availability(
            config,
            status=ModelStatus.NOT_INSTALLED,
            checked_at=timestamp,
            user_message=(
                "Local AI model is not installed. Recording, timeline, and export work without AI."
            ),
            can_generate_report=False,
            failure_category=ModelFailureCategory.NOT_INSTALLED,
        )

    if probe is None:
        return _availability(
            config,
            status=ModelStatus.READY,
            checked_at=timestamp,
            user_message="Local AI model metadata is available for manual report generation.",
            can_generate_report=True,
        )

    try:
        result = probe.check(config)
    except TimeoutError:
        return _availability(
            config,
            status=ModelStatus.TOO_SLOW,
            checked_at=timestamp,
            user_message=(
                "Local AI model check exceeded the timeout. "
                "Recording, timeline, and export continue."
            ),
            can_generate_report=False,
            failure_category=ModelFailureCategory.TIMEOUT,
        )
    except Exception:
        return _availability(
            config,
            status=ModelStatus.FAILED,
            checked_at=timestamp,
            user_message=(
                "Local AI model check failed safely. Recording, timeline, and export continue."
            ),
            can_generate_report=False,
            failure_category=ModelFailureCategory.PROBE_FAILED,
        )

    if _is_too_slow(result.latency_ms, config.timeout_ms):
        return _availability(
            config,
            status=ModelStatus.TOO_SLOW,
            checked_at=timestamp,
            user_message=(
                "Local AI model is too slow for the configured timeout. "
                "Recording, timeline, and export continue."
            ),
            can_generate_report=False,
            failure_category=ModelFailureCategory.TIMEOUT,
            latency_ms=result.latency_ms,
            model_version=result.model_version,
        )

    if result.status is ModelStatus.READY:
        return _availability(
            config,
            status=ModelStatus.READY,
            checked_at=timestamp,
            user_message=result.safe_message
            or "Local AI model is available for manual report generation.",
            can_generate_report=True,
            latency_ms=result.latency_ms,
            model_version=result.model_version,
        )

    if result.status is ModelStatus.LOADING:
        return _availability(
            config,
            status=ModelStatus.LOADING,
            checked_at=timestamp,
            user_message=result.safe_message
            or "Local AI model is loading. Recording, timeline, and export continue.",
            can_generate_report=False,
            latency_ms=result.latency_ms,
            model_version=result.model_version,
        )

    return _availability(
        config,
        status=ModelStatus.UNAVAILABLE,
        checked_at=timestamp,
        user_message=result.safe_message
        or "Local AI model is unavailable. Recording, timeline, and export continue.",
        can_generate_report=False,
        failure_category=result.failure_category or ModelFailureCategory.UNAVAILABLE,
        latency_ms=result.latency_ms,
        model_version=result.model_version,
    )


def disabled_model_availability(
    *,
    model_name: str,
    provider: ModelProvider,
    checked_at: str | None = None,
) -> ModelAvailability:
    config = ModelAvailabilityConfig(model_name=model_name, provider=provider)
    _validate_config(config)
    return _availability(
        config,
        status=ModelStatus.DISABLED,
        checked_at=checked_at or _utc_now_iso(),
        user_message="Local AI is disabled. Recording, timeline, and export work without AI.",
        can_generate_report=False,
        failure_category=ModelFailureCategory.DISABLED,
    )


def _availability(
    config: ModelAvailabilityConfig,
    *,
    status: ModelStatus,
    checked_at: str,
    user_message: str,
    can_generate_report: bool,
    failure_category: ModelFailureCategory | None = None,
    latency_ms: int | None = None,
    model_version: str | None = None,
) -> ModelAvailability:
    return ModelAvailability(
        model_name=redact_text(config.model_name.strip()),
        provider=config.provider,
        status=status,
        checked_at=checked_at,
        user_message=redact_text(user_message),
        can_record=True,
        can_build_timeline=True,
        can_export=True,
        can_generate_report=can_generate_report,
        failure_category=failure_category,
        latency_ms=latency_ms,
        model_version=redact_text(model_version) if model_version is not None else None,
    )


def _validate_config(config: ModelAvailabilityConfig) -> None:
    if not config.model_name.strip():
        raise ValueError("model_name must be a non-empty string")
    if config.timeout_ms <= 0:
        raise ValueError("timeout_ms must be greater than zero")


def _model_path_exists(model_path: Path | None) -> bool:
    return model_path is not None and Path(model_path).is_file()


def _is_too_slow(latency_ms: int | None, timeout_ms: int) -> bool:
    return latency_ms is not None and latency_ms > timeout_ms


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
