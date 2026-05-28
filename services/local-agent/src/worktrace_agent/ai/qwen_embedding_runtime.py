from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from worktrace_agent.ai.embeddings import CommandEmbeddingModel
from worktrace_agent.ai.local_http import require_local_http_url
from worktrace_agent.ai.model_availability import ModelAvailabilityConfig, ModelProvider
from worktrace_agent.ai.model_cache import ModelDownloadSpec
from worktrace_agent.privacy.redaction import redact_text

QWEN_EMBEDDING_MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
QWEN_EMBEDDING_MODEL_KEY = "qwen3-embedding-0.6b"
QWEN_EMBEDDING_CONTEXT_LENGTH_TOKENS = 32_768
QWEN_EMBEDDING_MIN_OUTPUT_DIMENSION = 32
QWEN_EMBEDDING_MAX_OUTPUT_DIMENSION = 1_024
DEFAULT_QWEN_EMBEDDING_OUTPUT_DIMENSION = 1_024
DEFAULT_QWEN_EMBEDDING_MAX_INPUT_CHARS = 8_000
DEFAULT_QWEN_EMBEDDING_TIMEOUT_SECONDS = 20


class QwenEmbeddingRuntimeError(RuntimeError):
    """Safe user-readable local embedding runtime failure."""


class EmbeddingJsonTransport(Protocol):
    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: int,
    ) -> object:
        """POST JSON and return decoded JSON."""
        ...


@dataclass(frozen=True)
class QwenEmbeddingRuntimeConfig:
    base_url: str
    model_name: str = QWEN_EMBEDDING_MODEL_ID
    timeout_seconds: int = DEFAULT_QWEN_EMBEDDING_TIMEOUT_SECONDS
    max_input_chars: int = DEFAULT_QWEN_EMBEDDING_MAX_INPUT_CHARS
    output_dimension: int = DEFAULT_QWEN_EMBEDDING_OUTPUT_DIMENSION
    query_instruction: str | None = None


@dataclass(frozen=True)
class QwenEmbeddingManifest:
    key: str
    display_name: str
    hugging_face_model_id: str
    context_length_tokens: int
    min_output_dimension: int
    default_output_dimension: int
    max_output_dimension: int
    default_max_input_chars: int
    auto_download_allowed: bool
    download_spec: ModelDownloadSpec
    vector_storage_strategy: str
    safety_note: str


DEFAULT_QWEN_EMBEDDING_MANIFEST = QwenEmbeddingManifest(
    key=QWEN_EMBEDDING_MODEL_KEY,
    display_name="Qwen3-Embedding-0.6B",
    hugging_face_model_id=QWEN_EMBEDDING_MODEL_ID,
    context_length_tokens=QWEN_EMBEDDING_CONTEXT_LENGTH_TOKENS,
    min_output_dimension=QWEN_EMBEDDING_MIN_OUTPUT_DIMENSION,
    default_output_dimension=DEFAULT_QWEN_EMBEDDING_OUTPUT_DIMENSION,
    max_output_dimension=QWEN_EMBEDDING_MAX_OUTPUT_DIMENSION,
    default_max_input_chars=DEFAULT_QWEN_EMBEDDING_MAX_INPUT_CHARS,
    auto_download_allowed=False,
    download_spec=ModelDownloadSpec(
        model_id="embeddings/qwen3-embedding-0.6b",
        filename="model.safetensors",
        expected_bytes=1_191_586_416,
        sha256="0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd",
        source_url="https://huggingface.co/Qwen/Qwen3-Embedding-0.6B/resolve/main/model.safetensors",
        manual_install_instructions=(
            "Download model.safetensors manually from Hugging Face and install it through the "
            "local model cache flow."
        ),
    ),
    vector_storage_strategy=(
        "Store vectors in SQLite for smaller local indexes first; add a local file index only "
        "after benchmarked growth requires it."
    ),
    safety_note=(
        "Embedding runtime is adapter-only and local-first. It does not auto-download models, "
        "does not run during recording, and does not create claims without evidence IDs."
    ),
)


