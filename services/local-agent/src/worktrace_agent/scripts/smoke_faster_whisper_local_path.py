from __future__ import annotations

import importlib.util
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from worktrace_agent.capture.audio_transcription import (
    AudioSegment,
    AudioTranscriptionPolicy,
    AudioTranscriptionStatus,
    transcribe_audio_segment,
)
from worktrace_agent.capture.faster_whisper_runtime import (
    DEFAULT_FASTER_WHISPER_MANIFEST,
    FasterWhisperRuntimeConfig,
    FasterWhisperTranscriptionEngine,
    WhisperRecognizer,
)
from worktrace_agent.privacy.redaction import count_privacy_leaks, redact_text

SmokeStatus = Literal["passed", "skipped", "failed"]
SMOKE_GENERATED_AT = "2026-05-08T00:00:00+05:30"
MODEL_PATH_ENV = "WORKTRACE_FASTER_WHISPER_MODEL_PATH"
SAMPLE_AUDIO_PATH_ENV = "WORKTRACE_FASTER_WHISPER_SAMPLE_AUDIO_PATH"
SMOKE_SESSION_ID = "sess_faster_whisper_smoke"
SMOKE_AUDIO_ID = "audio_faster_whisper_smoke"
SMOKE_SOURCE_EVENT_ID = "evt_faster_whisper_smoke_audio"
DEFAULT_SAMPLE_AUDIO_BYTES = b"fake-wav-bytes"


@dataclass(frozen=True)
class FasterWhisperSmokeResult:
    status: SmokeStatus
    model_name: str
    model_path: str
    generated_at: str
    evidence_ids: tuple[str, ...]
    transcript_char_count: int
    language: str | None
    privacy_leak_count: int
    reason: str | None

    def to_public_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "model_name": self.model_name,
            "model_path": self.model_path,
            "generated_at": self.generated_at,
            "evidence_ids": list(self.evidence_ids),
            "transcript_char_count": self.transcript_char_count,
            "language": self.language,
            "privacy_leak_count": self.privacy_leak_count,
            "reason": self.reason,
        }


def run_faster_whisper_smoke(
    *,
    model_path: Path | None = None,
    sample_audio_path: Path | None = None,
    recognizer: WhisperRecognizer | None = None,
) -> FasterWhisperSmokeResult:
    selected_model_path = model_path or _env_path(MODEL_PATH_ENV)
    model_name = DEFAULT_FASTER_WHISPER_MANIFEST.model_name
    if selected_model_path is None:
        return _skipped(
            model_name=model_name,
            model_path="not_configured",
            reason=f"{MODEL_PATH_ENV} is not configured.",
        )
    if not selected_model_path.exists():
        return _skipped(
            model_name=model_name,
            model_path="missing",
            reason="Configured faster-whisper model path does not exist.",
        )
    if recognizer is None and importlib.util.find_spec("faster_whisper") is None:
        return _skipped(
            model_name=model_name,
            model_path="configured",
            reason="Optional faster-whisper package is not installed.",
        )

    selected_audio_path = sample_audio_path or _env_path(SAMPLE_AUDIO_PATH_ENV)
    if selected_audio_path is None and recognizer is None:
        return _skipped(
            model_name=model_name,
            model_path="configured",
            reason=f"{SAMPLE_AUDIO_PATH_ENV} is not configured.",
        )
    audio_bytes = (
        selected_audio_path.read_bytes()
        if selected_audio_path is not None
        else DEFAULT_SAMPLE_AUDIO_BYTES
    )

    engine = FasterWhisperTranscriptionEngine(
        config=FasterWhisperRuntimeConfig(model_path=selected_model_path),
        recognizer=recognizer,
    )
    result = transcribe_audio_segment(
        _smoke_audio_segment(audio_bytes),
        policy=AudioTranscriptionPolicy(enabled=True),
        engine=engine,
    )
    if result.status is not AudioTranscriptionStatus.TRANSCRIBED or result.transcript is None:
        return _failed(
            model_name=model_name,
            model_path="configured",
            reason=result.user_message,
        )

    transcript = result.transcript
    language = _safe_language(transcript.metadata.get("language"))
    public_payload = {
        "model_name": model_name,
        "model_path": "configured",
        "evidence_ids": transcript.evidence_event_ids,
        "transcript_char_count": len(transcript.text),
        "language": language,
    }
    return FasterWhisperSmokeResult(
        status="passed",
        model_name=model_name,
        model_path="configured",
        generated_at=SMOKE_GENERATED_AT,
        evidence_ids=transcript.evidence_event_ids,
        transcript_char_count=len(transcript.text),
        language=language,
        privacy_leak_count=count_privacy_leaks(public_payload),
        reason=None,
    )


def main() -> int:
    result = run_faster_whisper_smoke()
    print(json.dumps(result.to_public_dict(), sort_keys=True, indent=2))
    return 1 if result.status == "failed" else 0


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    return Path(value)


def _smoke_audio_segment(audio_bytes: bytes) -> AudioSegment:
    return AudioSegment(
        id=SMOKE_AUDIO_ID,
        session_id=SMOKE_SESSION_ID,
        source_event_id=SMOKE_SOURCE_EVENT_ID,
        started_at="2026-05-08T15:20:00+05:30",
        ended_at="2026-05-08T15:20:02+05:30",
        audio_bytes=audio_bytes,
        mime_type="audio/wav",
    )


def _skipped(*, model_name: str, model_path: str, reason: str) -> FasterWhisperSmokeResult:
    redacted_reason = redact_text(reason)
    return FasterWhisperSmokeResult(
        status="skipped",
        model_name=model_name,
        model_path=model_path,
        generated_at=SMOKE_GENERATED_AT,
        evidence_ids=(),
        transcript_char_count=0,
        language=None,
        privacy_leak_count=count_privacy_leaks(redacted_reason),
        reason=redacted_reason,
    )


def _failed(*, model_name: str, model_path: str, reason: str) -> FasterWhisperSmokeResult:
    redacted_reason = redact_text(reason)
    return FasterWhisperSmokeResult(
        status="failed",
        model_name=model_name,
        model_path=model_path,
        generated_at=SMOKE_GENERATED_AT,
        evidence_ids=(),
        transcript_char_count=0,
        language=None,
        privacy_leak_count=count_privacy_leaks(
            {"model_name": model_name, "model_path": model_path, "reason": redacted_reason}
        ),
        reason=redacted_reason,
    )


def _safe_language(value: object) -> str | None:
    if value is None:
        return None
    return redact_text(str(value))


if __name__ == "__main__":
    raise SystemExit(main())
