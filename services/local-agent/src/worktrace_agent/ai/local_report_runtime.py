from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol, cast

from worktrace_agent.ai.local_http import require_local_http_url
from worktrace_agent.privacy.redaction import redact_text

DEFAULT_CONTEXT_BUDGET_TOKENS = 8192
DEFAULT_MAX_INPUT_CHARS = 32000
DEFAULT_MAX_OUTPUT_TOKENS = 512
DEFAULT_TEMPERATURE = 0.2
DEEP_CONTEXT_BUDGET_TOKEN_LIMIT = 16384
LOCAL_REPORT_RUNTIME_MODES = {"default", "deep"}


class LocalReportRuntimeError(RuntimeError):
    """Safe user-readable local report runtime failure."""


class JsonPostTransport(Protocol):
    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: int,
    ) -> dict[str, object]:
        """POST JSON and return a decoded JSON object."""
        ...


@dataclass(frozen=True)
class LocalReportRuntimeConfig:
    base_url: str
    model_name: str
    timeout_seconds: int = 30
    max_input_chars: int = DEFAULT_MAX_INPUT_CHARS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    context_budget_tokens: int = DEFAULT_CONTEXT_BUDGET_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    mode: str = "default"


class UrllibJsonPostTransport:
    def post_json(
        self,
        *,
        url: str,
        payload: dict[str, object],
        timeout_seconds: int,
    ) -> dict[str, object]:
        safe_url = require_local_http_url(url)
        request = urllib.request.Request(
            safe_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
                decoded = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            raise LocalReportRuntimeError("Local report runtime failed safely.") from error

        if not isinstance(decoded, dict):
            raise LocalReportRuntimeError("Local report runtime failed safely.")
        return cast(dict[str, object], decoded)


class OllamaReportModel:
    def __init__(
        self,
        *,
        config: LocalReportRuntimeConfig,
        transport: JsonPostTransport | None = None,
    ) -> None:
        _validate_config(config)
        self._config = config
        self._transport = transport or UrllibJsonPostTransport()
        self._base_url = _normalized_local_base_url(config.base_url)

    @property
    def model_name(self) -> str:
        return redact_text(self._config.model_name.strip())

    def generate(self, prompt: str) -> str:
        if len(prompt) > self._config.max_input_chars:
            raise LocalReportRuntimeError("Local report prompt is too large for configured budget.")
        payload: dict[str, object] = {
            "model": self._config.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "num_ctx": self._config.context_budget_tokens,
                "num_predict": self._config.max_output_tokens,
                "temperature": self._config.temperature,
            },
        }
        try:
            response = self._transport.post_json(
                url=f"{self._base_url}/api/generate",
                payload=payload,
                timeout_seconds=self._config.timeout_seconds,
            )
        except Exception as error:
            raise LocalReportRuntimeError("Local report runtime failed safely.") from error

        generated = response.get("response")
        if not isinstance(generated, str) or not generated.strip():
            raise LocalReportRuntimeError("Local report runtime failed safely.")
        return generated


def _validate_config(config: LocalReportRuntimeConfig) -> None:
    if not config.model_name.strip():
        raise ValueError("model_name must be a non-empty string")
    if config.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if config.max_input_chars <= 0:
        raise ValueError("max_input_chars must be greater than zero")
    if config.max_output_tokens <= 0:
        raise ValueError("max_output_tokens must be greater than zero")
    if config.context_budget_tokens <= 0:
        raise ValueError("context_budget_tokens must be greater than zero")
    if not 0 <= config.temperature <= 1:
        raise ValueError("temperature must be between 0 and 1")
    if config.mode not in LOCAL_REPORT_RUNTIME_MODES:
        raise ValueError("mode must be default or deep")
    if config.mode == "default" and config.context_budget_tokens > DEFAULT_CONTEXT_BUDGET_TOKENS:
        raise ValueError("default mode context_budget_tokens must not exceed 8192")
    if config.mode == "deep" and config.context_budget_tokens > DEEP_CONTEXT_BUDGET_TOKEN_LIMIT:
        raise ValueError("deep mode context_budget_tokens must not exceed 16384")


def _normalized_local_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("local report runtime URL must use http or https")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("local report runtime URL must point to localhost")
    if parsed.username or parsed.password or parsed.path not in {"", "/"}:
        raise ValueError("local report runtime base URL must not include credentials or path")
    if parsed.query or parsed.fragment:
        raise ValueError("local report runtime URL must not include query or fragment")
    return base_url.rstrip("/")
