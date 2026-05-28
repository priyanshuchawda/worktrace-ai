from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from worktrace_agent.ai.model_availability import ModelStatus, check_model_availability
from worktrace_agent.ai.model_cache import ModelDownloadSpec
from worktrace_agent.capture.audio_transcription import (
    AudioSegment,
    AudioTranscriptionPolicy,
    transcribe_audio_segment,
)
from worktrace_agent.capture.faster_whisper_runtime import (
    DEFAULT_FASTER_WHISPER_MANIFEST,
    DISTIL_WHISPER_MANIFEST,
    FasterWhisperRuntimeConfig,
    FasterWhisperRuntimeError,
    FasterWhisperTranscriptionEngine,
    build_faster_whisper_availability_config,
    build_faster_whisper_download_spec,
)
from worktrace_agent.privacy.redaction import PRIVACY_TEST_CORPUS, REDACTION_TOKEN

SESSION_ID = "sess_faster_whisper_001"
TIMESTAMP = "2026-05-08T01:35:00+05:30"
HEAVY_AUDIO_MODULES = (
    "faster_whisper",
    "torch",
    "transformers",
    "ctranslate2",
)


def test_faster_whisper_manifests_keep_base_default_and_distil_manual() -> None:
    assert DEFAULT_FASTER_WHISPER_MANIFEST.key == "faster-whisper-base-int8"
    assert DEFAULT_FASTER_WHISPER_MANIFEST.model_name == "base"
    assert DEFAULT_FASTER_WHISPER_MANIFEST.device == "cpu"
    assert DEFAULT_FASTER_WHISPER_MANIFEST.compute_type == "int8"
    assert DEFAULT_FASTER_WHISPER_MANIFEST.laptop_safe_default is True
    assert DEFAULT_FASTER_WHISPER_MANIFEST.auto_download_allowed is False

    assert DISTIL_WHISPER_MANIFEST.key == "distil-whisper-large-v3-int8"
    assert DISTIL_WHISPER_MANIFEST.model_name == "distil-large-v3"
    assert DISTIL_WHISPER_MANIFEST.manual_only is True
    assert DISTIL_WHISPER_MANIFEST.laptop_safe_default is False
    assert DISTIL_WHISPER_MANIFEST.auto_download_allowed is False


def test_faster_whisper_adapter_transcribes_opt_in_segment_and_cleans_temp_file() -> None:
    recognizer = FakeWhisperRecognizer(
        segments=[
            fake_segment(0.0, 1.2, f"Investigated {PRIVACY_TEST_CORPUS[0]}"),
            fake_segment(1.2, 2.0, "and fixed tests."),
        ],
        language="en",
        language_probability=0.91,
    )
    engine = FasterWhisperTranscriptionEngine(
        config=FasterWhisperRuntimeConfig(model_name="base"),
        recognizer=recognizer,
    )

    result = transcribe_audio_segment(
        audio_segment(source_event_id="evt_audio_opt_in"),
        policy=AudioTranscriptionPolicy(enabled=True),
        engine=engine,
    )

    assert result.status == "transcribed"
    assert result.transcript is not None
    assert result.transcript.engine_name == "faster-whisper:base"
    assert result.transcript.evidence_event_ids == ("evt_audio_opt_in",)
    assert REDACTION_TOKEN in result.transcript.text
    assert PRIVACY_TEST_CORPUS[0] not in result.transcript.text
    assert result.transcript.confidence == 0.91
    assert result.transcript.metadata["language"] == "en"
    assert result.transcript.metadata["segment_count"] == 2

    assert len(recognizer.calls) == 1
    call = recognizer.calls[0]
    assert call["beam_size"] == 5
    assert call["vad_filter"] is True
    temp_path = Path(str(call["path"]))
    assert temp_path.suffix == ".wav"
    assert temp_path.exists() is False


def test_faster_whisper_runtime_failure_is_safe_through_policy() -> None:
    engine = FasterWhisperTranscriptionEngine(
        config=FasterWhisperRuntimeConfig(model_name="base"),
        recognizer=RaisingWhisperRecognizer(RuntimeError(f"boom {PRIVACY_TEST_CORPUS[0]}")),
    )

    result = transcribe_audio_segment(
        audio_segment(),
        policy=AudioTranscriptionPolicy(enabled=True),
        engine=engine,
    )

    assert result.status == "failed"
    assert result.transcript is None
    assert result.user_message == "Audio transcription failed safely."
    assert PRIVACY_TEST_CORPUS[0] not in result.user_message


