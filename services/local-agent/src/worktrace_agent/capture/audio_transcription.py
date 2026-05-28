from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, cast

from worktrace_agent.privacy.redaction import redact_json_value, redact_text
from worktrace_agent.timeline.deterministic import (
    require_confidence,
    require_iso_datetime,
    require_non_empty,
)


class AudioTranscriptionStatus(StrEnum):
    DISABLED = "disabled"
    TRANSCRIBED = "transcribed"
    FAILED = "failed"


class AudioFailureCategory(StrEnum):
    DISABLED = "disabled"
    ENGINE_FAILED = "engine_failed"


@dataclass(frozen=True)
class AudioTranscriptionPolicy:
    enabled: bool = False
    store_raw_audio: bool = False
    private_mode: bool = False


@dataclass(frozen=True)
class AudioSegment:
    id: str
    session_id: str
    source_event_id: str | None
    started_at: str
    ended_at: str
    audio_bytes: bytes
    mime_type: str


@dataclass(frozen=True)
class TranscriptionEngineResult:
    text: str
    confidence: float
    metadata: dict[str, object] | None = None


class TranscriptionEngine(Protocol):
    @property
    def engine_name(self) -> str:
        """Safe display name for the transcription engine."""
        ...

    def transcribe(self, segment: AudioSegment) -> TranscriptionEngineResult:
        """Transcribe an opt-in audio segment."""
        ...


@dataclass(frozen=True)
class AudioTranscript:
    id: str
    session_id: str
    audio_segment_id: str
    started_at: str
    ended_at: str
    text: str
    confidence: float
    engine_name: str
    evidence_event_ids: tuple[str, ...]
    metadata: dict[str, object]


@dataclass(frozen=True)
class AudioTranscriptionResult:
    status: AudioTranscriptionStatus
    transcript: AudioTranscript | None
    user_message: str
    failure_category: AudioFailureCategory | None = None


def transcribe_audio_segment(
    segment: AudioSegment,
    *,
    policy: AudioTranscriptionPolicy,
    engine: TranscriptionEngine,
) -> AudioTranscriptionResult:
    _validate_audio_segment(segment)
    if not policy.enabled or policy.private_mode:
        return AudioTranscriptionResult(
            status=AudioTranscriptionStatus.DISABLED,
            transcript=None,
            user_message="Audio transcription is disabled.",
            failure_category=AudioFailureCategory.DISABLED,
        )

    try:
        engine_result = engine.transcribe(segment)
    except Exception:
        return AudioTranscriptionResult(
            status=AudioTranscriptionStatus.FAILED,
            transcript=None,
            user_message="Audio transcription failed safely.",
            failure_category=AudioFailureCategory.ENGINE_FAILED,
        )

    return AudioTranscriptionResult(
        status=AudioTranscriptionStatus.TRANSCRIBED,
        transcript=build_audio_transcript(
            segment=segment,
            engine_name=engine.engine_name,
            engine_result=engine_result,
        ),
        user_message="Audio transcription completed.",
    )


def build_audio_transcript(
    *,
    segment: AudioSegment,
    engine_name: str,
    engine_result: TranscriptionEngineResult,
) -> AudioTranscript:
    _validate_audio_segment(segment)
    evidence_event_ids = _evidence_event_ids(segment)
    metadata = cast(dict[str, object], redact_json_value(engine_result.metadata or {}))
    return AudioTranscript(
        id=f"{segment.id}-transcript",
        session_id=segment.session_id,
        audio_segment_id=segment.id,
        started_at=segment.started_at,
        ended_at=segment.ended_at,
        text=redact_text(require_non_empty(engine_result.text, "text")),
        confidence=require_confidence(engine_result.confidence),
        engine_name=redact_text(require_non_empty(engine_name, "engine_name")),
        evidence_event_ids=evidence_event_ids,
        metadata=metadata,
    )


def _validate_audio_segment(segment: AudioSegment) -> None:
    require_non_empty(segment.id, "audio_segment.id")
    require_non_empty(segment.session_id, "audio_segment.session_id")
    require_iso_datetime(segment.started_at, "audio_segment.started_at")
    require_iso_datetime(segment.ended_at, "audio_segment.ended_at")
    require_non_empty(segment.mime_type, "audio_segment.mime_type")
    if not segment.audio_bytes:
        raise ValueError("audio_segment.audio_bytes must not be empty")


def _evidence_event_ids(segment: AudioSegment) -> tuple[str, ...]:
    if segment.source_event_id is not None and segment.source_event_id.strip():
        return (segment.source_event_id,)
    return (segment.id,)
