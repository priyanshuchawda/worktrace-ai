from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

import pytest

from worktrace_agent.ai.embeddings import (
    CommandEmbeddingInput,
    cluster_similar_commands,
    embed_command_inputs,
)
from worktrace_agent.ai.model_availability import (
    ModelFailureCategory,
    ModelProvider,
    ModelStatus,
    check_model_availability,
)
from worktrace_agent.ai.qwen_embedding_runtime import (
    DEFAULT_QWEN_EMBEDDING_MANIFEST,
    EmbeddingJsonTransport,
    QwenCommandEmbeddingModel,
    QwenEmbeddingRuntime,
    QwenEmbeddingRuntimeConfig,
    QwenEmbeddingRuntimeError,
    UrllibEmbeddingTransport,
    build_qwen_embedding_availability_config,
)
from worktrace_agent.privacy.redaction import (
    PRIVACY_TEST_CORPUS,
    REDACTION_TOKEN,
    count_privacy_leaks,
)

SESSION_ID = "sess_qwen_embedding_001"
TIMESTAMP = "2026-05-08T00:40:00+05:30"
HEAVY_MODEL_MODULES = (
    "torch",
    "transformers",
    "sentence_transformers",
    "llama_cpp",
    "ollama",
)


def test_qwen_embedding_runtime_rejects_non_localhost_endpoint() -> None:
    with pytest.raises(ValueError, match="localhost"):
        QwenEmbeddingRuntime(
            config=QwenEmbeddingRuntimeConfig(
                base_url="https://example.com",
                model_name="Qwen/Qwen3-Embedding-0.6B",
                output_dimension=32,
            ),
            transport=FakeEmbeddingTransport(vectors=[vec32(1.0)]),
        )


def test_urllib_embedding_transport_rejects_non_http_url_before_request() -> None:
    transport = UrllibEmbeddingTransport()

    with pytest.raises(ValueError, match="local HTTP"):
        transport.post_json(
            url="file:///tmp/qwen-embedding-response.json",
            payload={"inputs": ["redacted command"]},
            timeout_seconds=1,
        )


def test_qwen_embedding_runtime_rejects_oversized_input_before_transport() -> None:
    transport = FakeEmbeddingTransport(vectors=[vec32(1.0)])
    runtime = QwenEmbeddingRuntime(
        config=QwenEmbeddingRuntimeConfig(
            base_url="http://127.0.0.1:8080",
            model_name="Qwen/Qwen3-Embedding-0.6B",
            max_input_chars=4,
            output_dimension=32,
        ),
        transport=transport,
    )

    with pytest.raises(QwenEmbeddingRuntimeError, match="too large"):
        runtime.embed_texts(["this input is too long"])

    assert transport.requests == []


def test_qwen_embedding_runtime_empty_input_returns_empty_tuple() -> None:
    transport = FakeEmbeddingTransport(vectors=[])
    runtime = QwenEmbeddingRuntime(
        config=QwenEmbeddingRuntimeConfig(
            base_url="http://localhost:8080",
            model_name="Qwen/Qwen3-Embedding-0.6B",
            output_dimension=32,
        ),
        transport=transport,
    )

    assert runtime.embed_texts([]) == ()
    assert transport.requests == []


def test_qwen_embedding_runtime_posts_redacted_payload_to_local_embed_endpoint() -> None:
    transport = FakeEmbeddingTransport(vectors=[vec32(1.0), vec32(0.9, 0.1)])
    runtime = QwenEmbeddingRuntime(
        config=QwenEmbeddingRuntimeConfig(
            base_url="http://127.0.0.1:8080",
            model_name="Qwen/Qwen3-Embedding-0.6B",
            timeout_seconds=9,
            output_dimension=32,
        ),
        transport=transport,
    )

    vectors = runtime.embed_texts(
        [
            f"curl --header 'Authorization: Bearer {PRIVACY_TEST_CORPUS[0]}'",
            "uv run --python 3.13 pytest tests",
        ]
    )

    assert vectors == (tuple(vec32(1.0)), tuple(vec32(0.9, 0.1)))
    assert transport.requests == [
        {
            "url": "http://127.0.0.1:8080/embed",
            "payload": {
                "model": "Qwen/Qwen3-Embedding-0.6B",
                "dimensions": 32,
                "inputs": [
                    f"curl --header 'Authorization: Bearer {REDACTION_TOKEN}'",
                    "uv run --python 3.13 pytest tests",
                ],
            },
            "timeout_seconds": 9,
        }
    ]
    assert count_privacy_leaks(transport.requests[0]["payload"]) == 0


def test_qwen_embedding_runtime_transport_failure_is_safe() -> None:
    runtime = QwenEmbeddingRuntime(
        config=QwenEmbeddingRuntimeConfig(
            base_url="http://localhost:8080",
            model_name=f"Qwen/Qwen3-Embedding-0.6B {PRIVACY_TEST_CORPUS[0]}",
            output_dimension=32,
        ),
        transport=FailingEmbeddingTransport(RuntimeError(f"failed with {PRIVACY_TEST_CORPUS[1]}")),
    )

    with pytest.raises(QwenEmbeddingRuntimeError) as error:
        runtime.embed_texts(["uv run --python 3.13 pytest"])

    assert str(error.value) == "Local embedding runtime failed safely."
    assert count_privacy_leaks(str(error.value)) == 0


