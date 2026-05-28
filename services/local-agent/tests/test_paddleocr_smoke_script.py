from __future__ import annotations

import json

from worktrace_agent.scripts.smoke_paddleocr_sample import (
    run_paddleocr_smoke,
)


def test_paddleocr_smoke_skips_when_runtime_is_missing() -> None:
    result = run_paddleocr_smoke(module_name="worktrace_missing_paddleocr_runtime")

    assert result.status == "skipped"
    assert result.provider == "paddleocr"
    assert "not installed" in (result.reason or "")
    assert result.privacy_leak_count == 0
    assert result.evidence_ids == ()


def test_paddleocr_smoke_passes_with_fake_runtime_and_local_sample() -> None:
    result = run_paddleocr_smoke(
        module_name="json",
        recognizer_factory=lambda: FakeRecognizer(),
    )
    serialized = json.dumps(result.to_public_dict(), sort_keys=True)

    assert result.status == "passed"
    assert result.provider == "paddleocr"
    assert result.evidence_ids == ("shot_paddleocr_smoke",)
    assert result.privacy_leak_count == 0
    assert result.line_count == 2
    assert "Traceback passed" in (result.text_preview or "")
    assert "image_bytes" not in serialized
    assert "prompt" not in serialized.lower()


class FakeRecognizer:
    def predict(self, image_path: str) -> object:
        if not image_path.endswith(".png"):
            raise AssertionError("smoke sample must be written as a PNG")
        return [
            {
                "res": {
                    "rec_texts": ["Traceback passed", "No remote OCR"],
                    "rec_scores": [0.92, 0.88],
                }
            }
        ]
