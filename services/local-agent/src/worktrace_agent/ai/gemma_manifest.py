from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from worktrace_agent.ai.local_report_runtime import (
    DEEP_CONTEXT_BUDGET_TOKEN_LIMIT,
    DEFAULT_CONTEXT_BUDGET_TOKENS,
    DEFAULT_MAX_INPUT_CHARS,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_TEMPERATURE,
    LocalReportRuntimeConfig,
)
from worktrace_agent.ai.model_availability import ModelAvailabilityConfig, ModelProvider
from worktrace_agent.ai.model_cache import ModelDownloadSpec

DEEP_MAX_INPUT_CHARS = 64000


@dataclass(frozen=True)
class GemmaReportModelManifest:
    key: str
    display_name: str
    ollama_model: str
    hugging_face_model_id: str
    quantization: str
    mode: str
    context_budget_tokens: int
    max_tested_context_budget_tokens: int
    max_input_chars: int
    max_output_tokens: int
    temperature: float
    auto_download_allowed: bool
    download_spec: ModelDownloadSpec | None
    safety_note: str


@dataclass(frozen=True)
class GemmaReportModelSelection:
    requested_mode: str
    selected_manifest: GemmaReportModelManifest
    fallback_reason: str | None
    can_run_deep: bool


DEFAULT_GEMMA_REPORT_MODEL = GemmaReportModelManifest(
    key="gemma4-e2b-it-q4",
    display_name="Gemma 4 E2B-it Q4",
    ollama_model="gemma4:e2b",
    hugging_face_model_id="google/gemma-4-E2B-it",
    quantization="Q4_0",
    mode="default",
    context_budget_tokens=DEFAULT_CONTEXT_BUDGET_TOKENS,
    max_tested_context_budget_tokens=DEEP_CONTEXT_BUDGET_TOKEN_LIMIT,
    max_input_chars=DEFAULT_MAX_INPUT_CHARS,
    max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
    temperature=DEFAULT_TEMPERATURE,
    auto_download_allowed=False,
    download_spec=None,
    safety_note=(
        "Default Gemma report config does not download, start, or load models; "
        "it only names a user-managed local runtime model and conservative budgets."
    ),
)


DEEP_GEMMA_REPORT_MODEL = GemmaReportModelManifest(
    key="gemma4-e4b-it-q4",
    display_name="Gemma 4 E4B-it Q4",
    ollama_model="gemma4:e4b",
    hugging_face_model_id="google/gemma-4-E4B-it",
    quantization="Q4_0",
    mode="deep",
    context_budget_tokens=DEEP_CONTEXT_BUDGET_TOKEN_LIMIT,
    max_tested_context_budget_tokens=DEEP_CONTEXT_BUDGET_TOKEN_LIMIT,
    max_input_chars=DEEP_MAX_INPUT_CHARS,
    max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
    temperature=DEFAULT_TEMPERATURE,
    auto_download_allowed=False,
    download_spec=None,
    safety_note=(
        "Gemma E4B deep report config is manual-only metadata. It does not download, "
        "start, or load models and falls back to Gemma E2B when guardrails block deep mode."
    ),
)


def select_gemma_report_model(
    *,
    requested_mode: str = "default",
    manual_deep_mode: bool = False,
    recording_active: bool = False,
    memory_pressure_high: bool = False,
    e4b_available: bool = False,
) -> GemmaReportModelSelection:
    if requested_mode not in {"default", "deep"}:
        raise ValueError("requested_mode must be default or deep.")
    if requested_mode == "default":
        return GemmaReportModelSelection(
            requested_mode=requested_mode,
            selected_manifest=DEFAULT_GEMMA_REPORT_MODEL,
            fallback_reason=None,
            can_run_deep=False,
        )
    if not manual_deep_mode:
        return _deep_mode_fallback(
            requested_mode=requested_mode,
            reason="Deep mode requires manual selection.",
        )
    if recording_active:
        return _deep_mode_fallback(
            requested_mode=requested_mode,
            reason="Deep mode is disabled during recording.",
        )
    if memory_pressure_high:
        return _deep_mode_fallback(
            requested_mode=requested_mode,
            reason="Deep mode is disabled while memory pressure is high.",
        )
    if not e4b_available:
        return _deep_mode_fallback(
            requested_mode=requested_mode,
            reason="Gemma E4B is unavailable; falling back to Gemma E2B.",
        )
    return GemmaReportModelSelection(
        requested_mode=requested_mode,
        selected_manifest=DEEP_GEMMA_REPORT_MODEL,
        fallback_reason=None,
        can_run_deep=True,
    )


