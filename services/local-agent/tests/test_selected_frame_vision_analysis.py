import sys

from worktrace_agent.ai.vision_analysis import (
    VisionAnalysisRequest,
    VisionAnalyzerResult,
    VisionCancellationToken,
    analyze_selected_frame,
    is_error_dialog_candidate,
)
from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact
from worktrace_agent.privacy.redaction import (
    PRIVACY_TEST_CORPUS,
    REDACTION_TOKEN,
    count_privacy_leaks,
)

SESSION_ID = "sess_vision_001"
TIMESTAMP = "2026-05-06T11:00:00+05:30"
HEAVY_VISION_MODULES = (
    "torch",
    "transformers",
    "qwen_vl_utils",
    "paddleocr",
    "cv2",
)


def test_non_selected_frame_is_skipped_without_analyzer_call() -> None:
    analyzer = FakeVisionAnalyzer(
        VisionAnalyzerResult(
            title="Not used",
            description="Not used",
            confidence=0.9,
        )
    )

    decision = analyze_selected_frame(
        vision_request(selected=False),
        analyzer=analyzer,
    )

    assert decision.status == "skipped_not_selected"
    assert decision.result is None
    assert decision.user_message == "Vision analysis requires a selected screenshot."
    assert analyzer.call_count == 0


def test_secret_risk_screen_refuses_detailed_extraction_without_analyzer_call() -> None:
    analyzer = FakeVisionAnalyzer(
        VisionAnalyzerResult(
            title="Not used",
            description="Not used",
            confidence=0.9,
        )
    )

    decision = analyze_selected_frame(
        vision_request(
            ocr_text=f".env editor shows {PRIVACY_TEST_CORPUS[0]}",
            window_title="settings.py secret token",
        ),
        analyzer=analyzer,
    )

    assert decision.status == "refused_secret_risk"
    assert decision.result is None
    assert "secret" in decision.user_message.lower()
    assert count_privacy_leaks(decision.user_message) == 0
    assert analyzer.call_count == 0


def test_cancelled_request_does_not_call_analyzer() -> None:
    analyzer = FakeVisionAnalyzer(
        VisionAnalyzerResult(
            title="Not used",
            description="Not used",
            confidence=0.9,
        )
    )

    decision = analyze_selected_frame(
        vision_request(),
        analyzer=analyzer,
        cancellation_token=VisionCancellationToken(cancelled=True),
    )

    assert decision.status == "cancelled"
    assert decision.result is None
    assert analyzer.call_count == 0


def test_error_dialog_selected_frame_is_analyzed_with_evidence_and_redaction() -> None:
    analyzer = FakeVisionAnalyzer(
        VisionAnalyzerResult(
            title="Python traceback dialog",
            description=f"Detected a pytest failure dialog with {PRIVACY_TEST_CORPUS[1]}",
            confidence=0.86,
            metadata={"screen_text": f"Error details {PRIVACY_TEST_CORPUS[2]}"},
        )
    )

    request = vision_request(
        source_event_id="evt_screenshot_error",
        app_name="Windows Terminal",
        window_title="pytest traceback error dialog",
        ocr_text="Traceback: AssertionError",
    )
    decision = analyze_selected_frame(request, analyzer=analyzer)

    assert decision.status == "analyzed"
    assert decision.result is not None
    assert decision.result.evidence_event_ids == ("evt_screenshot_error",)
    assert decision.result.kind == "error_dialog"
    assert REDACTION_TOKEN in decision.result.description
    assert count_privacy_leaks(decision.result.description) == 0
    assert count_privacy_leaks(decision.result.metadata) == 0
    assert analyzer.call_count == 1
    assert analyzer.requests[0].image_bytes == b"fake-selected-frame"


def test_selected_frame_without_source_event_uses_screenshot_evidence_id() -> None:
    decision = analyze_selected_frame(
        vision_request(source_event_id=None),
        analyzer=FakeVisionAnalyzer(
            VisionAnalyzerResult(
                title="Selected frame",
                description="Selected screenshot reviewed.",
                confidence=0.8,
            )
        ),
    )

    assert decision.status == "analyzed"
    assert decision.result is not None
    assert decision.result.evidence_event_ids == ("shot_vision_001",)


def test_analyzer_failure_is_safe_and_redacted() -> None:
    decision = analyze_selected_frame(
        vision_request(),
        analyzer=RaisingVisionAnalyzer(RuntimeError(f"provider failed {PRIVACY_TEST_CORPUS[0]}")),
    )

    assert decision.status == "failed"
    assert decision.result is None
    assert decision.failure_category == "analyzer_failed"
    assert "provider failed" not in decision.user_message
    assert count_privacy_leaks(decision.user_message) == 0


def test_error_dialog_detection_uses_window_and_ocr_context() -> None:
    assert (
        is_error_dialog_candidate(
            app_name="PowerShell",
            window_title="pytest failure",
            ocr_text="Traceback AssertionError",
        )
        is True
    )
    assert (
        is_error_dialog_candidate(
            app_name="Chrome",
            window_title="Documentation",
            ocr_text="Installation guide",
        )
        is False
    )


def test_selected_frame_vision_does_not_import_heavy_vlm_modules() -> None:
    for module_name in HEAVY_VISION_MODULES:
        sys.modules.pop(module_name, None)

    analyze_selected_frame(
        vision_request(),
        analyzer=FakeVisionAnalyzer(
            VisionAnalyzerResult(
                title="Safe analysis",
                description="Selected screenshot reviewed.",
                confidence=0.9,
            )
        ),
    )

    assert not any(module_name in sys.modules for module_name in HEAVY_VISION_MODULES)


def vision_request(
    *,
    selected: bool = True,
    source_event_id: str | None = "evt_selected_frame",
    app_name: str = "VS Code",
    window_title: str = "test failure",
    ocr_text: str = "AssertionError in pytest output",
) -> VisionAnalysisRequest:
    return VisionAnalysisRequest(
        screenshot=build_screenshot(source_event_id=source_event_id),
        image_bytes=b"fake-selected-frame",
        selected=selected,
        app_name=app_name,
        window_title=window_title,
        ocr_text=ocr_text,
    )


def build_screenshot(*, source_event_id: str | None) -> ScreenshotArtifact:
    return ScreenshotArtifact(
        id="shot_vision_001",
        session_id=SESSION_ID,
        source_event_id=source_event_id,
        timestamp=TIMESTAMP,
        width=1280,
        height=720,
        stored_width=1280,
        stored_height=720,
        byte_size=1024,
        content_hash="content-shot-vision-001",
        visual_hash="visionhash",
        storage_path="screenshots/shot_vision_001.rgb",
    )


class FakeVisionAnalyzer:
    analyzer_name = "fake-vlm"
    analyzer_version = "test-v1"

    def __init__(self, result: VisionAnalyzerResult) -> None:
        self.result = result
        self.requests: list[VisionAnalysisRequest] = []

    @property
    def call_count(self) -> int:
        return len(self.requests)

    def analyze(self, request: VisionAnalysisRequest) -> VisionAnalyzerResult:
        self.requests.append(request)
        return self.result


class RaisingVisionAnalyzer:
    analyzer_name = "failing-vlm"
    analyzer_version = "test-v1"

    def __init__(self, error: Exception) -> None:
        self.error = error

    def analyze(self, request: VisionAnalysisRequest) -> VisionAnalyzerResult:
        raise self.error