class UrllibEmbeddingTransport:
    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: int,
    ) -> object:
        safe_url = require_local_http_url(url)
        request = urllib.request.Request(
            safe_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
                return json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            raise QwenEmbeddingRuntimeError("Local embedding runtime failed safely.") from error


class QwenEmbeddingRuntime:
    def __init__(
        self,
        *,
        config: QwenEmbeddingRuntimeConfig,
        transport: EmbeddingJsonTransport | None = None,
    ) -> None:
        _validate_runtime_config(config)
        self._config = config
        self._transport = transport or UrllibEmbeddingTransport()
        self._base_url = _normalized_local_base_url(config.base_url)

    @property
    def model_name(self) -> str:
        return redact_text(self._config.model_name.strip())

    def embed_texts(self, texts: list[str]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()

        prepared_inputs = [
            _prepare_input_text(
                text=text,
                max_input_chars=self._config.max_input_chars,
                query_instruction=self._config.query_instruction,
            )
            for text in texts
        ]
        payload: dict[str, object] = {
            "model": self._config.model_name,
            "dimensions": self._config.output_dimension,
            "inputs": prepared_inputs,
        }
        try:
            response = self._transport.post_json(
                url=f"{self._base_url}/embed",
                payload=payload,
                timeout_seconds=self._config.timeout_seconds,
            )
        except QwenEmbeddingRuntimeError:
            raise
        except Exception as error:
            raise QwenEmbeddingRuntimeError("Local embedding runtime failed safely.") from error

        try:
            return _parse_embedding_response(
                response=response,
                expected_count=len(texts),
                expected_dimension=self._config.output_dimension,
            )
        except ValueError as error:
            raise QwenEmbeddingRuntimeError("Local embedding runtime failed safely.") from error


class QwenCommandEmbeddingModel(CommandEmbeddingModel):
    def __init__(
        self,
        *,
        runtime: QwenEmbeddingRuntime,
        model_version: str | None = None,
    ) -> None:
        self._runtime = runtime
        self._model_version = model_version

    @property
    def model_name(self) -> str:
        return self._runtime.model_name

    @property
    def model_version(self) -> str | None:
        if self._model_version is None:
            return None
        return redact_text(self._model_version)

    def embed(self, text: str) -> tuple[float, ...]:
        vectors = self._runtime.embed_texts([text])
        if len(vectors) != 1:
            raise QwenEmbeddingRuntimeError("Local embedding runtime failed safely.")
        return vectors[0]


def build_qwen_embedding_runtime_config(
    *,
    base_url: str,
    output_dimension: int | None = None,
    manifest: QwenEmbeddingManifest = DEFAULT_QWEN_EMBEDDING_MANIFEST,
) -> QwenEmbeddingRuntimeConfig:
    _validate_manifest(manifest)
    selected_dimension = output_dimension or manifest.default_output_dimension
    if selected_dimension < manifest.min_output_dimension:
        raise ValueError("Qwen embedding output dimension is below the supported minimum.")
    if selected_dimension > manifest.max_output_dimension:
        raise ValueError("Qwen embedding output dimension exceeds the supported maximum.")
    return QwenEmbeddingRuntimeConfig(
        base_url=base_url,
        model_name=manifest.hugging_face_model_id,
        max_input_chars=manifest.default_max_input_chars,
        output_dimension=selected_dimension,
    )


def build_qwen_embedding_cache_spec(
    manifest: QwenEmbeddingManifest = DEFAULT_QWEN_EMBEDDING_MANIFEST,
) -> ModelDownloadSpec:
    _validate_manifest(manifest)
    return manifest.download_spec


def build_qwen_embedding_availability_config(
    *,
    model_path: Path | None,
    manifest: QwenEmbeddingManifest = DEFAULT_QWEN_EMBEDDING_MANIFEST,
) -> ModelAvailabilityConfig:
    _validate_manifest(manifest)
    return ModelAvailabilityConfig(
        model_name=manifest.hugging_face_model_id,
        provider=ModelProvider.LOCAL_FILE,
        model_path=model_path,
    )


def _prepare_input_text(*, text: str, max_input_chars: int, query_instruction: str | None) -> str:
    if not text.strip():
        raise QwenEmbeddingRuntimeError("Local embedding input text is empty.")
    if len(text) > max_input_chars:
        raise QwenEmbeddingRuntimeError(
            "Local embedding input text is too large for configured budget."
        )
    redacted_text = redact_text(text, redact_contact_info=True)
    if query_instruction is None:
        return redacted_text
    instruction = query_instruction.strip()
    if not instruction:
        raise ValueError("query_instruction must be non-empty when provided")
    return f"Instruct: {instruction}\nQuery: {redacted_text}"


def _parse_embedding_response(
    *,
    response: object,
    expected_count: int,
    expected_dimension: int,
) -> tuple[tuple[float, ...], ...]:
    embeddings_data: object = response
    if isinstance(response, dict):
        response_dict = cast(dict[str, object], response)
        if "embeddings" in response_dict:
            embeddings_data = response_dict["embeddings"]
        else:
            response_data = response_dict.get("data")
            if isinstance(response_data, list):
                data_items = cast(list[object], response_data)
                embeddings_data = []
                for item in data_items:
                    if not isinstance(item, dict):
                        raise ValueError("embedding response data item must be an object")
                    embedding = cast(dict[str, object], item).get("embedding")
                    embeddings_data.append(embedding)

    if not isinstance(embeddings_data, list):
        raise ValueError("embedding response must contain a list")
    raw_embeddings = cast(list[object], embeddings_data)
    if len(raw_embeddings) != expected_count:
        raise ValueError("embedding response count mismatch")

    embeddings: list[tuple[float, ...]] = []
    for raw_vector in raw_embeddings:
        if not isinstance(raw_vector, list):
            raise ValueError("embedding vector must be a list")
        raw_values = cast(list[object], raw_vector)
        if len(raw_values) != expected_dimension:
            raise ValueError("embedding vector dimensions mismatch")
        vector = tuple(_to_finite_float(value) for value in raw_values)
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("embedding vector contains non-finite values")
        if not any(value != 0 for value in vector):
            raise ValueError("embedding vector must not be all zeros")
        embeddings.append(vector)

    return tuple(embeddings)


def _to_finite_float(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("embedding vector values must be numeric")
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError("embedding vector values must be numeric")


def _validate_runtime_config(config: QwenEmbeddingRuntimeConfig) -> None:
    if not config.model_name.strip():
        raise ValueError("model_name must be a non-empty string")
    if config.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if config.max_input_chars <= 0:
        raise ValueError("max_input_chars must be greater than zero")
    if config.output_dimension < QWEN_EMBEDDING_MIN_OUTPUT_DIMENSION:
        raise ValueError("output_dimension must be at least 32")
    if config.output_dimension > QWEN_EMBEDDING_MAX_OUTPUT_DIMENSION:
        raise ValueError("output_dimension must not exceed 1024")
    if config.query_instruction is not None and not config.query_instruction.strip():
        raise ValueError("query_instruction must be non-empty when provided")


def _validate_manifest(manifest: QwenEmbeddingManifest) -> None:
    if not manifest.key.strip():
        raise ValueError("Qwen embedding manifest key must be non-empty.")
    if manifest.hugging_face_model_id != QWEN_EMBEDDING_MODEL_ID:
        raise ValueError("Qwen embedding manifest must target Qwen/Qwen3-Embedding-0.6B.")
    if manifest.context_length_tokens != QWEN_EMBEDDING_CONTEXT_LENGTH_TOKENS:
        raise ValueError("Qwen embedding context length must remain 32k.")
    if manifest.min_output_dimension != QWEN_EMBEDDING_MIN_OUTPUT_DIMENSION:
        raise ValueError("Qwen embedding min output dimension must remain 32.")
    if manifest.default_output_dimension != DEFAULT_QWEN_EMBEDDING_OUTPUT_DIMENSION:
        raise ValueError("Qwen embedding default output dimension must remain 1024.")
    if manifest.max_output_dimension != QWEN_EMBEDDING_MAX_OUTPUT_DIMENSION:
        raise ValueError("Qwen embedding max output dimension must remain 1024.")
    if manifest.auto_download_allowed:
        raise ValueError("Qwen embedding manifest must not enable automatic downloads.")


def _normalized_local_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("local embedding runtime URL must use http or https")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("local embedding runtime URL must point to localhost")
    if parsed.username or parsed.password or parsed.path not in {"", "/"}:
        raise ValueError("local embedding runtime base URL must not include credentials or path")
    if parsed.query or parsed.fragment:
        raise ValueError("local embedding runtime URL must not include query or fragment")
    return base_url.rstrip("/")
