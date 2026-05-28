from __future__ import annotations

import os
import urllib.parse
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from worktrace_agent.ai.local_http import require_local_http_url
from worktrace_agent.privacy.redaction import redact_text

WORKTRACE_AI_PROVIDER_ENV = "WORKTRACE_AI_PROVIDER"
WORKTRACE_ENABLE_DEV_CLOUD_AI_ENV = "WORKTRACE_ENABLE_DEV_CLOUD_AI"
WORKTRACE_LOCAL_OLLAMA_BASE_URL_ENV = "WORKTRACE_LOCAL_OLLAMA_BASE_URL"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
WORKTRACE_GEMMA_PRIMARY_MODEL_ENV = "WORKTRACE_GEMMA_PRIMARY_MODEL"
WORKTRACE_GEMMA_FALLBACK_MODEL_ENV = "WORKTRACE_GEMMA_FALLBACK_MODEL"

DEFAULT_LOCAL_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_GEMMA_DEV_PRIMARY_MODEL = "gemma-4-31b-it"
DEFAULT_GEMMA_DEV_FALLBACK_MODEL = "gemma-4-26b-a4b-it"


class AiReportProvider(StrEnum):
    LOCAL_OLLAMA = "local_ollama"
    GEMINI_GEMMA_DEV = "gemini_gemma_dev"


@dataclass(frozen=True)
class AiProviderConfig:
    provider: AiReportProvider
    dev_cloud_enabled: bool
    local_ollama_base_url: str = DEFAULT_LOCAL_OLLAMA_BASE_URL
    gemma_primary_model: str = DEFAULT_GEMMA_DEV_PRIMARY_MODEL
    gemma_fallback_model: str = DEFAULT_GEMMA_DEV_FALLBACK_MODEL
    _gemini_api_key: str | None = field(default=None, repr=False)

    @property
    def gemini_api_key_present(self) -> bool:
        return self._gemini_api_key is not None and bool(self._gemini_api_key.strip())

    @property
    def can_use_gemini_dev_provider(self) -> bool:
        return (
            self.provider is AiReportProvider.GEMINI_GEMMA_DEV
            and self.dev_cloud_enabled
            and self.gemini_api_key_present
        )

    def require_gemini_api_key(self) -> str:
        if not self.gemini_api_key_present or self._gemini_api_key is None:
            raise ValueError("GEMINI_API_KEY is required for gemini_gemma_dev.")
        return self._gemini_api_key

    def to_safe_metadata(self) -> dict[str, object]:
        return {
            "provider": self.provider.value,
            "dev_cloud_enabled": self.dev_cloud_enabled,
            "gemini_api_key_present": self.gemini_api_key_present,
            "local_ollama_base_url": redact_text(self.local_ollama_base_url),
            "primary_model": redact_text(self.gemma_primary_model),
            "fallback_model": redact_text(self.gemma_fallback_model),
        }


def read_ai_provider_config(env: Mapping[str, str] | None = None) -> AiProviderConfig:
    source = os.environ if env is None else env
    return AiProviderConfig(
        provider=_read_provider(source.get(WORKTRACE_AI_PROVIDER_ENV)),
        dev_cloud_enabled=_read_bool(
            source.get(WORKTRACE_ENABLE_DEV_CLOUD_AI_ENV),
            env_name=WORKTRACE_ENABLE_DEV_CLOUD_AI_ENV,
            default=True,
        ),
        local_ollama_base_url=_read_local_ollama_base_url(
            source.get(WORKTRACE_LOCAL_OLLAMA_BASE_URL_ENV)
        ),
        gemma_primary_model=_read_model_name(
            source.get(WORKTRACE_GEMMA_PRIMARY_MODEL_ENV),
            default=DEFAULT_GEMMA_DEV_PRIMARY_MODEL,
            env_name=WORKTRACE_GEMMA_PRIMARY_MODEL_ENV,
        ),
        gemma_fallback_model=_read_model_name(
            source.get(WORKTRACE_GEMMA_FALLBACK_MODEL_ENV),
            default=DEFAULT_GEMMA_DEV_FALLBACK_MODEL,
            env_name=WORKTRACE_GEMMA_FALLBACK_MODEL_ENV,
        ),
        _gemini_api_key=source.get(GEMINI_API_KEY_ENV),
    )


def _read_provider(value: str | None) -> AiReportProvider:
    selected = (value or AiReportProvider.GEMINI_GEMMA_DEV.value).strip()
    try:
        return AiReportProvider(selected)
    except ValueError as error:
        supported = ", ".join(provider.value for provider in AiReportProvider)
        raise ValueError(f"Unsupported AI provider. Supported values: {supported}.") from error


def _read_bool(value: str | None, *, env_name: str, default: bool = False) -> bool:
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{env_name} must be a boolean.")


def _read_local_ollama_base_url(value: str | None) -> str:
    selected = (value or DEFAULT_LOCAL_OLLAMA_BASE_URL).strip().rstrip("/")
    if not selected:
        raise ValueError(f"{WORKTRACE_LOCAL_OLLAMA_BASE_URL_ENV} must be a non-empty URL.")
    safe_url = require_local_http_url(selected)
    parsed = urllib.parse.urlparse(safe_url)
    if parsed.path not in {"", "/"}:
        raise ValueError(f"{WORKTRACE_LOCAL_OLLAMA_BASE_URL_ENV} must not include a path.")
    return safe_url.rstrip("/")


def _read_model_name(value: str | None, *, default: str, env_name: str) -> str:
    selected = (value or default).strip()
    if not selected:
        raise ValueError(f"{env_name} must be a non-empty model name.")
    return redact_text(selected)
