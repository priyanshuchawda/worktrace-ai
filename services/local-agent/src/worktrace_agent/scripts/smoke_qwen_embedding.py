from __future__ import annotations

import json
import os
import urllib.parse
from dataclasses import dataclass
from typing import Literal

from worktrace_agent.ai.qwen_embedding_runtime import (
    DEFAULT_QWEN_EMBEDDING_MANIFEST,
    DEFAULT_QWEN_EMBEDDING_OUTPUT_DIMENSION,
    EmbeddingJsonTransport,
    QwenEmbeddingRuntime,
    QwenEmbeddingRuntimeConfig,
    QwenEmbeddingRuntimeError,
)
from worktrace_agent.privacy.redaction import count_privacy_leaks, redact_text

SmokeStatus = Literal["passed", "skipped", "failed"]
SMOKE_GENERATED_AT = "2026-05-08T00:00:00+05:30"
DEFAULT_ENDPOINT_ENV = "WORKTRACE_QWEN_EMBEDDING_BASE_URL"
SMOKE_INPUTS = (
    "uv run --python 3.13 pytest tests/test_qwen_embedding_runtime.py",
    "pnpm --dir apps/desktop build",
)


@dataclass(frozen=True)
class QwenEmbeddingSmokeResult:
    status: SmokeStatus
    model_name: str
    endpoint: str
    generated_at: str
    embedding_count: int
    embedding_dimension: int
    privacy_leak_count: int
    reason: str | None

    def to_public_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "model_name": self.model_name,
            "endpoint": self.endpoint,
            "generated_at": self.generated_at,
            "embedding_count": self.embedding_count,
            "embedding_dimension": self.embedding_dimension,
            "privacy_leak_count": self.privacy_leak_count,
            "reason": self.reason,
        }


def run_qwen_embedding_smoke(
    *,
    base_url: str | None = None,
    output_dimension: int = DEFAULT_QWEN_EMBEDDING_OUTPUT_DIMENSION,
    transport: EmbeddingJsonTransport | None = None,
) -> QwenEmbeddingSmokeResult:
    selected_base_url = base_url if base_url is not None else os.environ.get(DEFAULT_ENDPOINT_ENV)
    model_name = DEFAULT_QWEN_EMBEDDING_MANIFEST.hugging_face_model_id
    if not selected_base_url:
        return _skipped(
            model_name=model_name,
            endpoint="not_configured",
            reason=f"{DEFAULT_ENDPOINT_ENV} is not configured.",
        )

    try:
        runtime = QwenEmbeddingRuntime(
            config=QwenEmbeddingRuntimeConfig(
                base_url=selected_base_url,
                model_name=model_name,
                output_dimension=output_dimension,
            ),
            transport=transport,
        )
        embeddings = runtime.embed_texts(list(SMOKE_INPUTS))
    except (QwenEmbeddingRuntimeError, ValueError) as error:
        return _failed(
            model_name=model_name,
            endpoint=_safe_endpoint(selected_base_url),
            reason=str(error),
        )

    dimension = len(embeddings[0]) if embeddings else 0
    return QwenEmbeddingSmokeResult(
        status="passed",
        model_name=model_name,
        endpoint=_safe_endpoint(selected_base_url),
        generated_at=SMOKE_GENERATED_AT,
        embedding_count=len(embeddings),
        embedding_dimension=dimension,
        privacy_leak_count=count_privacy_leaks(
            {
                "model_name": model_name,
                "endpoint": _safe_endpoint(selected_base_url),
                "embedding_count": len(embeddings),
                "embedding_dimension": dimension,
            }
        ),
        reason=None,
    )


def main() -> int:
    result = run_qwen_embedding_smoke()
    print(json.dumps(result.to_public_dict(), sort_keys=True, indent=2))
    return 1 if result.status == "failed" else 0


def _skipped(*, model_name: str, endpoint: str, reason: str) -> QwenEmbeddingSmokeResult:
    redacted_reason = redact_text(reason)
    return QwenEmbeddingSmokeResult(
        status="skipped",
        model_name=model_name,
        endpoint=endpoint,
        generated_at=SMOKE_GENERATED_AT,
        embedding_count=0,
        embedding_dimension=0,
        privacy_leak_count=count_privacy_leaks(redacted_reason),
        reason=redacted_reason,
    )


def _failed(*, model_name: str, endpoint: str, reason: str) -> QwenEmbeddingSmokeResult:
    redacted_reason = redact_text(reason)
    return QwenEmbeddingSmokeResult(
        status="failed",
        model_name=model_name,
        endpoint=endpoint,
        generated_at=SMOKE_GENERATED_AT,
        embedding_count=0,
        embedding_dimension=0,
        privacy_leak_count=count_privacy_leaks({"endpoint": endpoint, "reason": redacted_reason}),
        reason=redacted_reason,
    )


def _safe_endpoint(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    return parsed.hostname or "invalid"


if __name__ == "__main__":
    raise SystemExit(main())
