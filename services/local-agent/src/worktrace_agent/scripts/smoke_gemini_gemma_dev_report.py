from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from worktrace_agent.ai.gemini_gemma_dev_provider import (
    GeminiGemmaDevReportService,
    GeminiTextClient,
)
from worktrace_agent.ai.provider_config import read_ai_provider_config
from worktrace_agent.domain.raw_event import RawEvent
from worktrace_agent.privacy.redaction import count_privacy_leaks, redact_text

SmokeStatus = Literal["passed", "skipped", "failed"]


@dataclass(frozen=True)
class GeminiGemmaDevSmokeResult:
    status: SmokeStatus
    provider: str
    requested_model: str
    actual_model: str | None
    fallback_used: bool
    runtime_ms: int | None
    privacy_leak_count: int
    reason: str | None

    def to_public_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "provider": self.provider,
            "requested_model": self.requested_model,
            "actual_model": self.actual_model,
            "fallback_used": self.fallback_used,
            "runtime_ms": self.runtime_ms,
            "privacy_leak_count": self.privacy_leak_count,
            "reason": self.reason,
        }


def run_gemini_gemma_dev_smoke(
    *, client: GeminiTextClient | None = None
) -> GeminiGemmaDevSmokeResult:
    config = read_ai_provider_config()
    if not config.can_use_gemini_dev_provider:
        return _skipped(
            provider=config.provider.value,
            requested_model=config.gemma_primary_model,
            reason=(
                "gemini_gemma_dev smoke requires WORKTRACE_AI_PROVIDER=gemini_gemma_dev, "
                "WORKTRACE_ENABLE_DEV_CLOUD_AI=true, and GEMINI_API_KEY."
            ),
        )

    service = GeminiGemmaDevReportService(config=config, client=client)
    result = service.generate(session_id="sess_gemini_dev_smoke", events=_synthetic_events())
    if result["status"] != "complete":
        return _failed(
            provider=config.provider.value,
            requested_model=config.gemma_primary_model,
            actual_model=_optional_string(result.get("actual_model")),
            fallback_used=bool(result.get("fallback_used", False)),
            runtime_ms=_optional_int(result.get("runtime_ms")),
            reason=str(result.get("message") or "Gemini/Gemma development smoke failed safely."),
        )

    public_payload = {
        "provider": result.get("provider"),
        "requested_model": result.get("requested_model"),
        "actual_model": result.get("actual_model"),
        "fallback_used": result.get("fallback_used"),
        "runtime_ms": result.get("runtime_ms"),
    }
    return GeminiGemmaDevSmokeResult(
        status="passed",
        provider=config.provider.value,
        requested_model=config.gemma_primary_model,
        actual_model=_optional_string(result.get("actual_model")),
        fallback_used=bool(result.get("fallback_used", False)),
        runtime_ms=_optional_int(result.get("runtime_ms")),
        privacy_leak_count=count_privacy_leaks(public_payload),
        reason=None,
    )


def main() -> int:
    result = run_gemini_gemma_dev_smoke()
    print(json.dumps(result.to_public_dict(), sort_keys=True, indent=2))
    return 1 if result.status == "failed" else 0


def _synthetic_events() -> list[RawEvent]:
    return [
        RawEvent(
            id="evt_gemini_dev_smoke_terminal",
            session_id="sess_gemini_dev_smoke",
            timestamp="2026-05-26T09:00:00+05:30",
            source="terminal_command_detector",
            type="terminal_command",
            privacy_level="redacted",
            confidence=0.9,
            metadata={
                "command": "uv run --python 3.13 pytest tests/test_gemini_gemma_dev_provider.py",
                "shell": "powershell",
                "exit_code": 0,
                "command_hash": "hash-gemini-dev-smoke",
            },
        )
    ]


def _skipped(*, provider: str, requested_model: str, reason: str) -> GeminiGemmaDevSmokeResult:
    redacted_reason = redact_text(reason)
    return GeminiGemmaDevSmokeResult(
        status="skipped",
        provider=provider,
        requested_model=requested_model,
        actual_model=None,
        fallback_used=False,
        runtime_ms=None,
        privacy_leak_count=count_privacy_leaks(redacted_reason),
        reason=redacted_reason,
    )


def _failed(
    *,
    provider: str,
    requested_model: str,
    actual_model: str | None,
    fallback_used: bool,
    runtime_ms: int | None,
    reason: str,
) -> GeminiGemmaDevSmokeResult:
    redacted_reason = redact_text(reason)
    return GeminiGemmaDevSmokeResult(
        status="failed",
        provider=provider,
        requested_model=requested_model,
        actual_model=actual_model,
        fallback_used=fallback_used,
        runtime_ms=runtime_ms,
        privacy_leak_count=count_privacy_leaks(redacted_reason),
        reason=redacted_reason,
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return redact_text(str(value))


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None


if __name__ == "__main__":
    raise SystemExit(main())
