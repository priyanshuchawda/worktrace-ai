# Gemma E2B Default Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe Gemma 4 E2B local report model manifest and default runtime config without downloading, loading, or starting any model.

**Architecture:** Keep model identity and budget policy in a small Python AI manifest module. The existing Ollama report runtime remains the transport adapter; the new manifest only builds a validated `LocalReportRuntimeConfig` and cache metadata for future explicit install/download work.

**Tech Stack:** Python 3.13 dataclasses, pytest, existing local report runtime and model cache modules, Markdown docs.

---

### Task 1: Gemma Manifest Tests

**Files:**
- Create: `services/local-agent/tests/test_gemma_model_manifest.py`
- Read: `services/local-agent/src/worktrace_agent/ai/local_report_runtime.py`
- Read: `services/local-agent/src/worktrace_agent/ai/model_cache.py`

- [ ] **Step 1: Write failing tests for default model identity and budgets**

```python
from worktrace_agent.ai.gemma_manifest import DEFAULT_GEMMA_REPORT_MODEL


def test_default_gemma_report_model_uses_e2b_q4_budget() -> None:
    manifest = DEFAULT_GEMMA_REPORT_MODEL

    assert manifest.key == "gemma4-e2b-it-q4"
    assert manifest.display_name == "Gemma 4 E2B-it Q4"
    assert manifest.ollama_model == "gemma4:e2b"
    assert manifest.hugging_face_model_id == "google/gemma-4-E2B-it"
    assert manifest.mode == "default"
    assert manifest.context_budget_tokens == 8192
    assert manifest.max_tested_context_budget_tokens == 16384
    assert manifest.max_output_tokens == 512
    assert manifest.temperature == 0.2
    assert manifest.auto_download_allowed is False
```

- [ ] **Step 2: Write failing tests for runtime config derivation and cap enforcement**

```python
import pytest

from worktrace_agent.ai.gemma_manifest import build_gemma_report_runtime_config


def test_default_gemma_runtime_config_uses_ollama_e2b_tag() -> None:
    config = build_gemma_report_runtime_config(base_url="http://127.0.0.1:11434")

    assert config.model_name == "gemma4:e2b"
    assert config.context_budget_tokens == 8192
    assert config.max_output_tokens == 512
    assert config.temperature == 0.2
    assert config.mode == "default"


def test_default_gemma_runtime_config_rejects_full_128k_context() -> None:
    with pytest.raises(ValueError, match="context"):
        build_gemma_report_runtime_config(
            base_url="http://127.0.0.1:11434",
            context_budget_tokens=128000,
        )
```

- [ ] **Step 3: Run tests to verify RED**

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_gemma_model_manifest.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'worktrace_agent.ai.gemma_manifest'`.

### Task 2: Manifest Implementation

**Files:**
- Create: `services/local-agent/src/worktrace_agent/ai/gemma_manifest.py`
- Modify: `services/local-agent/tests/test_gemma_model_manifest.py`

- [ ] **Step 1: Implement the manifest dataclass and default constant**

```python
from __future__ import annotations

from dataclasses import dataclass

from worktrace_agent.ai.local_report_runtime import (
    DEFAULT_CONTEXT_BUDGET_TOKENS,
    DEFAULT_MAX_INPUT_CHARS,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_TEMPERATURE,
    DEEP_CONTEXT_BUDGET_TOKEN_LIMIT,
    LocalReportRuntimeConfig,
)
from worktrace_agent.ai.model_cache import ModelDownloadSpec


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
```

- [ ] **Step 2: Add config builder with explicit caps**

```python
def build_gemma_report_runtime_config(
    *,
    base_url: str,
    manifest: GemmaReportModelManifest = DEFAULT_GEMMA_REPORT_MODEL,
    context_budget_tokens: int | None = None,
) -> LocalReportRuntimeConfig:
    selected_context_budget = context_budget_tokens or manifest.context_budget_tokens
    if selected_context_budget > manifest.max_tested_context_budget_tokens:
        raise ValueError("Gemma report context budget must not exceed the tested cap.")
    if manifest.mode == "default" and selected_context_budget > DEFAULT_CONTEXT_BUDGET_TOKENS:
        raise ValueError("Default Gemma report context budget must not exceed 8192.")

    return LocalReportRuntimeConfig(
        base_url=base_url,
        model_name=manifest.ollama_model,
        max_input_chars=manifest.max_input_chars,
        max_output_tokens=manifest.max_output_tokens,
        context_budget_tokens=selected_context_budget,
        temperature=manifest.temperature,
        mode=manifest.mode,
    )
```

- [ ] **Step 3: Run tests to verify GREEN**

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_gemma_model_manifest.py -q`

Expected: PASS.

### Task 3: Docs and Claim Discipline

**Files:**
- Modify: `README.md`
- Modify: `docs/model-routing.md`
- Modify: `docs/models/gemma.md`
- Modify: `docs/models/local_model_runtime.md`
- Modify: `docs/AGENT_STATE.md`

- [ ] **Step 1: Update docs to state exact model IDs and limitations**

Document:

```txt
Default report model config is Gemma 4 E2B-it Q4, exposed to Ollama-style runtimes as gemma4:e2b and mapped to Hugging Face as google/gemma-4-E2B-it.
The config does not download or start the model.
Default context budget remains 8192 tokens and first tested maximum remains 16384 tokens.
```

- [ ] **Step 2: Run claim-discipline tests**

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_portfolio_claim_discipline.py -q`

Expected: PASS.

### Task 4: Verification and PR

**Files:**
- All changed #87 files

- [ ] **Step 1: Run model-focused tests**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_gemma_model_manifest.py tests/test_local_report_runtime.py tests/test_model_cache.py tests/test_portfolio_claim_discipline.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the full quality gate**

Run the full required Python, shared, desktop, and Rust gate from the issue prompt.

- [ ] **Step 3: Self-review and publish**

Run:

```powershell
git diff --check
git diff --cached --check
git diff --stat
git diff -- services/local-agent/src/worktrace_agent/ai/gemma_manifest.py services/local-agent/tests/test_gemma_model_manifest.py
```

Then stage scoped #87 files, commit `feat: add Gemma E2B default config`, push, open PR with `Closes #87`, and merge only after checks are green.