def test_qwen_embedding_runtime_clusters_similar_commands_with_evidence_ids() -> None:
    transport = MappingEmbeddingTransport(
        mapping={
            "uv run --python 3.13 pytest": tuple(vec32(1.0)),
            "uv run --python 3.13 pytest tests": tuple(vec32(0.96, 0.04)),
            "pnpm --dir apps/desktop build": tuple(vec32(0.0, 1.0)),
            "pnpm --dir apps/desktop test": tuple(vec32(0.0, 0.95, 0.05)),
        }
    )
    runtime = QwenEmbeddingRuntime(
        config=QwenEmbeddingRuntimeConfig(
            base_url="http://127.0.0.1:8080",
            model_name="Qwen/Qwen3-Embedding-0.6B",
            output_dimension=32,
        ),
        transport=transport,
    )
    model = QwenCommandEmbeddingModel(runtime=runtime, model_version="qwen-local-test")

    embedded = embed_command_inputs(
        [
            command_input("evt_pytest_1", "uv run --python 3.13 pytest"),
            command_input("evt_pytest_2", "uv run --python 3.13 pytest tests"),
            command_input("evt_build_1", "pnpm --dir apps/desktop build"),
            command_input("evt_test_1", "pnpm --dir apps/desktop test"),
        ],
        model=model,
    )
    clusters = cluster_similar_commands(embedded, similarity_threshold=0.92)

    assert [cluster.evidence_event_ids for cluster in clusters] == [
        ("evt_pytest_1", "evt_pytest_2"),
        ("evt_build_1", "evt_test_1"),
    ]
    assert all(cluster.model_name == "Qwen/Qwen3-Embedding-0.6B" for cluster in clusters)


def test_qwen_embedding_manifest_has_cache_spec_and_manual_install_policy() -> None:
    manifest = DEFAULT_QWEN_EMBEDDING_MANIFEST

    assert manifest.key == "qwen3-embedding-0.6b"
    assert manifest.display_name == "Qwen3-Embedding-0.6B"
    assert manifest.hugging_face_model_id == "Qwen/Qwen3-Embedding-0.6B"
    assert manifest.context_length_tokens == 32768
    assert manifest.default_output_dimension == 1024
    assert manifest.max_output_dimension == 1024
    assert manifest.auto_download_allowed is False
    assert manifest.download_spec.model_id == "embeddings/qwen3-embedding-0.6b"
    assert manifest.download_spec.filename == "model.safetensors"
    assert manifest.download_spec.expected_bytes == 1_191_586_416
    assert (
        manifest.download_spec.sha256
        == "0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd"
    )
    assert manifest.download_spec.source_url is not None
    assert "manual" in (manifest.download_spec.manual_install_instructions or "").lower()
    assert "SQLite" in manifest.vector_storage_strategy


def test_qwen_embedding_availability_maps_missing_model_to_not_installed(
    tmp_path: Path,
) -> None:
    availability = check_model_availability(
        build_qwen_embedding_availability_config(model_path=tmp_path / "missing-model.safetensors")
    )

    assert availability.model_name == "Qwen/Qwen3-Embedding-0.6B"
    assert availability.provider is ModelProvider.LOCAL_FILE
    assert availability.status is ModelStatus.NOT_INSTALLED
    assert availability.failure_category is ModelFailureCategory.NOT_INSTALLED
    assert availability.can_generate_report is False


def test_qwen_embedding_runtime_and_manifest_helpers_do_not_import_heavy_modules() -> None:
    for module_name in HEAVY_MODEL_MODULES:
        sys.modules.pop(module_name, None)

    runtime = QwenEmbeddingRuntime(
        config=QwenEmbeddingRuntimeConfig(
            base_url="http://localhost:8080",
            model_name="Qwen/Qwen3-Embedding-0.6B",
            output_dimension=32,
        ),
        transport=FakeEmbeddingTransport(vectors=[vec32(1.0)]),
    )
    runtime.embed_texts(["uv run --python 3.13 pytest"])
    build_qwen_embedding_availability_config(model_path=None)

    assert not any(module_name in sys.modules for module_name in HEAVY_MODEL_MODULES)


def command_input(event_id: str, command: str) -> CommandEmbeddingInput:
    return CommandEmbeddingInput(
        event_id=event_id,
        session_id=SESSION_ID,
        timestamp=TIMESTAMP,
        command=command,
        shell="powershell",
    )


def vec32(first: float, second: float = 0.0, third: float = 0.0) -> list[float]:
    return [first, second, third, *([0.0] * 29)]


class FakeEmbeddingTransport(EmbeddingJsonTransport):
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
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
        return {"embeddings": self.vectors}


class MappingEmbeddingTransport(EmbeddingJsonTransport):
    def __init__(self, mapping: dict[str, tuple[float, ...]]) -> None:
        self.mapping = mapping

    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: int,
    ) -> object:
        inputs = payload.get("inputs")
        if not isinstance(inputs, list):
            raise AssertionError("inputs must be list")
        input_items = cast(list[object], inputs)
        if not input_items or not all(isinstance(item, str) for item in input_items):
            raise AssertionError("inputs must be non-empty strings")
        input_values = cast(list[str], input_items)
        first = input_values[0]
        if first not in self.mapping:
            raise AssertionError(f"missing test embedding mapping for: {first}")
        return {"embeddings": [list(self.mapping[first])]}


class FailingEmbeddingTransport(EmbeddingJsonTransport):
    def __init__(self, error: Exception) -> None:
        self.error = error

    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: int,
    ) -> object:
        raise self.error
