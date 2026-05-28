from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, cast

from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact
from worktrace_agent.privacy.redaction import (
    PRIVACY_TEST_CORPUS,
    SECRET_VALUES,
    redact_json_value,
    redact_text,
)
from worktrace_agent.timeline.deterministic import require_confidence, require_evidence_event_ids

ERROR_DIALOG_MARKERS = (
    "assertionerror",
    "crash",
    "dialog",
    "error",
    "exception",
    "failed",
    "failure",
    "pytest",
    "traceback",
    "warning",
)

SECRET_RISK_MARKERS = (
    ".env",
    "api_key",
    "authorization: bearer",
    "aws_secret_access_key",
    "begin private key",
    "github_token",
    "password",
    "private key",
    "secret",
    "token",
)


class VisionAnalysisStatus(StrEnum):
    SKIPPED_NOT_SELECTED = "skipped_not_selected"
    REFUSED_SECRET_RISK = "refused_secret_risk"  # nosec B105
    CANCELLED = "cancelled"
    ANALYZED = "analyzed"
    FAILED = "failed"


class VisionFailureCategory(StrEnum):
    NOT_SELECTED = "not_selected"
    SECRET_RISK = "secret_risk"  # nosec B105
    CANCELLED = "cancelled"
    ANALYZER_FAILED = "analyzer_failed"


@dataclass(frozen=True)
class VisionAnalysisRequest:
    screenshot: ScreenshotArtifact
    image_bytes: bytes
    selected: bool
    app_name: str
    window_title: str
    ocr_text: str | None = None


@dataclass(frozen=True)
class VisionAnalyzerResult:
    title: str
    description: str
    confidence: float
    metadata: dict[str, object] | None = None


class VisionAnalyzer(Protocol):
    @property
    def analyzer_name(self) -> str:
        """Human-readable analyzer name for safe metadata."""
        ...

    @property
    def analyzer_version(self) -> str | None:
        """Optional analyzer version for safe metadata."""
        ...

    def analyze(self, request: VisionAnalysisRequest) -> VisionAnalyzerResult:
        """Analyze one explicitly selected screenshot."""
        ...


@dataclass(frozen=True)
class VisionCancellationToken:
    cancelled: bool = False


@dataclass(frozen=True)
class VisionAnalysis:
    id: str
    session_id: str
    screenshot_id: str
    kind: str
    title: str
    description: str
    confidence: float
    analyzer_name: str
    analyzer_version: str | None
    evidence_event_ids: tuple[str, ...]
    metadata: dict[str, object]


@dataclass(frozen=True)
class VisionAnalysisDecision:
    status: VisionAnalysisStatus
    result: VisionAnalysis | None
    user_message: str
    failure_category: VisionFailureCategory | None = None


def analyze_selected_frame(
    request: VisionAnalysisRequest,
    *,
    analyzer: VisionAnalyzer,
    cancellation_token: VisionCancellationToken | None = None,
) -> VisionAnalysisDecision:
    _validate_request(request)

    if not request.selected:
        return VisionAnalysisDecision(
            status=VisionAnalysisStatus.SKIPPED_NOT_SELECTED,
            result=None,
            user_message="Vision analysis requires a selected screenshot.",
            failure_category=VisionFailureCategory.NOT_SELECTED,
        )

    if cancellation_token is not None and cancellation_token.cancelled:
        return VisionAnalysisDecision(
            status=VisionAnalysisStatus.CANCELLED,
            result=None,
            user_message="Vision analysis was cancelled.",
            failure_category=VisionFailureCategory.CANCELLED,
        )

    if is_secret_risk_candidate(request):
        return VisionAnalysisDecision(
            status=VisionAnalysisStatus.REFUSED_SECRET_RISK,
            result=None,
            user_message=(
                "Vision analysis refused detailed extraction because the selected screen may "
                "contain secrets."
            ),
            failure_category=VisionFailureCategory.SECRET_RISK,
        )

    try:
        analyzer_result = analyzer.analyze(request)
    except Exception:
        return VisionAnalysisDecision(
            status=VisionAnalysisStatus.FAILED,
            result=None,
            user_message="Vision analysis failed safely.",
            failure_category=VisionFailureCategory.ANALYZER_FAILED,
        )

    return VisionAnalysisDecision(
        status=VisionAnalysisStatus.ANALYZED,
        result=build_vision_analysis(
            request=request,
            analyzer_name=analyzer.analyzer_name,
            analyzer_version=analyzer.analyzer_version,
            analyzer_result=analyzer_result,
        ),
        user_message="Vision analysis completed.",
    )


def build_vision_analysis(
    *,
    request: VisionAnalysisRequest,
    analyzer_name: str,
    analyzer_version: str | None,
    analyzer_result: VisionAnalyzerResult,
) -> VisionAnalysis:
    screenshot = request.screenshot
    metadata = cast(dict[str, object], redact_json_value(analyzer_result.metadata or {}))
    return VisionAnalysis(
        id=f"{screenshot.id}-vision",
        session_id=screenshot.session_id,
        screenshot_id=screenshot.id,
        kind="error_dialog"
        if is_error_dialog_candidate(
            app_name=request.app_name,
            window_title=request.window_title,
            ocr_text=request.ocr_text,
        )
        else "selected_frame",
        title=redact_text(analyzer_result.title.strip()),
        description=redact_text(analyzer_result.description.strip()),
        confidence=require_confidence(analyzer_result.confidence),
        analyzer_name=redact_text(analyzer_name.strip()),
        analyzer_version=redact_text(analyzer_version) if analyzer_version is not None else None,
        evidence_event_ids=_evidence_event_ids(screenshot),
        metadata=metadata,
    )


def is_error_dialog_candidate(*, app_name: str, window_title: str, ocr_text: str | None) -> bool:
    searchable = f"{app_name} {window_title} {ocr_text or ''}".lower()
    return any(marker in searchable for marker in ERROR_DIALOG_MARKERS)


def is_secret_risk_candidate(request: VisionAnalysisRequest) -> bool:
    searchable = (f"{request.app_name} {request.window_title} {request.ocr_text or ''}").lower()
    lowered_privacy_values = [value.lower() for value in PRIVACY_TEST_CORPUS + SECRET_VALUES]
    return any(
        marker in searchable for marker in SECRET_RISK_MARKERS + tuple(lowered_privacy_values)
    )


def _validate_request(request: VisionAnalysisRequest) -> None:
    if not request.image_bytes:
        raise ValueError("image_bytes must not be empty")
    if not request.app_name.strip():
        raise ValueError("app_name must be a non-empty string")
    if not request.window_title.strip():
        raise ValueError("window_title must be a non-empty string")


def _evidence_event_ids(screenshot: ScreenshotArtifact) -> tuple[str, ...]:
    if screenshot.source_event_id is not None and screenshot.source_event_id.strip():
        return require_evidence_event_ids((screenshot.source_event_id,))
    return require_evidence_event_ids((screenshot.id,))
