from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

import pytest

from worktrace_agent.ai.model_availability import ModelStatus, check_model_availability
from worktrace_agent.ai.qwen_vl_runtime import (
    DEFAULT_QWEN_VL_MANIFEST,
    QWEN_VL_4B_MANIFEST,
    QwenVlRuntimeConfig,
    QwenVlRuntimeError,
    QwenVlSelectedFrameAnalyzer,
    UrllibQwenVlTransport,
    build_qwen_vl_availability_config,
    build_qwen_vl_runtime_config,
)
from worktrace_agent.ai.vision_analysis import VisionAnalysisRequest
from worktrace_agent.capture.screenshot_sampler import ScreenshotArtifact
from worktrace_agent.privacy.redaction import PRIVACY_TEST_CORPUS, REDACTION_TOKEN

SESSION_ID = "sess_qwen_vl_001"
TIMESTAMP = "2026-05-08T01:30:00+05:30"
HEAVY_VLM_MODULES = (
    "torch",
    "transformers",
    "qwen_vl_utils",
    "accelerate",
)


@pytest.mark.parametrize(
    "base_url",
    [
        "https://example.com",
        "http://user:password@localhost:22002",
        "http://localhost:22002/v1",
    ],
)
def test_qwen_vl_runtime_rejects_non_local_or_path_base_urls(base_url: str) -> None:
    with pytest.raises(ValueError):
        QwenVlSelectedFrameAnalyzer(
            config=QwenVlRuntimeConfig(base_url=base_url),
            transport=FakeTransport(valid_chat_response()),
        )


def test_urllib_qwen_vl_transport_rejects_non_http_url_before_request() -> None:
    transport = UrllibQwenVlTransport()

    with pytest.raises(ValueError, match="local HTTP"):
        transport.post_json(
            url="file:///tmp/qwen-vl-response.json",
            payload={"messages": []},
            timeout_seconds=1,
        )


def test_qwen_vl_manifests_prefer_2b_and_keep_4b_manual() -> None:
    assert DEFAULT_QWEN_VL_MANIFEST.key == "qwen3-vl-2b-instruct"
    assert DEFAULT_QWEN_VL_MANIFEST.hugging_face_model_id == "Qwen/Qwen3-VL-2B-Instruct"
    assert DEFAULT_QWEN_VL_MANIFEST.laptop_safe_default is True
    assert DEFAULT_QWEN_VL_MANIFEST.auto_download_allowed is False

    assert QWEN_VL_4B_MANIFEST.key == "qwen3-vl-4b-instruct"
    assert QWEN_VL_4B_MANIFEST.hugging_face_model_id == "Qwen/Qwen3-VL-4B-Instruct"
    assert QWEN_VL_4B_MANIFEST.laptop_safe_default is False
    assert QWEN_VL_4B_MANIFEST.manual_only is True
    assert QWEN_VL_4B_MANIFEST.auto_download_allowed is False


def test_qwen_vl_runtime_posts_selected_frame_to_local_chat_transport() -> None:
    transport = FakeTransport(valid_chat_response())
    analyzer = QwenVlSelectedFrameAnalyzer(
        config=build_qwen_vl_runtime_config(base_url="http://127.0.0.1:22002"),
        transport=transport,
    )

    result = analyzer.analyze(
        selected_frame_request(
            ocr_text=f"Traceback with {PRIVACY_TEST_CORPUS[0]}",
        )
    )

    assert result.title == "Pytest failure dialog"
    assert result.description == "The selected screenshot shows a pytest assertion failure."
    assert result.confidence == 0.82
    assert result.metadata == {"ui_state": "terminal_error"}

    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request["url"] == "http://127.0.0.1:22002/v1/chat/completions"
    assert request["timeout_seconds"] == 60
    payload = cast(dict[str, object], request["payload"])
    assert payload["model"] == "Qwen/Qwen3-VL-2B-Instruct"
    assert payload["max_tokens"] == 256
    assert payload["temperature"] == 0.1

    messages = cast(list[object], payload["messages"])
    message = cast(dict[str, object], messages[0])
    content = cast(list[object], message["content"])
    image_content = cast(dict[str, object], content[0])
    image_url = cast(dict[str, object], image_content["image_url"])
    text_content = cast(dict[str, object], content[1])
    text = str(text_content["text"])

    assert image_content["type"] == "image_url"
    assert str(image_url["url"]).startswith("data:image/png;base64,")
    assert text_content["type"] == "text"
    assert "shot_qwen_vl_001" in text
    assert REDACTION_TOKEN in text
    assert PRIVACY_TEST_CORPUS[0] not in text