def test_real_faster_whisper_binding_requires_local_model_path_before_import() -> None:
    for module_name in HEAVY_AUDIO_MODULES:
        sys.modules.pop(module_name, None)

    engine = FasterWhisperTranscriptionEngine(config=FasterWhisperRuntimeConfig())

    with pytest.raises(FasterWhisperRuntimeError, match="not installed"):
        engine.transcribe(audio_segment())

    assert not any(module_name in sys.modules for module_name in HEAVY_AUDIO_MODULES)


def test_faster_whisper_adapter_rejects_empty_transcript() -> None:
    engine = FasterWhisperTranscriptionEngine(
        config=FasterWhisperRuntimeConfig(model_name="base"),
        recognizer=FakeWhisperRecognizer(
            segments=[fake_segment(0.0, 0.5, "   ")],
            language="en",
            language_probability=0.9,
        ),
    )

    with pytest.raises(FasterWhisperRuntimeError, match="empty transcript"):
        engine.transcribe(audio_segment())


def test_faster_whisper_adapter_rejects_invalid_language_probability() -> None:
    engine = FasterWhisperTranscriptionEngine(
        config=FasterWhisperRuntimeConfig(model_name="base"),
        recognizer=FakeWhisperRecognizer(
            segments=[fake_segment(0.0, 0.5, "hello")],
            language="en",
            language_probability=1.5,
        ),
    )

    with pytest.raises(FasterWhisperRuntimeError, match="language probability"):
        engine.transcribe(audio_segment())


def test_faster_whisper_missing_model_maps_to_not_installed(tmp_path: Path) -> None:
    availability = check_model_availability(
        build_faster_whisper_availability_config(model_path=tmp_path / "missing-model")
    )

    assert availability.model_name == "base"
    assert availability.status is ModelStatus.NOT_INSTALLED
    assert availability.can_record is True
    assert availability.can_generate_report is False


def test_faster_whisper_download_spec_is_manual_only_metadata() -> None:
    spec = build_faster_whisper_download_spec()

    assert isinstance(spec, ModelDownloadSpec)
    assert spec.model_id == "faster-whisper/base-int8"
    assert spec.filename == "faster-whisper-base-int8.ct2"
    assert spec.expected_bytes > 0
    assert spec.source_url is None
    assert spec.manual_install_instructions is not None


def test_faster_whisper_config_and_fake_runtime_do_not_import_heavy_modules(tmp_path: Path) -> None:
    for module_name in HEAVY_AUDIO_MODULES:
        sys.modules.pop(module_name, None)

    build_faster_whisper_availability_config(model_path=tmp_path / "missing-model")
    build_faster_whisper_download_spec()
    engine = FasterWhisperTranscriptionEngine(
        config=FasterWhisperRuntimeConfig(model_name="base"),
        recognizer=FakeWhisperRecognizer(
            segments=[fake_segment(0.0, 0.5, "safe transcript")],
            language="en",
            language_probability=0.8,
        ),
    )
    engine.transcribe(audio_segment())

    assert not any(module_name in sys.modules for module_name in HEAVY_AUDIO_MODULES)


def audio_segment(*, source_event_id: str | None = None) -> AudioSegment:
    return AudioSegment(
        id="audio_segment_fw_001",
        session_id=SESSION_ID,
        source_event_id=source_event_id,
        started_at=TIMESTAMP,
        ended_at="2026-05-08T01:35:04+05:30",
        audio_bytes=b"fake-wav-bytes",
        mime_type="audio/wav",
    )


def fake_segment(start: float, end: float, text: str) -> object:
    return SimpleNamespace(start=start, end=end, text=text)


class FakeWhisperRecognizer:
    def __init__(
        self,
        *,
        segments: list[object],
        language: str,
        language_probability: float,
    ) -> None:
        self.segments = segments
        self.language = language
        self.language_probability = language_probability
        self.calls: list[dict[str, object]] = []

    def transcribe_file(
        self,
        *,
        audio_path: Path,
        config: FasterWhisperRuntimeConfig,
    ) -> tuple[list[object], object]:
        self.calls.append(
            {
                "path": audio_path,
                "beam_size": config.beam_size,
                "vad_filter": config.vad_filter,
            }
        )
        return self.segments, SimpleNamespace(
            language=self.language,
            language_probability=self.language_probability,
        )


class RaisingWhisperRecognizer:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def transcribe_file(
        self,
        *,
        audio_path: Path,
        config: FasterWhisperRuntimeConfig,
    ) -> tuple[list[object], object]:
        raise self.error
