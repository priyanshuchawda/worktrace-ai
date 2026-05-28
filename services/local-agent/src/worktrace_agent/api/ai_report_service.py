from __future__ import annotations

from typing import Protocol, cast

from worktrace_agent.ai.provider_config import AiProviderConfig, AiReportProvider
from worktrace_agent.domain.raw_event import RawEvent
from worktrace_agent.privacy.redaction import redact_json_value, redact_text

AI_REPORT_UNAVAILABLE_MESSAGE = (
    "Local AI report runtime is unavailable. Recording, timeline, and export continue."
)


class AiReportService(Protocol):
    def status(self, *, session_id: str) -> dict[str, object]:
        """Return safe local AI report availability for a session."""
        ...

    def generate(self, *, session_id: str, events: list[RawEvent]) -> dict[str, object]:
        """Generate a local AI report from redacted deterministic evidence."""
        ...

    def cancel(self, *, session_id: str) -> dict[str, object]:
        """Cancel a running local AI report if supported."""
        ...


class UnavailableAiReportService:
    def __init__(self, *, provider_config: AiProviderConfig | None = None) -> None:
        self._provider_config = provider_config

    def status(self, *, session_id: str) -> dict[str, object]:
        return unavailable_ai_report_result(provider_config=self._provider_config)

    def generate(self, *, session_id: str, events: list[RawEvent]) -> dict[str, object]:
        return unavailable_ai_report_result(provider_config=self._provider_config)

    def cancel(self, *, session_id: str) -> dict[str, object]:
        return {
            **_base_result(
                status="cancelled",
                message="Local AI report generation cancelled.",
                can_generate=True,
            ),
            **_provider_fields(self._provider_config),
            "report": None,
        }


def unavailable_ai_report_result(
    *, provider_config: AiProviderConfig | None = None
) -> dict[str, object]:
    return {
        **_base_result(
            status="runtime_unavailable",
            message=_unavailable_message(provider_config),
            can_generate=False,
        ),
        **_provider_fields(provider_config),
        "report": None,
    }


def failed_ai_report_result() -> dict[str, object]:
    return {
        **_base_result(
            status="failed_safely",
            message="Local AI report generation failed safely.",
            can_generate=False,
        ),
        "report": None,
    }


def safe_ai_report_result(payload: dict[str, object]) -> dict[str, object]:
    return redact_json_value(
        {
            **_base_result(
                status=str(payload.get("status") or "failed_safely"),
                message=str(payload.get("message") or "Local AI report failed safely."),
                can_generate=bool(payload.get("can_generate", False)),
            ),
            "report": payload.get("report"),
            "evidence_ids": _string_list(payload.get("evidence_ids")),
            "model_name": _optional_string(payload.get("model_name")),
            "model_version": _optional_string(payload.get("model_version")),
            "provider": _optional_string(payload.get("provider")),
            "requested_model": _optional_string(payload.get("requested_model")),
            "actual_model": _optional_string(payload.get("actual_model")),
            "fallback_used": bool(payload.get("fallback_used", False)),
            "runtime_ms": payload.get("runtime_ms"),
            "input_hash": _optional_string(payload.get("input_hash")),
            "generated_at": _optional_string(payload.get("generated_at")),
        }
    )


def _base_result(*, status: str, message: str, can_generate: bool) -> dict[str, object]:
    return {
        "status": redact_text(status),
        "message": redact_text(message),
        "can_generate": can_generate,
        "report": None,
        "evidence_ids": [],
        "model_name": None,
        "model_version": None,
        "provider": None,
        "requested_model": None,
        "actual_model": None,
        "fallback_used": False,
        "runtime_ms": None,
        "input_hash": None,
        "generated_at": None,
    }


def _provider_fields(provider_config: AiProviderConfig | None) -> dict[str, object]:
    if provider_config is None:
        return {"provider": None}
    return {
        "provider": provider_config.provider.value,
        "requested_model": (
            provider_config.gemma_primary_model
            if provider_config.provider is AiReportProvider.GEMINI_GEMMA_DEV
            else None
        ),
        "actual_model": None,
        "fallback_used": False,
    }


def _unavailable_message(provider_config: AiProviderConfig | None) -> str:
    if provider_config is None or provider_config.provider is AiReportProvider.LOCAL_OLLAMA:
        return AI_REPORT_UNAVAILABLE_MESSAGE
    if not provider_config.dev_cloud_enabled:
        return (
            "Development cloud AI is disabled. Set WORKTRACE_ENABLE_DEV_CLOUD_AI=true "
            "to use gemini_gemma_dev."
        )
    if not provider_config.gemini_api_key_present:
        return "GEMINI_API_KEY is required for gemini_gemma_dev."
    return "Gemini/Gemma development AI provider is not wired yet."


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return redact_text(str(value))


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items = cast(list[object], value)
    return [redact_text(str(item)) for item in items if str(item).strip()]