def test_qwen_vl_runtime_plain_text_response_is_safe_result() -> None:
    analyzer = QwenVlSelectedFrameAnalyzer(
        config=build_qwen_vl_runtime_config(base_url="http://localhost:22002"),
        transport=FakeTransport(
            {"choices": [{"message": {"content": "Selected frame shows a build error."}}]}
        ),
    )

    result = analyzer.analyze(selected_frame_request())

    assert result.title == "Qwen3-VL selected frame"
    assert result.description == "Selected frame shows a build error."
    assert result.confidence == 0.7


def test_qwen_vl_runtime_malformed_response_fails_safely() -> None:
    analyzer = QwenVlSelectedFrameAnalyzer(
        config=build_qwen_vl_runtime_config(base_url="http://localhost:22002"),
        transport=FakeTransport({"choices": []}),
    )

    with pytest.raises(QwenVlRuntimeError, match="failed safely"):
        analyzer.analyze(selected_frame_request())


def test_qwen_vl_runtime_refuses_oversized_image_before_transport() -> None:
    transport = FakeTransport(valid_chat_response())
    analyzer = QwenVlSelectedFrameAnalyzer(
        config=QwenVlRuntimeConfig(base_url="http://localhost:22002", max_image_bytes=4),
        transport=transport,
    )

    with pytest.raises(QwenVlRuntimeError, match="too large"):
        analyzer.analyze(selected_frame_request(image_bytes=b"larger-than-four"))

    assert transport.requests == []


def test_qwen_vl_missing_model_maps_to_not_installed(tmp_path: Path) -> None:
    availability = check_model_availability(
        build_qwen_vl_availability_config(model_path=tmp_path / "missing-qwen-vl")
    )

    assert availability.model_name == "Qwen/Qwen3-VL-2B-Instruct"
    assert availability.status is ModelStatus.NOT_INSTALLED
    assert availability.can_record is True
    assert availability.can_generate_report is False


def test_qwen_vl_runtime_does_not_import_heavy_modules() -> None:
    for module_name in HEAVY_VLM_MODULES:
        sys.modules.pop(module_name, None)

    analyzer = QwenVlSelectedFrameAnalyzer(
        config=build_qwen_vl_runtime_config(base_url="http://localhost:22002"),
        transport=FakeTransport(valid_chat_response()),
    )
    analyzer.analyze(selected_frame_request())

    assert not any(module_name in sys.modules for module_name in HEAVY_VLM_MODULES)


def selected_frame_request(
    *,
    image_bytes: bytes = b"fake-png-bytes",
    ocr_text: str | None = "AssertionError in pytest output",
) -> VisionAnalysisRequest:
    return VisionAnalysisRequest(
        screenshot=ScreenshotArtifact(
            id="shot_qwen_vl_001",
            session_id=SESSION_ID,
            source_event_id="evt_qwen_vl_selected",
            timestamp=TIMESTAMP,
            width=1280,
            height=720,
            stored_width=1280,
            stored_height=720,
            byte_size=len(image_bytes),
            content_hash="content-qwen-vl",
            visual_hash="visual-qwen-vl",
            storage_path="screenshots/shot_qwen_vl_001.png",
        ),
        image_bytes=image_bytes,
        selected=True,
        app_name="Windows Terminal",
        window_title="pytest traceback",
        ocr_text=ocr_text,
    )


def valid_chat_response() -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "title": "Pytest failure dialog",
                            "description": (
                                "The selected screenshot shows a pytest assertion failure."
                            ),
                            "confidence": 0.82,
                            "metadata": {"ui_state": "terminal_error"},
                        }
                    )
                }
            }
        ]
    }


class FakeTransport:
    def __init__(self, response: object) -> None:
        self.response = response
        self.requests: list[dict[str, object]] = []

    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: int,
    ) -> object:
        self.requests.append(
            {
                "url": url,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.response
