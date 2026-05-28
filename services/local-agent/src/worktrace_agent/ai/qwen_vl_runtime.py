from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from worktrace_agent.ai.local_http import require_local_http_url
from worktrace_agent.ai.model_availability import ModelAvailabilityConfig, ModelProvider
from worktrace_agent.ai.vision_analysis import VisionAnalysisRequest, VisionAnalyzerResult
from worktrace_agent.privacy.redaction import redact_json_value, redact_text
from worktrace_agent.timeline.deterministic import require_confidence

QWEN_VL_2B_MODEL_ID = "Qwen/Qwen3-VL-2B-Instruct"
QWEN_VL_4B_MODEL_ID = "Qwen/Qwen3-VL-4B-Instruct"
DEFAULT_QWEN_VL_TIMEOUT_SECONDS = 60
DEFAULT_QWEN_VL_MAX_IMAGE_BYTES = 2_000_000
DEFAULT_QWEN_VL_MAX_OUTPUT_TOKENS = 256
DEFAULT_QWEN_VL_TEMPERATURE = 0.1


class QwenVlRuntimeError(RuntimeError):
    """Safe user-readable selected-frame VLM runtime failure."""


class QwenVlJsonTransport(Protocol):
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
class QwenVlManifest:
    key: str
    display_name: str
    hugging_face_model_id: str
    laptop_safe_default: bool
    manual_only: bool
    auto_download_allowed: bool
    max_output_tokens: int
    temperature: float
    safety_note: str


@dataclass(frozen=True)
class QwenVlRuntimeConfig:
    base_url: str
    model_name: str = QWEN_VL_2B_MODEL_ID
    timeout_seconds: int = DEFAULT_QWEN_VL_TIMEOUT_SECONDS
    max_image_bytes: int = DEFAULT_QWEN_VL_MAX_IMAGE_BYTES
    max_output_tokens: int = DEFAULT_QWEN_VL_MAX_OUTPUT_TOKENS
    temperature: float = DEFAULT_QWEN_VL_TEMPERATURE


DEFAULT_QWEN_VL_MANIFEST = QwenVlManifest(
    key="qwen3-vl-2b-instruct",
    display_name="Qwen3-VL-2B-Instruct",
    hugging_face_model_id=QWEN_VL_2B_MODEL_ID,
    laptop_safe_default=True,
    manual_only=False,
    auto_download_allowed=False,
    max_output_tokens=DEFAULT_QWEN_VL_MAX_OUTPUT_TOKENS,
    temperature=DEFAULT_QWEN_VL_TEMPERATURE,
    safety_note=(
        "Qwen3-VL 2B is the preferred selected-frame vision target for laptop safety. "
        "It is metadata only and does not download, load, or start models."
    ),
)

QWEN_VL_4B_MANIFEST = QwenVlManifest(
    key="qwen3-vl-4b-instruct",
    display_name="Qwen3-VL-4B-Instruct",
    hugging_face_model_id=QWEN_VL_4B_MODEL_ID,
    laptop_safe_default=False,
    manual_only=True,
    auto_download_allowed=False,
    max_output_tokens=DEFAULT_QWEN_VL_MAX_OUTPUT_TOKENS,
    temperature=DEFAULT_QWEN_VL_TEMPERATURE,
    safety_note=(
        "Qwen3-VL 4B is manual-only until Windows laptop benchmarks prove it is safe. "
        "It is metadata only and does not download, load, or start models."
    ),
)


class UrllibQwenVlTransport:
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
            raise QwenVlRuntimeError("Local Qwen-VL runtime failed safely.") from error


class QwenVlSelectedFrameAnalyzer:
    def __init__(
        self,
        *,
        config: QwenVlRuntimeConfig,
        transport: QwenVlJsonTransport | None = None,
        analyzer_version: str | None = None,
    ) -> None:
        _validate_runtime_config(config)
        self._config = config
        self._base_url = _normalized_local_base_url(config.base_url)
        self._transport = transport or UrllibQwenVlTransport()
        self._analyzer_version = analyzer_version

    @property
    def analyzer_name(self) -> str:
        return redact_text(self._config.model_name.strip())

    @property
    def analyzer_version(self) -> str | None:
        if self._analyzer_version is None:
            return None
        return redact_text(self._analyzer_version)

    def analyze(self, request: VisionAnalysisRequest) -> VisionAnalyzerResult:
        if len(request.image_bytes) > self._config.max_image_bytes:
            raise QwenVlRuntimeError("Selected-frame image is too large for Qwen-VL analysis.")

        payload = _build_chat_payload(config=self._config, request=request)
        try:
            response = self._transport.post_json(
                url=f"{self._base_url}/v1/chat/completions",
                payload=payload,
                timeout_seconds=self._config.timeout_seconds,
            )
        except QwenVlRuntimeError:
            raise
        except Exception as error:
            raise QwenVlRuntimeError("Local Qwen-VL runtime failed safely.") from error

        try:
            return _parse_chat_response(response)
        except ValueError as error:
            raise QwenVlRuntimeError("Local Qwen-VL runtime failed safely.") from error


