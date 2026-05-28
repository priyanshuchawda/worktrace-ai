from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from worktrace_agent.capture.faster_whisper_runtime import (
    FasterWhisperRuntimeConfig,
    WhisperRecognizer,
)
from worktrace_agent.scripts.smoke_faster_whisper_local_path import (
    run_faster_whisper_smoke,
)


def test_faster_whisper_smoke_skips_without_configured_model_path() -> None:
    result = run_faster_whisper_smoke(model_path=None)

    assert result.status == "skipped"
    assert result.model_name == "base"
    assert result.model_path == "not_configured"
    assert result.evidence_ids == ()
    assert result.transcript_char_count == 0
    assert result.privacy_leak_count == 0
    assert "not configured" in (result.reason or "")


def test_faster_whisper_smoke_passes_with_fake_local_path_runtime(tmp_path: Path) -> None:
    model_path = tmp_path / "faster-whisper-base-ct2"
    model_path.mkdir()
    recognizer = FakeWhisperRecognizer()

    result = run_faster_whisper_smoke(
        model_path=model_path,
        recognizer=recognizer,
    )
    serialized = json.dumps(result.to_public_dict(), sort_keys=True)

    assert result.status == "passed"
    assert result.model_name == "base"
    assert result.model_path == "configured"
    assert result.evidence_ids == ("evt_faster_whisper_smoke_audio",)
    assert result.transcript_char_count == len("fixed tests and updated docs")
    assert result.language == "en"
    assert result.privacy_leak_count == 0
    assert "fixed tests and updated docs" not in serialized
    assert "fake-wav-bytes" not in serialized
    assert "audio_bytes" not in serialized
    assert recognizer.model_paths == [model_path]
    assert recognizer.beam_sizes == [5]


class FakeWhisperRecognizer(WhisperRecognizer):
    def __init__(self) -> None:
        self.model_paths: list[Path | None] = []
        self.beam_sizes: list[int] = []

    def transcribe_file(
        self,
        *,
        audio_path: Path,
        config: FasterWhisperRuntimeConfig,
    ) -> tuple[list[object], object]:
        self.model_paths.append(config.model_path)
        self.beam_sizes.append(config.beam_size)
        assert audio_path.suffix == ".wav"
        return [
            SimpleNamespace(start=0.0, end=1.0, text="fixed tests"),
            SimpleNamespace(start=1.0, end=2.0, text="and updated docs"),
        ], SimpleNamespace(language="en", language_probability=0.88)