def _deep_mode_fallback(*, requested_mode: str, reason: str) -> GemmaReportModelSelection:
    return GemmaReportModelSelection(
        requested_mode=requested_mode,
        selected_manifest=DEFAULT_GEMMA_REPORT_MODEL,
        fallback_reason=reason,
        can_run_deep=False,
    )


def build_gemma_report_runtime_config(
    *,
    base_url: str,
    manifest: GemmaReportModelManifest = DEFAULT_GEMMA_REPORT_MODEL,
    context_budget_tokens: int | None = None,
) -> LocalReportRuntimeConfig:
    _validate_manifest(manifest)
    selected_context_budget = (
        manifest.context_budget_tokens if context_budget_tokens is None else context_budget_tokens
    )
    if selected_context_budget <= 0:
        raise ValueError("Gemma report context budget must be greater than zero.")
    if selected_context_budget > manifest.max_tested_context_budget_tokens:
        raise ValueError("Gemma report context budget must not exceed the tested cap.")
    if manifest.mode == "default" and selected_context_budget > DEFAULT_CONTEXT_BUDGET_TOKENS:
        raise ValueError("Default Gemma report context budget must not exceed 8192.")
    if manifest.mode == "deep" and selected_context_budget > DEEP_CONTEXT_BUDGET_TOKEN_LIMIT:
        raise ValueError("Deep Gemma report context budget must not exceed 16384.")

    return LocalReportRuntimeConfig(
        base_url=base_url,
        model_name=manifest.ollama_model,
        max_input_chars=manifest.max_input_chars,
        max_output_tokens=manifest.max_output_tokens,
        context_budget_tokens=selected_context_budget,
        temperature=manifest.temperature,
        mode=manifest.mode,
    )


def build_gemma_report_availability_config(
    *,
    model_path: Path | None,
    manifest: GemmaReportModelManifest = DEFAULT_GEMMA_REPORT_MODEL,
) -> ModelAvailabilityConfig:
    _validate_manifest(manifest)
    return ModelAvailabilityConfig(
        model_name=manifest.ollama_model,
        provider=ModelProvider.LOCAL_FILE,
        model_path=model_path,
    )


def _validate_manifest(manifest: GemmaReportModelManifest) -> None:
    if not manifest.key.strip():
        raise ValueError("Gemma manifest key must be non-empty.")
    if not manifest.ollama_model.strip():
        raise ValueError("Gemma Ollama model name must be non-empty.")
    if not manifest.hugging_face_model_id.startswith("google/gemma-4-"):
        raise ValueError("Gemma Hugging Face model id must name an official Gemma 4 model.")
    if manifest.mode not in {"default", "deep"}:
        raise ValueError("Gemma manifest mode must be default or deep.")
    if manifest.auto_download_allowed:
        raise ValueError("Gemma default report model must not enable automatic downloads.")
    if (
        manifest.mode == "default"
        and manifest.context_budget_tokens > DEFAULT_CONTEXT_BUDGET_TOKENS
    ):
        raise ValueError("Gemma default context budget must not exceed 8192.")
    if manifest.mode == "deep" and manifest.context_budget_tokens > DEEP_CONTEXT_BUDGET_TOKEN_LIMIT:
        raise ValueError("Gemma deep context budget must not exceed 16384.")
    if manifest.max_tested_context_budget_tokens > DEEP_CONTEXT_BUDGET_TOKEN_LIMIT:
        raise ValueError("Gemma tested context budget must not exceed 16384.")
    if manifest.max_output_tokens > DEFAULT_MAX_OUTPUT_TOKENS:
        raise ValueError("Gemma default max output tokens must not exceed 512.")
