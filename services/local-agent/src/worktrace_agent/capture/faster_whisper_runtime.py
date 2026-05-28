from __future__ import annotations

import importlib
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from worktrace_agent.ai.model_availability import ModelAvailabilityConfig, ModelProvider
from worktrace_agent.ai.model_cache import ModelDownloadSpec
from worktrace_agent.capture.audio_transcription import (
    AudioSegment,
    TranscriptionEngineResult,
)
from worktrace_agent.privacy.redaction import redact_text
from worktrace_agent.timeline.deterministic import require_confidence, require_non_empty

DEFAULT_FASTER_WHISPER_MODEL_NAME = "base"
DISTIL_WHISPER_MODEL_NAME = "distil-large-v3"
DEFAULT_FASTER_WHISPER_EXPECTED_BYTES = 150 * 1024 * 1024
DISTIL_WHISPER_EXPECTED_BYTES = 1_500 * 1024 * 1024
DEFAULT_FASTER_WHISPER_BEAM_SIZE = 5
DEFAULT_FASTER_WHISPER_MAX_AUDIO_BYTES = 25 * 1024 * 1024


class FasterWhisperRuntimeError(RuntimeError):
    """Safe user-readable faster-whisper runtime failure."""


class WhisperRecognizer(Protocol):
    def transcribe_file(
        self,
        *,
        audio_path: Path,
        config: FasterWhisperRuntimeConfig,
    ) -> tuple[object, object]:
        """Transcribe a local audio file and return faster-whisper style segments/info."""
        ...


@dataclass(frozen=True)
class FasterWhisperManifest:
    key: str
    model_name: str
    display_name: str
    device: str
    compute_type: str
    laptop_safe_default: bool
    manual_only: bool
    auto_download_allowed: bool
    expected_bytes: int
    safety_note: str


@dataclass(frozen=True)
class FasterWhisperRuntimeConfig:
    model_name: str = DEFAULT_FASTER_WHISPER_MODEL_NAME
    model_path: Path | None = None
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = DEFAULT_FASTER_WHISPER_BEAM_SIZE
    vad_filter: bool = True
    max_audio_bytes: int = DEFAULT_FASTER_WHISPER_MAX_AUDIO_BYTES


DEFAULT_FASTER_WHISPER_MANIFEST = FasterWhisperManifest(
    key="faster-whisper-base-int8",
    model_name=DEFAULT_FASTER_WHISPER_MODEL_NAME,
    display_name="faster-whisper base CPU int8",
    device="cpu",
    compute_type="int8",
    laptop_safe_default=True,
    manual_only=False,
    auto_download_allowed=False,
    expected_bytes=DEFAULT_FASTER_WHISPER_EXPECTED_BYTES,
    safety_note=(
        "CPU int8 base is the laptop-safe default metadata target. "
        "WorkTrace does not download, load, or start it during recording."
    ),
)

DISTIL_WHISPER_MANIFEST = FasterWhisperManifest(
    key="distil-whisper-large-v3-int8",
    model_name=DISTIL_WHISPER_MODEL_NAME,
    display_name="Distil-Whisper large-v3 CPU int8",
    device="cpu",
    compute_type="int8",
    laptop_safe_default=False,
    manual_only=True,
    auto_download_allowed=False,
    expected_bytes=DISTIL_WHISPER_EXPECTED_BYTES,
    safety_note=(
        "Distil-Whisper is optional and manual-only until Windows CPU/RAM benchmarks "
        "prove it is safe for this project."
    ),
)


class FasterWhisperRecognizerBinding:
    def transcribe_file(
        self,
        *,
        audio_path: Path,
        config: FasterWhisperRuntimeConfig,
    ) -> tuple[object, object]:
        if config.model_path is None or not config.model_path.exists():
            raise FasterWhisperRuntimeError("Local faster-whisper model is not installed.")

        try:
            module = importlib.import_module("faster_whisper")
            whisper_model = module.WhisperModel(
                str(config.model_path),
                device=config.device,
                compute_type=config.compute_type,
            )
            segments, info = whisper_model.transcribe(
                str(audio_path),
                beam_size=config.beam_size,
                vad_filter=config.vad_filter,
            )
            return list(segments), info
        except Exception as error:
            raise FasterWhisperRuntimeError(
                "Local faster-whisper runtime failed safely."
            ) from error


