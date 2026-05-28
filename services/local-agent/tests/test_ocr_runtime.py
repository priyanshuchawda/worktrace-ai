from __future__ import annotations

import importlib.machinery
import sys
from pathlib import Path
from types import ModuleType

from worktrace_agent.capture.ocr_runtime import (
    OcrRuntimeConfig,
    OcrRuntimeStatus,
    build_paddle_ocr_engine,
    check_ocr_runtime_availability,
)
from worktrace_agent.capture.ocr_worker import OcrCandidate
from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact

HEAVY_OCR_MODULES = (
    "paddle",
    "paddleocr",
    "cv2",
    "onnxruntime",
)


def test_disabled_ocr_runtime_is_safe_and_not_runnable() -> None:
    availability = check_ocr_runtime_availability(
        OcrRuntimeConfig(enabled=False, provider="paddleocr")
    )

    assert availability.status is OcrRuntimeStatus.DISABLED
    assert availability.can_run is False
    assert availability.provider == "paddleocr"
    assert availability.user_message == "OCR runtime is disabled. Recording continues without OCR."


def test_missing_ocr_runtime_returns_unavailable_without_importing_package() -> None:
    for module_name in HEAVY_OCR_MODULES:
        sys.modules.pop(module_name, None)

    availability = check_ocr_runtime_availability(
        OcrRuntimeConfig(
            enabled=True,
            provider="paddleocr",
            module_name="worktrace_missing_ocr_runtime",
        )
    )

    assert availability.status is OcrRuntimeStatus.UNAVAILABLE
    assert availability.can_run is False
    assert "not installed" in availability.user_message
    assert not any(module_name in sys.modules for module_name in HEAVY_OCR_MODULES)


def test_available_ocr_runtime_is_ready_without_importing_heavy_module() -> None:
    for module_name in HEAVY_OCR_MODULES:
        sys.modules.pop(module_name, None)

    availability = check_ocr_runtime_availability(
        OcrRuntimeConfig(enabled=True, provider="fake-ocr", module_name="json")
    )

    assert availability.status is OcrRuntimeStatus.READY
    assert availability.can_run is True
    assert availability.provider == "fake-ocr"
    assert not any(module_name in sys.modules for module_name in HEAVY_OCR_MODULES)


def test_build_paddle_ocr_engine_returns_unavailable_when_runtime_missing() -> None:
    binding = build_paddle_ocr_engine(
        OcrRuntimeConfig(
            enabled=True,
            provider="paddleocr",
            module_name="worktrace_missing_ocr_runtime",
        )
    )

    assert binding.engine is None
    assert binding.availability.status is OcrRuntimeStatus.UNAVAILABLE
    assert binding.availability.can_run is False


def test_build_paddle_ocr_engine_with_fake_recognizer_parses_text_and_confidence(
    tmp_path: Path,
) -> None:
    recognizer = FakePredictRecognizer(
        [
            {
                "res": {
                    "rec_texts": ["Traceback detected", "AssertionError"],
                    "rec_scores": [0.9, 0.7],
                }
            }
        ]
    )
    binding = build_paddle_ocr_engine(
        OcrRuntimeConfig(enabled=True, provider="paddleocr", module_name="json"),
        recognizer_factory=lambda: recognizer,
    )
    candidate = build_candidate(image_bytes=b"fake-image-bytes")

    assert binding.engine is not None
    result = binding.engine.recognize(candidate)

    assert result.text == "Traceback detected\nAssertionError"
    assert result.confidence == 0.8
    assert result.metadata == {"line_count": 2}
    assert recognizer.last_input_path is not None
    assert recognizer.last_input_path.exists() is False


def test_build_paddle_ocr_engine_uses_documented_predict_api_options() -> None:
    module_name = "worktrace_fake_paddleocr_runtime"
    fake_module = ModuleType(module_name)
    fake_module.__spec__ = importlib.machinery.ModuleSpec(module_name, loader=None)
    fake_module.PaddleOCR = FakePaddleOcrClass  # type: ignore[attr-defined]
    sys.modules[module_name] = fake_module
    try:
        binding = build_paddle_ocr_engine(
            OcrRuntimeConfig(enabled=True, provider="paddleocr", module_name=module_name)
        )
        candidate = build_candidate(image_bytes=b"fake-image-bytes")

        assert binding.engine is not None
        result = binding.engine.recognize(candidate)

        assert result.text == "Traceback detected"
        assert FakePaddleOcrClass.last_kwargs == {
            "lang": "en",
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        }
        assert FakePaddleOcrClass.last_instance is not None
        assert FakePaddleOcrClass.last_instance.predict_call_count == 1
    finally:
        sys.modules.pop(module_name, None)


def test_paddle_engine_failure_is_safe(tmp_path: Path) -> None:
    binding = build_paddle_ocr_engine(
        OcrRuntimeConfig(enabled=True, provider="paddleocr", module_name="json"),
        recognizer_factory=lambda: RaisingRecognizer(),
    )
    candidate = build_candidate(image_bytes=b"fake-image-bytes")

    assert binding.engine is not None
    try:
        binding.engine.recognize(candidate)
    except RuntimeError as error:
        assert str(error) == "OCR runtime failed safely."
    else:
        raise AssertionError("runtime failure should raise a safe runtime error")


def build_candidate(*, image_bytes: bytes) -> OcrCandidate:
    return OcrCandidate(
        screenshot=ScreenshotArtifact(
            id="shot_ocr_runtime",
            session_id="sess_ocr_runtime_001",
            source_event_id="evt_ocr_runtime",
            timestamp="2026-05-08T01:00:00+05:30",
            width=1280,
            height=720,
            stored_width=1280,
            stored_height=720,
            byte_size=len(image_bytes),
            content_hash="content-hash",
            visual_hash="visual-hash",
            storage_path="screenshots/shot_ocr_runtime.png",
        ),
        image_bytes=image_bytes,
        app_name="Windows Terminal",
        window_title="pytest traceback",
    )


class FakePredictRecognizer:
    def __init__(self, response: object) -> None:
        self.response = response
        self.last_input_path: Path | None = None

    def predict(self, image_path: str) -> object:
        self.last_input_path = Path(image_path)
        return self.response


class RaisingRecognizer:
    def predict(self, image_path: str) -> object:
        raise RuntimeError("engine crashed")


class FakePaddleOcrClass:
    last_kwargs: dict[str, object] | None = None
    last_instance: FakePaddleOcrClass | None = None

    def __init__(self, **kwargs: object) -> None:
        FakePaddleOcrClass.last_kwargs = kwargs
        FakePaddleOcrClass.last_instance = self
        self.predict_call_count = 0

    def predict(self, image_path: str) -> object:
        self.predict_call_count += 1
        return [{"res": {"rec_texts": ["Traceback detected"], "rec_scores": [0.9]}}]
