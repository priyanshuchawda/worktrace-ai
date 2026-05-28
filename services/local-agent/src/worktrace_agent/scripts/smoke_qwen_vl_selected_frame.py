from __future__ import annotations

import base64
import json
import os
import urllib.parse
from dataclasses import dataclass
from typing import Literal

from worktrace_agent.ai.qwen_vl_runtime import (
    DEFAULT_QWEN_VL_MANIFEST,
    QwenVlJsonTransport,
    QwenVlSelectedFrameAnalyzer,
    build_qwen_vl_runtime_config,
)
from worktrace_agent.ai.vision_analysis import (
    VisionAnalysisRequest,
    VisionAnalysisStatus,
    analyze_selected_frame,
)
from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact
from worktrace_agent.privacy.redaction import count_privacy_leaks, redact_text

SmokeStatus = Literal["passed", "skipped", "failed"]
SMOKE_GENERATED_AT = "2026-05-08T00:00:00+05:30"
DEFAULT_ENDPOINT_ENV = "WORKTRACE_QWEN_VL_BASE_URL"
SMOKE_SESSION_ID = "sess_qwen_vl_smoke"
SMOKE_SCREENSHOT_ID = "shot_qwen_vl_smoke_frame"
SMOKE_SOURCE_EVENT_ID = "evt_qwen_vl_smoke_frame"

SAMPLE_FRAME_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAARnQU1B"
    "AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAANSURBVBhXY2BgYAAAAAQAAVzN/2kA"
    "AAAASUVORK5CYII="
)


@dataclass(frozen=True)
class QwenVlSmokeResult:
    status: SmokeStatus
    model_name: str
    endpoint: str
    generated_at: str
    evidence_ids: tuple[str, ...]
    privacy_leak_count: int
    reason: str | None
    title: str | None
    description: str | None

    def to_public_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "model_name": self.model_name,
            "endpoint": self.endpoint,
            "generated_at": self.generated_at,
            "evidence_ids": list(self.evidence_ids),
            "privacy_leak_count": self.privacy_leak_count,
            "reason": self.reason,
            "title": self.title,
            "description": self.description,
        }


def run_qwen_vl_smoke(
    *,
    base_url: str | None = None,
    transport: QwenVlJsonTransport | None = None,
) -> QwenVlSmokeResult:
    selected_base_url = base_url if base_url is not None else os.environ.get(DEFAULT_ENDPOINT_ENV)
    model_name = DEFAULT_QWEN_VL_MANIFEST.hugging_face_model_id
    if not selected_base_url:
        return _skipped(
            model_name=model_name,
            endpoint="not_configured",
            reason=f"{DEFAULT_ENDPOINT_ENV} is not configured.",
        )

    try:
        analyzer = QwenVlSelectedFrameAnalyzer(
            config=build_qwen_vl_runtime_config(base_url=selected_base_url),
            transport=transport,
            analyzer_version="qwen-vl-local-smoke",
        )
        decision = analyze_selected_frame(_smoke_request(), analyzer=analyzer)
    except ValueError as error:
        return _failed(
            model_name=model_name,
            endpoint=_safe_endpoint(selected_base_url),
            reason=str(error),
        )

    if decision.status is not VisionAnalysisStatus.ANALYZED or decision.result is None:
        return _failed(
            model_name=model_name,
            endpoint=_safe_endpoint(selected_base_url),
            reason=decision.user_message,
        )

    result = decision.result
    public_payload = {
        "title": result.title,
        "description": result.description,
        "evidence_ids": result.evidence_event_ids,
        "model_name": model_name,
        "endpoint": _safe_endpoint(selected_base_url),
    }
    return QwenVlSmokeResult(
        status="passed",
        model_name=model_name,
        endpoint=_safe_endpoint(selected_base_url),
        generated_at=SMOKE_GENERATED_AT,
        evidence_ids=result.evidence_event_ids,
        privacy_leak_count=count_privacy_leaks(public_payload),
        reason=None,
        title=result.title,
        description=result.description,
    )


def main() -> int:
    result = run_qwen_vl_smoke()
    print(json.dumps(result.to_public_dict(), sort_keys=True, indent=2))
    return 1 if result.status == "failed" else 0


def _smoke_request() -> VisionAnalysisRequest:
    image_bytes = base64.b64decode(SAMPLE_FRAME_PNG_BASE64)
    return VisionAnalysisRequest(
        screenshot=ScreenshotArtifact(
            id=SMOKE_SCREENSHOT_ID,
            session_id=SMOKE_SESSION_ID,
            source_event_id=SMOKE_SOURCE_EVENT_ID,
            timestamp="2026-05-08T14:20:00+05:30",
            width=1,
            height=1,
            stored_width=1,
            stored_height=1,
            byte_size=len(image_bytes),
            content_hash="embedded-qwen-vl-smoke-png",
            visual_hash="embedded-qwen-vl-smoke-visual",
            storage_path="embedded/shot_qwen_vl_smoke_frame.png",
        ),
        image_bytes=image_bytes,
        selected=True,
        app_name="Windows Terminal",
        window_title="pytest traceback",
        ocr_text="Traceback AssertionError in pytest output",
    )


def _skipped(*, model_name: str, endpoint: str, reason: str) -> QwenVlSmokeResult:
    redacted_reason = redact_text(reason)
    return QwenVlSmokeResult(
        status="skipped",
        model_name=model_name,
        endpoint=endpoint,
        generated_at=SMOKE_GENERATED_AT,
        evidence_ids=(),
        privacy_leak_count=count_privacy_leaks(redacted_reason),
        reason=redacted_reason,
        title=None,
        description=None,
    )


def _failed(*, model_name: str, endpoint: str, reason: str) -> QwenVlSmokeResult:
    redacted_reason = redact_text(reason)
    return QwenVlSmokeResult(
        status="failed",
        model_name=model_name,
        endpoint=endpoint,
        generated_at=SMOKE_GENERATED_AT,
        evidence_ids=(),
        privacy_leak_count=count_privacy_leaks({"endpoint": endpoint, "reason": redacted_reason}),
        reason=redacted_reason,
        title=None,
        description=None,
    )


def _safe_endpoint(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    return parsed.hostname or "invalid"


if __name__ == "__main__":
    raise SystemExit(main())
