import sys

from worktrace_agent.ai.embeddings import (
    CommandEmbeddingInput,
    cluster_similar_commands,
    embed_command_inputs,
)
from worktrace_agent.capture.audio_transcription import (
    AudioSegment,
    AudioTranscriptionPolicy,
    TranscriptionEngineResult,
    transcribe_audio_segment,
)
from worktrace_agent.privacy.redaction import (
    PRIVACY_TEST_CORPUS,
    REDACTION_TOKEN,
    count_privacy_leaks,
)

SESSION_ID = "sess_audio_embeddings_001"
TIMESTAMP = "2026-05-06T10:00:00+05:30"
HEAVY_MODEL_MODULES = (
    "torch",
    "transformers",
    "sentence_transformers",
    "faster_whisper",
    "llama_cpp",
)


def test_audio_transcription_policy_is_disabled_by_default_and_does_not_call_engine() -> None:
    engine = FakeTranscriptionEngine(
        TranscriptionEngineResult(text="should not run", confidence=0.9)
    )

    result = transcribe_audio_segment(
        audio_segment(),
        policy=AudioTranscriptionPolicy(),
        engine=engine,
    )

    assert result.status == "disabled"
    assert result.transcript is None
    assert result.user_message == "Audio transcription is disabled."
    assert engine.call_count == 0


def test_audio_transcription_private_mode_does_not_call_engine() -> None:
    engine = FakeTranscriptionEngine(
        TranscriptionEngineResult(text="should not run", confidence=0.9)
    )

    result = transcribe_audio_segment(
        audio_segment(),
        policy=AudioTranscriptionPolicy(enabled=True, private_mode=True),
        engine=engine,
    )

    assert result.status == "disabled"
    assert result.transcript is None
    assert result.user_message == "Audio transcription is disabled."
    assert engine.call_count == 0


def test_opt_in_audio_transcription_redacts_text_and_cites_source_event() -> None:
    engine = FakeTranscriptionEngine(
        TranscriptionEngineResult(
            text=f"Investigated failing tests with {PRIVACY_TEST_CORPUS[0]}",
            confidence=0.83,
            metadata={"note": f"contains {PRIVACY_TEST_CORPUS[1]}"},
        )
    )

    result = transcribe_audio_segment(
        audio_segment(source_event_id="evt_audio_source"),
        policy=AudioTranscriptionPolicy(enabled=True),
        engine=engine,
    )

    assert result.status == "transcribed"
    assert result.transcript is not None
    assert result.transcript.evidence_event_ids == ("evt_audio_source",)
    assert REDACTION_TOKEN in result.transcript.text
    assert count_privacy_leaks(result.transcript.text) == 0
    assert count_privacy_leaks(result.transcript.metadata) == 0
    assert engine.call_count == 1


def test_audio_transcription_failure_is_safe_and_redacted() -> None:
    result = transcribe_audio_segment(
        audio_segment(),
        policy=AudioTranscriptionPolicy(enabled=True),
        engine=RaisingTranscriptionEngine(RuntimeError(f"failed with {PRIVACY_TEST_CORPUS[0]}")),
    )

    assert result.status == "failed"
    assert result.transcript is None
    assert result.failure_category == "engine_failed"
    assert "failed with" not in result.user_message
    assert count_privacy_leaks(result.user_message) == 0


def test_embedding_worker_clusters_similar_commands_with_evidence_ids() -> None:
    model = FakeEmbeddingModel(
        {
            "uv run --python 3.13 pytest": (1.0, 0.0, 0.0),
            "uv run --python 3.13 pytest tests": (0.96, 0.04, 0.0),
            "pnpm --dir apps/desktop build": (0.0, 1.0, 0.0),
            "pnpm --dir apps/desktop test": (0.0, 0.95, 0.05),
        }
    )
    embedded = embed_command_inputs(
        [
            command_input("evt_pytest_1", "uv run --python 3.13 pytest"),
            command_input("evt_pytest_2", "uv run --python 3.13 pytest tests"),
            command_input("evt_pnpm_build", "pnpm --dir apps/desktop build"),
            command_input("evt_pnpm_test", "pnpm --dir apps/desktop test"),
        ],
        model=model,
    )

    clusters = cluster_similar_commands(embedded, similarity_threshold=0.92)

    assert [cluster.evidence_event_ids for cluster in clusters] == [
        ("evt_pytest_1", "evt_pytest_2"),
        ("evt_pnpm_build", "evt_pnpm_test"),
    ]
    assert clusters[0].representative_command == "uv run --python 3.13 pytest"
    assert clusters[0].average_similarity >= 0.92


def test_embedding_worker_redacts_commands_and_preserves_hash_metadata() -> None:
    model = FakeEmbeddingModel(
        {
            f"curl --api-key {PRIVACY_TEST_CORPUS[0]}": (1.0, 0.0),
        }
    )

    embedded = embed_command_inputs(
        [command_input("evt_secret_command", f"curl --api-key {PRIVACY_TEST_CORPUS[0]}")],
        model=model,
    )

    assert embedded[0].command == f"curl --api-key {REDACTION_TOKEN}"
    assert embedded[0].command_hash.startswith("sha256:")
    assert count_privacy_leaks(embedded[0].command) == 0


def test_audio_and_embedding_foundations_do_not_import_heavy_model_modules() -> None:
    for module_name in HEAVY_MODEL_MODULES:
        sys.modules.pop(module_name, None)

    engine = FakeTranscriptionEngine(TranscriptionEngineResult(text="safe", confidence=1))
    model = FakeEmbeddingModel({"pnpm test": (1.0, 0.0)})

    transcribe_audio_segment(
        audio_segment(),
        policy=AudioTranscriptionPolicy(),
        engine=engine,
    )
    embed_command_inputs([command_input("evt_no_heavy_import", "pnpm test")], model=model)

    assert not any(module_name in sys.modules for module_name in HEAVY_MODEL_MODULES)


def audio_segment(*, source_event_id: str | None = None) -> AudioSegment:
    return AudioSegment(
        id="audio_segment_001",
        session_id=SESSION_ID,
        source_event_id=source_event_id,
        started_at=TIMESTAMP,
        ended_at="2026-05-06T10:00:05+05:30",
        audio_bytes=b"fake-audio-bytes",
        mime_type="audio/wav",
    )


def command_input(event_id: str, command: str) -> CommandEmbeddingInput:
    return CommandEmbeddingInput(
        event_id=event_id,
        session_id=SESSION_ID,
        timestamp=TIMESTAMP,
        command=command,
        shell="powershell",
    )


class FakeTranscriptionEngine:
    engine_name = "fake-transcriber"

    def __init__(self, result: TranscriptionEngineResult) -> None:
        self.result = result
        self.call_count = 0

    def transcribe(self, segment: AudioSegment) -> TranscriptionEngineResult:
        self.call_count += 1
        return self.result


class RaisingTranscriptionEngine:
    engine_name = "failing-transcriber"

    def __init__(self, error: Exception) -> None:
        self.error = error

    def transcribe(self, segment: AudioSegment) -> TranscriptionEngineResult:
        raise self.error


class FakeEmbeddingModel:
    model_name = "fake-command-embedder"
    model_version = "test-v1"

    def __init__(self, embeddings: dict[str, tuple[float, ...]]) -> None:
        self.embeddings = embeddings

    def embed(self, text: str) -> tuple[float, ...]:
        return self.embeddings[text]
