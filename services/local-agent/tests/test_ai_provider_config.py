from __future__ import annotations

import pytest

from worktrace_agent.ai.provider_config import (
    DEFAULT_GEMMA_DEV_FALLBACK_MODEL,
    DEFAULT_GEMMA_DEV_PRIMARY_MODEL,
    DEFAULT_LOCAL_OLLAMA_BASE_URL,
    AiReportProvider,
    read_ai_provider_config,
)


def test_default_provider_config_uses_development_gemini_gemma_reports() -> None:
    config = read_ai_provider_config({})

    assert config.provider is AiReportProvider.GEMINI_GEMMA_DEV
    assert config.dev_cloud_enabled is True
    assert config.local_ollama_base_url == DEFAULT_LOCAL_OLLAMA_BASE_URL
    assert config.gemini_api_key_present is False
    assert config.to_safe_metadata() == {
        "provider": "gemini_gemma_dev",
        "dev_cloud_enabled": True,
        "gemini_api_key_present": False,
        "local_ollama_base_url": DEFAULT_LOCAL_OLLAMA_BASE_URL,
        "primary_model": DEFAULT_GEMMA_DEV_PRIMARY_MODEL,
        "fallback_model": DEFAULT_GEMMA_DEV_FALLBACK_MODEL,
    }


def test_gemini_dev_provider_requires_explicit_cloud_enablement() -> None:
    config = read_ai_provider_config(
        {
            "WORKTRACE_AI_PROVIDER": "gemini_gemma_dev",
            "WORKTRACE_ENABLE_DEV_CLOUD_AI": "false",
            "GEMINI_API_KEY": "AIza-test-secret-value-that-must-not-print",
        }
    )

    assert config.provider is AiReportProvider.GEMINI_GEMMA_DEV
    assert config.dev_cloud_enabled is False
    assert config.can_use_gemini_dev_provider is False


def test_auxiliary_model_environment_does_not_change_report_provider() -> None:
    config = read_ai_provider_config(
        {
            "WORKTRACE_QWEN_EMBEDDING_BASE_URL": "http://127.0.0.1:8001",
            "WORKTRACE_QWEN_VL_BASE_URL": "http://127.0.0.1:8002",
            "WORKTRACE_FASTER_WHISPER_MODEL_PATH": "C:\\models\\whisper",
        }
    )

    assert config.provider is AiReportProvider.GEMINI_GEMMA_DEV
    assert config.local_ollama_base_url == DEFAULT_LOCAL_OLLAMA_BASE_URL


def test_gemini_dev_provider_reports_key_presence_without_exposing_key() -> None:
    config = read_ai_provider_config(
        {
            "WORKTRACE_AI_PROVIDER": "gemini_gemma_dev",
            "WORKTRACE_ENABLE_DEV_CLOUD_AI": "true",
            "GEMINI_API_KEY": "AIza-test-secret-value-that-must-not-print",
            "WORKTRACE_GEMMA_PRIMARY_MODEL": "gemma-4-31b-it",
            "WORKTRACE_GEMMA_FALLBACK_MODEL": "gemma-4-26b-a4b-it",
        }
    )

    assert config.can_use_gemini_dev_provider is True
    assert config.gemini_api_key_present is True
    safe_text = str(config.to_safe_metadata()) + repr(config)
    assert "AIza-test" not in safe_text
    assert "gemma-4-31b-it" in safe_text


def test_invalid_provider_fails_without_echoing_environment_values() -> None:
    with pytest.raises(ValueError) as error:
        read_ai_provider_config(
            {
                "WORKTRACE_AI_PROVIDER": "https://example.com/not-a-provider",
                "GEMINI_API_KEY": "AIza-test-secret-value-that-must-not-print",
            }
        )

    message = str(error.value)
    assert "Unsupported AI provider" in message
    assert "AIza-test" not in message
    assert "example.com" not in message


def test_invalid_boolean_fails_closed_without_echoing_secret() -> None:
    with pytest.raises(ValueError) as error:
        read_ai_provider_config(
            {
                "WORKTRACE_ENABLE_DEV_CLOUD_AI": "definitely",
                "GEMINI_API_KEY": "AIza-test-secret-value-that-must-not-print",
            }
        )

    message = str(error.value)
    assert "WORKTRACE_ENABLE_DEV_CLOUD_AI must be a boolean" in message
    assert "AIza-test" not in message


def test_local_ollama_base_url_must_stay_localhost() -> None:
    with pytest.raises(ValueError) as error:
        read_ai_provider_config(
            {
                "WORKTRACE_LOCAL_OLLAMA_BASE_URL": "http://192.168.1.10:11434",
            }
        )

    assert "local HTTP URL" in str(error.value)


def test_local_ollama_base_url_rejects_paths_and_credentials() -> None:
    with pytest.raises(ValueError):
        read_ai_provider_config(
            {
                "WORKTRACE_LOCAL_OLLAMA_BASE_URL": "http://user:pass@127.0.0.1:11434",
            }
        )
    with pytest.raises(ValueError) as error:
        read_ai_provider_config(
            {
                "WORKTRACE_LOCAL_OLLAMA_BASE_URL": "http://127.0.0.1:11434/api/tags",
            }
        )

    assert "must not include a path" in str(error.value)
