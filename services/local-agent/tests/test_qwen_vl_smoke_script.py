from __future__ import annotations

import json

from worktrace_agent.ai.qwen_vl_runtime import QwenVlJsonTransport
from worktrace_agent.scripts.smoke_qwen_vl_selected_frame import run_qwen_vl_smoke


def test_qwen_vl_smoke_skips_without_configured_endpoint() -> None:
    result = run_qwen_vl_smoke(base_url=None)

    assert result.status == "skipped"
    assert result.model_name == "Qwen/Qwen3-VL-2B-Instruct"
    assert result.endpoint == "not_configured"
    assert result.evidence_ids == ()
    assert result.privacy_leak_count == 0
    assert "not configured" in (result.reason or "")


def test_qwen_vl_smoke_passes_with_fake_selected_frame_runtime() -> None:
    transport = FakeQwenVlTransport()

    result = run_qwen_vl_smoke(
        base_url="http://127.0.0.1:22002",
        transport=transport,
    )
    serialized = json.dumps(result.to_public_dict(), sort_keys=True)

    assert result.status == "passed"
    assert result.model_name == "Qwen/Qwen3-VL-2B-Instruct"
    assert result.endpoint == "127.0.0.1"
    assert result.evidence_ids == ("evt_qwen_vl_smoke_frame",)
    assert result.privacy_leak_count == 0
    assert result.title == "Selected traceback frame"
    assert "image_bytes" not in serialized
    assert "data:image" not in serialized
    assert "Analyze only this explicitly selected" not in serialized
    assert transport.urls == ["http://127.0.0.1:22002/v1/chat/completions"]


class FakeQwenVlTransport(QwenVlJsonTransport):
    def __init__(self) -> None:
        self.urls: list[str] = []

    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: int,
    ) -> object:
        self.urls.append(url)
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "title": "Selected traceback frame",
                                "description": "The selected frame shows a pytest traceback.",
                                "confidence": 0.84,
                            }
                        )
                    }
                }
            ]
        }