class FasterWhisperTranscriptionEngine:
    def __init__(
        self,
        *,
        config: FasterWhisperRuntimeConfig,
        recognizer: WhisperRecognizer | None = None,
    ) -> None:
        _validate_runtime_config(config)
        self._config = config
        self._recognizer = recognizer or FasterWhisperRecognizerBinding()

    @property
    def engine_name(self) -> str:
        return redact_text(f"faster-whisper:{self._config.model_name}")

    def transcribe(self, segment: AudioSegment) -> TranscriptionEngineResult:
        if len(segment.audio_bytes) > self._config.max_audio_bytes:
            raise FasterWhisperRuntimeError("Audio segment is too large for local transcription.")

        suffix = _audio_suffix(segment.mime_type)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as audio_file:
                audio_file.write(segment.audio_bytes)
                temp_path = Path(audio_file.name)

            segments, info = self._recognizer.transcribe_file(
                audio_path=temp_path,
                config=self._config,
            )
            parsed_segments = _parse_segments(segments)
            text = " ".join(str(part["text"]) for part in parsed_segments).strip()
            if not text:
                raise FasterWhisperRuntimeError(
                    "Local faster-whisper returned an empty transcript."
                )
            confidence = _language_probability(info)
            return TranscriptionEngineResult(
                text=redact_text(require_non_empty(text, "transcript_text")),
                confidence=confidence,
                metadata={
                    "language": redact_text(str(getattr(info, "language", "unknown"))),
                    "language_probability": confidence,
                    "segment_count": len(parsed_segments),
                    "segments": parsed_segments,
                    "model_name": redact_text(self._config.model_name),
                    "device": self._config.device,
                    "compute_type": self._config.compute_type,
                    "vad_filter": self._config.vad_filter,
                },
            )
        except FasterWhisperRuntimeError:
            raise
        except Exception as error:
            raise FasterWhisperRuntimeError(
                "Local faster-whisper runtime failed safely."
            ) from error
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)


def build_faster_whisper_availability_config(
    *,
    model_path: Path | None,
    manifest: FasterWhisperManifest = DEFAULT_FASTER_WHISPER_MANIFEST,
) -> ModelAvailabilityConfig:
    _validate_manifest(manifest)
    return ModelAvailabilityConfig(
        model_name=manifest.model_name,
        provider=ModelProvider.LOCAL_FILE,
        model_path=model_path,
    )


def build_faster_whisper_download_spec(
    manifest: FasterWhisperManifest = DEFAULT_FASTER_WHISPER_MANIFEST,
) -> ModelDownloadSpec:
    _validate_manifest(manifest)
    return ModelDownloadSpec(
        model_id=f"faster-whisper/{manifest.model_name}-int8",
        filename=f"{manifest.key}.ct2",
        expected_bytes=manifest.expected_bytes,
        source_url=None,
        manual_install_instructions=(
            "Install a compatible faster-whisper CTranslate2 model manually into the "
            "WorkTrace model cache. WorkTrace will not auto-download it during recording."
        ),
    )


def _parse_segments(segments: object) -> tuple[dict[str, object], ...]:
    if not isinstance(segments, Iterable):
        raise FasterWhisperRuntimeError("Local faster-whisper returned invalid segments.")

    segment_iterable = cast(Iterable[object], segments)
    parsed: list[dict[str, object]] = []
    for index, segment in enumerate(segment_iterable):
        text = str(getattr(segment, "text", "")).strip()
        start = getattr(segment, "start", None)
        end = getattr(segment, "end", None)
        if text:
            parsed.append(
                {
                    "index": index,
                    "start": float(start) if isinstance(start, int | float) else None,
                    "end": float(end) if isinstance(end, int | float) else None,
                    "text": redact_text(text),
                }
            )
    return tuple(parsed)


def _language_probability(info: object) -> float:
    probability = getattr(info, "language_probability", 0.7)
    if isinstance(probability, bool) or not isinstance(probability, int | float):
        raise FasterWhisperRuntimeError("Invalid faster-whisper language probability.")
    try:
        return require_confidence(float(probability))
    except ValueError as error:
        raise FasterWhisperRuntimeError("Invalid faster-whisper language probability.") from error


def _audio_suffix(mime_type: str) -> str:
    normalized = mime_type.lower().strip()
    if normalized == "audio/wav" or normalized == "audio/x-wav":
        return ".wav"
    if normalized == "audio/mpeg":
        return ".mp3"
    if normalized == "audio/webm":
        return ".webm"
    return ".audio"


def _validate_runtime_config(config: FasterWhisperRuntimeConfig) -> None:
    require_non_empty(config.model_name, "model_name")
    if config.model_path is not None and not str(config.model_path).strip():
        raise ValueError("model_path must not be blank")
    require_non_empty(config.device, "device")
    require_non_empty(config.compute_type, "compute_type")
    if config.beam_size <= 0:
        raise ValueError("beam_size must be greater than zero")
    if config.max_audio_bytes <= 0:
        raise ValueError("max_audio_bytes must be greater than zero")


def _validate_manifest(manifest: FasterWhisperManifest) -> None:
    require_non_empty(manifest.key, "manifest.key")
    require_non_empty(manifest.model_name, "manifest.model_name")
    require_non_empty(manifest.device, "manifest.device")
    require_non_empty(manifest.compute_type, "manifest.compute_type")
    if manifest.auto_download_allowed:
        raise ValueError("faster-whisper manifest must not enable automatic downloads.")
    if manifest.expected_bytes <= 0:
        raise ValueError("faster-whisper expected bytes must be greater than zero.")
