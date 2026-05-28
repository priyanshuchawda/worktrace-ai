from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from worktrace_agent.capture.ocr_runtime import (
    OcrRuntimeConfig,
    OcrRuntimeStatus,
    PaddleOcrRecognizer,
    build_paddle_ocr_engine,
)
from worktrace_agent.capture.ocr_worker import OcrCandidate
from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact
from worktrace_agent.privacy.redaction import count_privacy_leaks, redact_text

SmokeStatus = Literal["passed", "skipped", "failed"]
SMOKE_GENERATED_AT = "2026-05-08T00:00:00+05:30"
SMOKE_SESSION_ID = "sess_paddleocr_smoke"
SMOKE_SCREENSHOT_ID = "shot_paddleocr_smoke"
EXPECTED_TOKENS = ("traceback", "passed")

SAMPLE_SCREENSHOT_PNG_BASE64 = (
    "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"
)


@dataclass(frozen=True)
class PaddleOcrSmokeResult:
    status: SmokeStatus
    provider: str
    generated_at: str
    evidence_ids: tuple[str, ...]
    privacy_leak_count: int
    reason: str | None
    text_preview: str | None
    line_count: int

    def to_public_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "provider": self.provider,
            "generated_at": self.generated_at,
            "evidence_ids": list(self.evidence_ids),
            "privacy_leak_count": self.privacy_leak_count,
            "reason": self.reason,
            "text_preview": self.text_preview,
            "line_count": self.line_count,
        }


RecognizerFactory = Callable[[], PaddleOcrRecognizer]


def run_paddleocr_smoke(
    *,
    module_name: str = "paddleocr",
    recognizer_factory: RecognizerFactory | None = None,
) -> PaddleOcrSmokeResult:
    provider = "paddleocr"
    binding = build_paddle_ocr_engine(
        OcrRuntimeConfig(enabled=True, provider=provider, module_name=module_name),
        recognizer_factory=recognizer_factory,
    )
    if binding.availability.status is not OcrRuntimeStatus.READY or binding.engine is None:
        return _skipped(provider=provider, reason=binding.availability.user_message)

    try:
        result = binding.engine.recognize(_smoke_candidate())
    except RuntimeError as error:
        return _failed(provider=provider, reason=str(error))

    text_preview = redact_text(result.text.strip())
    lower_text = text_preview.lower()
    if not all(token in lower_text for token in EXPECTED_TOKENS):
        return _failed(
            provider=provider,
            reason="PaddleOCR smoke did not recognize the expected local screenshot text.",
            text_preview=text_preview,
            line_count=_line_count(result.metadata),
        )

    return PaddleOcrSmokeResult(
        status="passed",
        provider=provider,
        generated_at=SMOKE_GENERATED_AT,
        evidence_ids=(SMOKE_SCREENSHOT_ID,),
        privacy_leak_count=count_privacy_leaks(text_preview),
        reason=None,
        text_preview=text_preview,
        line_count=_line_count(result.metadata),
    )


def main() -> int:
    result = run_paddleocr_smoke()
    print(json.dumps(result.to_public_dict(), sort_keys=True, indent=2))
    return 1 if result.status == "failed" else 0


def _smoke_candidate() -> OcrCandidate:
    image_bytes = base64.b64decode(SAMPLE_SCREENSHOT_PNG_BASE64)
    return OcrCandidate(
        screenshot=ScreenshotArtifact(
            id=SMOKE_SCREENSHOT_ID,
            session_id=SMOKE_SESSION_ID,
            source_event_id="evt_paddleocr_smoke_window",
            timestamp="2026-05-08T13:30:00+05:30",
            width=360,
            height=90,
            stored_width=360,
            stored_height=90,
            byte_size=len(image_bytes),
            content_hash="embedded-paddleocr-smoke-png",
            visual_hash="embedded-paddleocr-smoke-visual",
            storage_path="embedded/shot_paddleocr_smoke.png",
        ),
        image_bytes=image_bytes,
        app_name="Windows Terminal",
        window_title="pytest traceback passed",
    )


def _line_count(metadata: dict[str, object] | None) -> int:
    value = (metadata or {}).get("line_count", 0)
    return value if isinstance(value, int) else 0


def _skipped(*, provider: str, reason: str) -> PaddleOcrSmokeResult:
    redacted_reason = redact_text(reason)
    return PaddleOcrSmokeResult(
        status="skipped",
        provider=provider,
        generated_at=SMOKE_GENERATED_AT,
        evidence_ids=(),
        privacy_leak_count=count_privacy_leaks(redacted_reason),
        reason=redacted_reason,
        text_preview=None,
        line_count=0,
    )


def _failed(
    *,
    provider: str,
    reason: str,
    text_preview: str | None = None,
    line_count: int = 0,
) -> PaddleOcrSmokeResult:
    redacted_reason = redact_text(reason)
    redacted_preview = redact_text(text_preview) if text_preview is not None else None
    return PaddleOcrSmokeResult(
        status="failed",
        provider=provider,
        generated_at=SMOKE_GENERATED_AT,
        evidence_ids=(),
        privacy_leak_count=count_privacy_leaks(
            {"reason": redacted_reason, "text_preview": redacted_preview}
        ),
        reason=redacted_reason,
        text_preview=redacted_preview,
        line_count=line_count,
    )


if __name__ == "__main__":
    raise SystemExit(main())
