# Real Gemma E2B Local Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the existing localhost-only AI report path can use a real user-managed Gemma E2B Ollama model when available, while keeping CI and normal tests fake/skipping.

**Architecture:** Add a small Python smoke script under `services/local-agent/scripts/` that checks Ollama CLI availability, verifies the configured default `gemma4:e2b` tag is installed, builds a tiny stopped-session evidence timeline, runs `generate_evidence_cited_report(...)` through the existing `OllamaReportModel`, validates evidence IDs and privacy, and exits successfully with a skipped JSON result when Ollama or the model is unavailable. Tests use fake subprocess/runtime dependencies only and never require a real model.

**Tech Stack:** Python 3.13, existing `worktrace_agent.ai.gemma_manifest`, existing `worktrace_agent.ai.local_report_runtime`, pytest, Markdown docs.

---

### Task 1: Red Tests for Gemma E2B Smoke

**Files:**
- Create: `services/local-agent/tests/test_gemma_e2b_smoke_script.py`

- [ ] **Step 1: Add test for missing Ollama skip**

Assert the smoke helper returns `status="skipped"` and does not call the report runtime when `ollama --version` is unavailable.

- [ ] **Step 2: Add test for missing model skip**

Assert installed Ollama without `gemma4:e2b` returns `status="skipped"` and includes the configured model tag in the reason.

- [ ] **Step 3: Add test for successful fake runtime proof**

Assert a fake runtime result reports `status="passed"`, `model_name="gemma4:e2b"`, evidence IDs present, privacy leaks zero, and no prompt text in the serialized result.

- [ ] **Step 4: Confirm RED**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_gemma_e2b_smoke_script.py -q
```

Expected: fail on missing `scripts/smoke_gemma_e2b_report.py`.

### Task 2: Implement Smoke Script

**Files:**
- Create: `services/local-agent/scripts/smoke_gemma_e2b_report.py`

- [ ] **Step 1: Add typed result model**

Use a dataclass or Pydantic-free typed dict for smoke result fields:
`status`, `model_name`, `ollama_version`, `evidence_ids`, `privacy_leak_count`, `generated_at`, `reason`, and `report_summary`.

- [ ] **Step 2: Add Ollama environment checks**

Use fixed `subprocess.run(["ollama", "--version"])` and `subprocess.run(["ollama", "list"])` commands with timeouts. Do not invoke a shell. Parse installed model names from `ollama list`.

- [ ] **Step 3: Add fakeable smoke execution helper**

Expose a pure helper that accepts command runner and report model factory dependencies so unit tests can simulate unavailable/installed/pass cases.

- [ ] **Step 4: Add real CLI entrypoint**

The script should print JSON, exit `0` for `passed` and `skipped`, and exit `1` only for an unsafe/failed smoke after Ollama and `gemma4:e2b` are available.

### Task 3: Real Smoke and Docs

**Files:**
- Modify: `README.md`
- Modify: `docs/eval-results.md`
- Modify: `docs/models/gemma.md`
- Modify: `docs/models/local_model_runtime.md`
- Modify: `docs/AGENT_STATE.md`

- [ ] **Step 1: Run real smoke only after confirming model is installed**

Run:

```powershell
ollama --version
ollama list
cd services/local-agent
uv run --python 3.13 python scripts/smoke_gemma_e2b_report.py
```

- [ ] **Step 2: Document result honestly**

If the real smoke passes, record exact Ollama version, installed model tag, and smoke status. If it fails or skips, document that instead and keep tests fake/skipping.

### Task 4: Verification and PR

**Files:**
- All changed #103 files

- [ ] **Step 1: Run focused checks**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_gemma_e2b_smoke_script.py tests/test_local_report_runtime.py tests/test_evidence_cited_report.py tests/test_gemma_model_manifest.py tests/test_portfolio_claim_discipline.py -q
```

- [ ] **Step 2: Run full quality gate**

Run the required Python, shared, desktop, and Rust gates. Include the user-confirmed `pyproject.toml` and `uv.lock` dependency changes only if the full gate still passes.

- [ ] **Step 3: Self-review and PR**

Run `git diff --check`, review staged diff, commit, push, open a PR with `Closes #103`, wait for checks, and merge only if green.
