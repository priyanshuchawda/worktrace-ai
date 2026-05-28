# Gemma E4B Deep Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manual-only Gemma 4 E4B-it Q4 deep report model config with safe fallback to the existing E2B default.

**Architecture:** Keep this issue metadata/config-only. Extend `gemma_manifest.py` with an E4B manifest and a pure selector that refuses deep mode during recording, when memory pressure is high, when E4B is unavailable, or when the user did not explicitly request deep mode. Reuse the existing localhost-only `LocalReportRuntimeConfig`; do not download, load, or start models.

**Tech Stack:** Python 3.13 dataclasses, existing local report runtime config, existing model availability helpers, pytest, Markdown docs.

---

### Task 1: Red Tests for E4B Manifest and Manual Selector

**Files:**
- Modify: `services/local-agent/tests/test_gemma_model_manifest.py`

- [x] **Step 1: Add failing tests for the E4B deep manifest**

Add tests that expect `DEEP_GEMMA_REPORT_MODEL` to use:
- key `gemma4-e4b-it-q4`
- display name `Gemma 4 E4B-it Q4`
- Ollama tag `gemma4:e4b`
- Hugging Face ID `google/gemma-4-E4B-it`
- quantization `Q4_0`
- mode `deep`
- context budget `16384`
- auto downloads disabled

- [x] **Step 2: Add failing tests for manual-only deep selection**

Add tests for:
- requested deep without `manual_deep_mode=True` falls back to E2B with a safe reason
- requested deep while recording falls back to E2B
- requested deep under high memory pressure falls back to E2B
- requested deep with E4B unavailable falls back to E2B
- requested deep with manual selection, not recording, memory OK, and E4B available selects E4B

- [x] **Step 3: Add failing tests for context cap and availability**

Add tests that:
- E4B runtime config uses deep mode and `num_ctx` budget 16384
- E4B runtime config rejects budgets over 16384
- missing E4B model maps to `not_installed`
- manifest helpers do not import heavy model modules

- [x] **Step 4: Run focused tests to confirm RED**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_gemma_model_manifest.py -q
```

Expected: fail on missing E4B manifest/selector symbols.

### Task 2: Implement Deep Mode Metadata and Selection

**Files:**
- Modify: `services/local-agent/src/worktrace_agent/ai/gemma_manifest.py`

- [x] **Step 1: Add `DEEP_GEMMA_REPORT_MODEL`**

Add a second `GemmaReportModelManifest` for Gemma 4 E4B-it Q4 with mode `deep`, 16384 context budget, conservative output/temperature defaults, and no download spec.

- [x] **Step 2: Add selection result dataclass**

Add `GemmaReportModelSelection` with:
- `requested_mode: str`
- `selected_manifest: GemmaReportModelManifest`
- `fallback_reason: str | None`
- `can_run_deep: bool`

- [x] **Step 3: Add manual-only selector**

Add `select_gemma_report_model(...)` parameters:
- `requested_mode: str = "default"`
- `manual_deep_mode: bool = False`
- `recording_active: bool = False`
- `memory_pressure_high: bool = False`
- `e4b_available: bool = False`

Rules:
- unknown mode raises `ValueError`
- default selects E2B
- deep without manual selection falls back to E2B
- deep while recording falls back to E2B
- deep under high memory pressure falls back to E2B
- deep when E4B unavailable falls back to E2B
- deep with all guards satisfied selects E4B

- [x] **Step 4: Relax manifest validation for deep mode only**

Keep default manifests capped at 8192. Allow deep manifests up to 16384. Keep max tested cap at 16384 for all Gemma manifests.

- [x] **Step 5: Run focused tests to confirm GREEN**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_gemma_model_manifest.py -q
```

### Task 3: Docs and Agent State

**Files:**
- Modify: `README.md`
- Modify: `docs/model-routing.md`
- Modify: `docs/models/gemma.md`
- Modify: `docs/models/local_model_runtime.md`
- Modify: `docs/AGENT_STATE.md`

- [x] **Step 1: Document E4B as manual deep mode only**

State that E4B is config metadata only, not bundled/downloaded/loaded, and never the default.

- [x] **Step 2: Document guardrails**

State that deep mode falls back to E2B when recording is active, memory pressure is high, E4B is unavailable, or the user did not manually select deep mode.

- [x] **Step 3: Keep context policy honest**

Document that E4B remains capped at 16K input budget until benchmark evidence proves more is safe, despite Gemma 4 E4B documenting 128K context.

### Task 4: Verification and PR

**Files:**
- All changed #95 files

- [x] **Step 1: Run focused model tests**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_gemma_model_manifest.py tests/test_local_report_runtime.py tests/test_model_availability.py tests/test_portfolio_claim_discipline.py -q
```

- [x] **Step 2: Run full quality gate**

Run the required Python, shared, desktop, and Rust gates from `docs/agent_continuous_execution.md`.

- [ ] **Step 3: Self-review and PR**

Run `git diff --check`, review the staged diff, commit, push, open a PR with `Closes #95`, and merge only after checks are green.
