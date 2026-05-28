from __future__ import annotations

import json

from worktrace_agent.ai.qwen_embedding_runtime import EmbeddingJsonTransport
from worktrace_agent.scripts.smoke_qwen_embedding import run_qwen_embedding_smoke


def test_qwen_embedding_smoke_skips_without_configured_endpoint() -> None:
    result = run_qwen_embedding_smoke(base_url=None)

    assert result.status == "skipped"
    assert result.model_name == "Qwen/Qwen3-Embedding-0.6B"
    assert result.endpoint == "not_configured"
    assert result.embedding_count == 0
    assert result.embedding_dimension == 0
    assert result.privacy_leak_count == 0
    assert "not configured" in (result.reason or "")


def test_qwen_embedding_smoke_passes_with_fake_local_runtime() -> None:
    transport = FakeEmbeddingTransport()

    result = run_qwen_embedding_smoke(
        base_url="http://127.0.0.1:8080",
        output_dimension=32,
        transport=transport,
    )
    serialized = json.dumps(result.to_public_dict(), sort_keys=True)

    assert result.status == "passed"
    assert result.model_name == "Qwen/Qwen3-Embedding-0.6B"
    assert result.endpoint == "127.0.0.1"
    assert result.embedding_count == 2
    assert result.embedding_dimension == 32
    assert result.privacy_leak_count == 0
    assert result.reason is None
    assert "Authorization" not in serialized
    assert "pytest" not in serialized
    assert transport.urls == ["http://127.0.0.1:8080/embed"]
    assert transport.payloads[0]["dimensions"] == 32


class FakeEmbeddingTransport(EmbeddingJsonTransport):
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.payloads: list[dict[str, object]] = []

    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: int,
    ) -> object:
        self.urls.append(url)
        self.payloads.append(payload)
        return {
            "embeddings": [
                [1.0, *([0.0] * 31)],
                [0.8, 0.2, *([0.0] * 30)],
            ]
        }
