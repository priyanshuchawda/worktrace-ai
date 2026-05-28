from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, cast

from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact
from worktrace_agent.privacy.policy import PrivacyPolicy
from worktrace_agent.privacy.redaction import (
    PRIVACY_TEST_CORPUS,
    SECRET_VALUES,
    redact_json_value,
    redact_text,
)

HIGH_VALUE_MARKERS = (
    "terminal",
    "powershell",
    "cmd",
    "traceback",
    "exception",
    "error",
    "failed",
    "failure",
    "pytest",
    "test",
)
DEFAULT_MAX_OCR_JOBS_PER_SESSION = 200


class OcrSkipReason(StrEnum):
    UNCHANGED = "unchanged"
    NOT_HIGH_VALUE = "not_high_value"
    PRIVACY_POLICY = "privacy_policy"
    SECRET_RISK = "secret_risk"  # nosec B105
    SESSION_LIMIT = "session_limit"
    RUNTIME_FAILED = "runtime_failed"


@dataclass(frozen=True)
class OcrCandidate:
    screenshot: ScreenshotArtifact
    image_bytes: bytes
    app_name: str
    window_title: str


@dataclass(frozen=True)
class OcrEngineResult:
    text: str
    confidence: float
    metadata: dict[str, object] | None = None


class OcrEngine(Protocol):
    engine_name: str

    def recognize(self, candidate: OcrCandidate) -> OcrEngineResult:
        """Extract text from a selected screenshot candidate."""
        ...


@dataclass(frozen=True)
class OcrResult:
    id: str
    session_id: str
    screenshot_id: str
    source_event_id: str | None
    timestamp: str
    text: str
    confidence: float
    engine_name: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class OcrDecision:
    result: OcrResult | None
    skipped: OcrSkipReason | None


class SelectiveOcrWorker:
    def __init__(
        self,
        *,
        privacy_policy: PrivacyPolicy | None = None,
        max_jobs_per_session: int = DEFAULT_MAX_OCR_JOBS_PER_SESSION,
    ) -> None:
        self._privacy_policy = privacy_policy or PrivacyPolicy()
        if max_jobs_per_session <= 0:
            raise ValueError("max_jobs_per_session must be greater than zero")
        self._max_jobs_per_session = max_jobs_per_session
        self._last_visual_hash_by_session: dict[str, str] = {}
        self._processed_jobs_by_session: dict[str, int] = {}

    def process_candidate(self, candidate: OcrCandidate, *, engine: OcrEngine) -> OcrDecision:
        validate_ocr_candidate(candidate)
        if not self._privacy_policy.should_capture_app(candidate.app_name):
            return OcrDecision(result=None, skipped=OcrSkipReason.PRIVACY_POLICY)
        if is_secret_risk_candidate(candidate):
            return OcrDecision(result=None, skipped=OcrSkipReason.SECRET_RISK)
        if not is_high_value_candidate(candidate):
            return OcrDecision(result=None, skipped=OcrSkipReason.NOT_HIGH_VALUE)

        previous_hash = self._last_visual_hash_by_session.get(candidate.screenshot.session_id)
        if previous_hash == candidate.screenshot.visual_hash:
            return OcrDecision(result=None, skipped=OcrSkipReason.UNCHANGED)
        processed_jobs = self._processed_jobs_by_session.get(candidate.screenshot.session_id, 0)
        if processed_jobs >= self._max_jobs_per_session:
            return OcrDecision(result=None, skipped=OcrSkipReason.SESSION_LIMIT)

        self._last_visual_hash_by_session[candidate.screenshot.session_id] = (
            candidate.screenshot.visual_hash
        )
        try:
            engine_result = engine.recognize(candidate)
        except Exception:
            return OcrDecision(result=None, skipped=OcrSkipReason.RUNTIME_FAILED)
        self._processed_jobs_by_session[candidate.screenshot.session_id] = processed_jobs + 1
        return OcrDecision(
            result=build_ocr_result(
                candidate=candidate,
                engine_name=engine.engine_name,
                engine_result=engine_result,
            ),
            skipped=None,
        )


def is_high_value_candidate(candidate: OcrCandidate) -> bool:
    searchable = f"{candidate.app_name} {candidate.window_title}".lower()
    return any(marker in searchable for marker in HIGH_VALUE_MARKERS)


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


def is_secret_risk_candidate(candidate: OcrCandidate) -> bool:
    searchable = f"{candidate.app_name} {candidate.window_title}".lower()
    lowered_privacy_values = [value.lower() for value in PRIVACY_TEST_CORPUS + SECRET_VALUES]
    return any(
        marker in searchable for marker in SECRET_RISK_MARKERS + tuple(lowered_privacy_values)
    )


def validate_ocr_candidate(candidate: OcrCandidate) -> None:
    if not candidate.image_bytes:
        raise ValueError("image_bytes must not be empty")
    if not candidate.app_name.strip():
        raise ValueError("app_name must be a non-empty string")
    if not candidate.window_title.strip():
        raise ValueError("window_title must be a non-empty string")


def build_ocr_result(
    *,
    candidate: OcrCandidate,
    engine_name: str,
    engine_result: OcrEngineResult,
) -> OcrResult:
    if engine_result.confidence < 0 or engine_result.confidence > 1:
        raise ValueError("OCR confidence must be between 0 and 1")

    screenshot = candidate.screenshot
    metadata = cast(dict[str, object], redact_json_value(engine_result.metadata or {}))
    metadata["evidence_ids"] = list(evidence_ids_for_ocr_result(screenshot))
    return OcrResult(
        id=f"{screenshot.id}-ocr",
        session_id=screenshot.session_id,
        screenshot_id=screenshot.id,
        source_event_id=screenshot.source_event_id,
        timestamp=screenshot.timestamp,
        text=redact_text(engine_result.text),
        confidence=engine_result.confidence,
        engine_name=redact_text(engine_name),
        metadata=metadata,
    )


def evidence_ids_for_ocr_result(screenshot: ScreenshotArtifact) -> tuple[str, ...]:
    if screenshot.source_event_id is not None and screenshot.source_event_id.strip():
        return (screenshot.source_event_id,)
    return (screenshot.id,)
