from __future__ import annotations

import sys
from pathlib import Path

import pytest

from worktrace_agent.ai.gemma_manifest import (
    DEEP_GEMMA_REPORT_MODEL,
    DEFAULT_GEMMA_REPORT_MODEL,
    build_gemma_report_availability_config,
    build_gemma_report_runtime_config,
    select_gemma_report_model,
)
from worktrace_agent.ai.model_availability import (
    ModelFailureCategory,
    ModelProvider,
    ModelStatus,
    check_model_availability,
)

HEAVY_MODEL_MODULES = (
    "torch",
    "transformers",
    "llama_cpp",
    "ollama",
)


def test_default_gemma_report_model_uses_e2b_q4_budget() -> None:
    manifest = DEFAULT_GEMMA_REPORT_MODEL

    assert manifest.key == "gemma4-e2b-it-q4"
    assert manifest.display_name == "Gemma 4 E2B-it Q4"
    assert manifest.ollama_model == "gemma4:e2b"
    assert manifest.hugging_face_model_id == "google/gemma-4-E2B-it"
    assert manifest.quantization == "Q4_0"
    assert manifest.mode == "default"
    assert manifest.context_budget_tokens == 8192
    assert manifest.max_tested_context_budget_tokens == 16384
    assert manifest.max_input_chars == 32000
    assert manifest.max_output_tokens == 512
    assert manifest.temperature == 0.2
    assert manifest.auto_download_allowed is False
    assert manifest.download_spec is None
    assert "does not download" in manifest.safety_note


def test_deep_gemma_report_model_uses_e4b_q4_manual_budget() -> None:
    manifest = DEEP_GEMMA_REPORT_MODEL

    assert manifest.key == "gemma4-e4b-it-q4"
    assert manifest.display_name == "Gemma 4 E4B-it Q4"
    assert manifest.ollama_model == "gemma4:e4b"
    assert manifest.hugging_face_model_id == "google/gemma-4-E4B-it"
    assert manifest.quantization == "Q4_0"
    assert manifest.mode == "deep"
    assert manifest.context_budget_tokens == 16384
    assert manifest.max_tested_context_budget_tokens == 16384
    assert manifest.max_input_chars == 64000
    assert manifest.max_output_tokens == 512
    assert manifest.temperature == 0.2
    assert manifest.auto_download_allowed is False
    assert manifest.download_spec is None
    assert "manual" in manifest.safety_note.lower()


def test_default_gemma_runtime_config_uses_ollama_e2b_tag() -> None:
    config = build_gemma_report_runtime_config(base_url="http://127.0.0.1:11434")

    assert config.base_url == "http://127.0.0.1:11434"
    assert config.model_name == "gemma4:e2b"
    assert config.context_budget_tokens == 8192
    assert config.max_input_chars == 32000
    assert config.max_output_tokens == 512
    assert config.temperature == 0.2
    assert config.mode == "default"


def test_deep_gemma_runtime_config_uses_ollama_e4b_tag_and_16k_budget() -> None:
    config = build_gemma_report_runtime_config(
        base_url="http://127.0.0.1:11434",
        manifest=DEEP_GEMMA_REPORT_MODEL,
    )

    assert config.base_url == "http://127.0.0.1:11434"
    assert config.model_name == "gemma4:e4b"
    assert config.context_budget_tokens == 16384
    assert config.max_input_chars == 64000
    assert config.max_output_tokens == 512
    assert config.temperature == 0.2
    assert config.mode == "deep"


def test_default_gemma_runtime_config_rejects_full_128k_context() -> None:
    with pytest.raises(ValueError, match="context"):
        build_gemma_report_runtime_config(
            base_url="http://127.0.0.1:11434",
            context_budget_tokens=128000,
        )


def test_default_gemma_runtime_config_rejects_16k_until_non_default_mode_exists() -> None:
    with pytest.raises(ValueError, match="Default Gemma"):
        build_gemma_report_runtime_config(
            base_url="http://127.0.0.1:11434",
            context_budget_tokens=16384,
        )


def test_default_gemma_runtime_config_rejects_zero_context_budget() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        build_gemma_report_runtime_config(
            base_url="http://127.0.0.1:11434",
            context_budget_tokens=0,
        )