def build_qwen_vl_runtime_config(
    *,
    base_url: str,
    manifest: QwenVlManifest = DEFAULT_QWEN_VL_MANIFEST,
) -> QwenVlRuntimeConfig:
    _validate_manifest(manifest)
    return QwenVlRuntimeConfig(
        base_url=base_url,
        model_name=manifest.hugging_face_model_id,
        max_output_tokens=manifest.max_output_tokens,
        temperature=manifest.temperature,
    )


def build_qwen_vl_availability_config(
    *,
    model_path: Path | None,
    manifest: QwenVlManifest = DEFAULT_QWEN_VL_MANIFEST,
) -> ModelAvailabilityConfig:
    _validate_manifest(manifest)
    return ModelAvailabilityConfig(
        model_name=manifest.hugging_face_model_id,
        provider=ModelProvider.LOCAL_FILE,
        model_path=model_path,
    )


def _build_chat_payload(
    *,
    config: QwenVlRuntimeConfig,
    request: VisionAnalysisRequest,
) -> dict[str, object]:
    image_data_url = "data:image/png;base64," + base64.b64encode(request.image_bytes).decode(
        "ascii"
    )
    prompt = _selected_frame_prompt(request)
    return {
        "model": config.model_name,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
        "max_tokens": config.max_output_tokens,
        "temperature": config.temperature,
    }


def _selected_frame_prompt(request: VisionAnalysisRequest) -> str:
    screenshot = request.screenshot
    ocr_text = request.ocr_text or ""
    return redact_text(
        "\n".join(
            [
                "Analyze only this explicitly selected WorkTrace screenshot.",
                "Do not extract secrets or credentials; summarize secret-risk content generically.",
                "Return JSON with title, description, confidence, and optional metadata.",
                f"screenshot_id: {screenshot.id}",
                f"source_event_id: {screenshot.source_event_id or screenshot.id}",
                f"app_name: {request.app_name}",
                f"window_title: {request.window_title}",
                f"redacted_ocr_context: {ocr_text}",
            ]
        ),
        redact_contact_info=True,
    )


def _parse_chat_response(response: object) -> VisionAnalyzerResult:
    content = _extract_chat_content(response)
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError:
        return VisionAnalyzerResult(
            title="Qwen3-VL selected frame",
            description=redact_text(content.strip()),
            confidence=0.7,
        )

    if not isinstance(decoded, dict):
        raise ValueError("Qwen-VL JSON response must be an object")
    payload = cast(dict[str, object], decoded)
    title = payload.get("title")
    description = payload.get("description")
    confidence = payload.get("confidence", 0.7)
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Qwen-VL response title must be a non-empty string")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Qwen-VL response description must be a non-empty string")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("Qwen-VL response confidence must be numeric")

    metadata = payload.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("Qwen-VL response metadata must be an object")

    return VisionAnalyzerResult(
        title=redact_text(title.strip()),
        description=redact_text(description.strip()),
        confidence=require_confidence(float(confidence)),
        metadata=cast(dict[str, object], redact_json_value(metadata or {})),
    )


def _extract_chat_content(response: object) -> str:
    if not isinstance(response, dict):
        raise ValueError("Qwen-VL response must be an object")
    response_dict = cast(dict[str, object], response)
    choices = response_dict.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Qwen-VL response choices must be a non-empty list")
    first_choice = cast(list[object], choices)[0]
    if not isinstance(first_choice, dict):
        raise ValueError("Qwen-VL response choice must be an object")
    message = cast(dict[str, object], first_choice).get("message")
    if not isinstance(message, dict):
        raise ValueError("Qwen-VL response message must be an object")
    content = cast(dict[str, object], message).get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Qwen-VL response content must be non-empty")
    return content


def _validate_runtime_config(config: QwenVlRuntimeConfig) -> None:
    if not config.model_name.strip():
        raise ValueError("model_name must be a non-empty string")
    if config.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if config.max_image_bytes <= 0:
        raise ValueError("max_image_bytes must be greater than zero")
    if config.max_output_tokens <= 0:
        raise ValueError("max_output_tokens must be greater than zero")
    if not 0 <= config.temperature <= 1:
        raise ValueError("temperature must be between 0 and 1")


def _validate_manifest(manifest: QwenVlManifest) -> None:
    if manifest.hugging_face_model_id not in {QWEN_VL_2B_MODEL_ID, QWEN_VL_4B_MODEL_ID}:
        raise ValueError("Qwen-VL manifest must target a supported Qwen3-VL model.")
    if manifest.auto_download_allowed:
        raise ValueError("Qwen-VL manifest must not enable automatic downloads.")
    if manifest.max_output_tokens <= 0:
        raise ValueError("Qwen-VL max output tokens must be greater than zero.")
    if not 0 <= manifest.temperature <= 1:
        raise ValueError("Qwen-VL temperature must be between 0 and 1.")


def _normalized_local_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("local Qwen-VL runtime URL must use http or https")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("local Qwen-VL runtime URL must point to localhost")
    if parsed.username or parsed.password or parsed.path not in {"", "/"}:
        raise ValueError("local Qwen-VL runtime base URL must not include credentials or path")
    if parsed.query or parsed.fragment:
        raise ValueError("local Qwen-VL runtime URL must not include query or fragment")
    return base_url.rstrip("/")