def test_deep_gemma_runtime_config_rejects_context_over_16k() -> None:
    with pytest.raises(ValueError, match="tested cap"):
        build_gemma_report_runtime_config(
            base_url="http://127.0.0.1:11434",
            manifest=DEEP_GEMMA_REPORT_MODEL,
            context_budget_tokens=32768,
        )


def test_select_gemma_deep_mode_requires_manual_selection() -> None:
    selection = select_gemma_report_model(
        requested_mode="deep",
        manual_deep_mode=False,
        recording_active=False,
        memory_pressure_high=False,
        e4b_available=True,
    )

    assert selection.selected_manifest is DEFAULT_GEMMA_REPORT_MODEL
    assert selection.can_run_deep is False
    assert selection.fallback_reason == "Deep mode requires manual selection."


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        (
            {"recording_active": True, "memory_pressure_high": False, "e4b_available": True},
            "Deep mode is disabled during recording.",
        ),
        (
            {"recording_active": False, "memory_pressure_high": True, "e4b_available": True},
            "Deep mode is disabled while memory pressure is high.",
        ),
        (
            {"recording_active": False, "memory_pressure_high": False, "e4b_available": False},
            "Gemma E4B is unavailable; falling back to Gemma E2B.",
        ),
    ],
)
def test_select_gemma_deep_mode_falls_back_to_e2b_when_guard_blocks(
    kwargs: dict[str, bool],
    reason: str,
) -> None:
    selection = select_gemma_report_model(
        requested_mode="deep",
        manual_deep_mode=True,
        **kwargs,
    )

    assert selection.selected_manifest is DEFAULT_GEMMA_REPORT_MODEL
    assert selection.can_run_deep is False
    assert selection.fallback_reason == reason


def test_select_gemma_deep_mode_uses_e4b_when_all_guards_pass() -> None:
    selection = select_gemma_report_model(
        requested_mode="deep",
        manual_deep_mode=True,
        recording_active=False,
        memory_pressure_high=False,
        e4b_available=True,
    )

    assert selection.selected_manifest is DEEP_GEMMA_REPORT_MODEL
    assert selection.can_run_deep is True
    assert selection.fallback_reason is None


def test_select_gemma_report_model_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="requested_mode"):
        select_gemma_report_model(requested_mode="experimental")


def test_gemma_availability_config_maps_missing_model_to_not_installed(
    tmp_path: Path,
) -> None:
    availability = check_model_availability(
        build_gemma_report_availability_config(model_path=tmp_path / "missing.gguf")
    )

    assert availability.model_name == "gemma4:e2b"
    assert availability.provider is ModelProvider.LOCAL_FILE
    assert availability.status is ModelStatus.NOT_INSTALLED
    assert availability.failure_category is ModelFailureCategory.NOT_INSTALLED
    assert availability.can_generate_report is False
    assert availability.can_record is True
    assert availability.can_build_timeline is True
    assert availability.can_export is True


def test_deep_gemma_availability_config_maps_missing_e4b_to_not_installed(
    tmp_path: Path,
) -> None:
    availability = check_model_availability(
        build_gemma_report_availability_config(
            model_path=tmp_path / "missing-e4b.gguf",
            manifest=DEEP_GEMMA_REPORT_MODEL,
        )
    )

    assert availability.model_name == "gemma4:e4b"
    assert availability.status is ModelStatus.NOT_INSTALLED
    assert availability.can_generate_report is False
    assert availability.can_record is True


def test_gemma_manifest_helpers_do_not_import_heavy_model_modules() -> None:
    for module_name in HEAVY_MODEL_MODULES:
        sys.modules.pop(module_name, None)

    build_gemma_report_runtime_config(base_url="http://localhost:11434")
    build_gemma_report_runtime_config(
        base_url="http://localhost:11434",
        manifest=DEEP_GEMMA_REPORT_MODEL,
    )
    select_gemma_report_model(
        requested_mode="deep",
        manual_deep_mode=True,
        recording_active=False,
        memory_pressure_high=False,
        e4b_available=True,
    )
    build_gemma_report_availability_config(model_path=None)

    assert not any(module_name in sys.modules for module_name in HEAVY_MODEL_MODULES)
