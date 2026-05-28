# AI Report Eval Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing golden-session eval foundation with an AI report benchmark harness that verifies report evidence discipline, privacy, unavailable fallback, and deterministic proxy metrics without requiring real models.

**Architecture:** Reuse `golden_sessions.py` for fixture loading and deterministic timeline/report context. Add a focused `ai_report_benchmark.py` module that runs deterministic, fake E2B, fake E4B, and unavailable report modes through existing report contracts where possible. Keep all model calls fakeable and disabled for unavailable/recording states.

**Tech Stack:** Python 3.13, existing `worktrace_agent.ai.reporting` report contracts, golden sessions, pytest, Markdown docs.

---

### Task 1: Red Tests for AI Report Benchmark

**Files:**
- Create: `services/local-agent/tests/test_ai_report_eval_benchmark.py`

- [ ] **Step 1: Add failing tests for benchmark modes and reproducible table**

Test deterministic, e2b, e4b, and unavailable modes are present and `render_ai_report_benchmark_table(...)` is reproducible.

- [ ] **Step 2: Add failing tests for evidence and privacy metrics**

Test generated reports cite valid evidence IDs, invalid evidence IDs fail the eval, and privacy leak count stays zero.

- [ ] **Step 3: Add failing tests for unavailable/no-recording model behavior**

Test unavailable mode does not call a model and benchmark results record `model_unavailable_fallback`.

- [ ] **Step 4: Confirm RED**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_ai_report_eval_benchmark.py -q
```

Expected: fail on missing `worktrace_agent.evals.ai_report_benchmark`.

### Task 2: Implement AI Report Benchmark

**Files:**
- Create: `services/local-agent/src/worktrace_agent/evals/ai_report_benchmark.py`
- Modify: `services/local-agent/scripts/evaluate_model.py`

- [ ] **Step 1: Add result dataclasses and fake model helpers**

Create report eval result dataclasses, default mode list, and a prompt-derived fake report model for E2B/E4B proxy runs.

- [ ] **Step 2: Add per-session evaluation**

Build deterministic timeline for each golden session, generate deterministic baseline metrics, run fake report models through `generate_evidence_cited_report`, and catch invalid evidence as failed eval results.

- [ ] **Step 3: Add aggregate and table rendering**

Aggregate per mode and render a stable Markdown table with mode, hallucinated evidence, citation validity, privacy leaks, unavailable fallback, latency/RAM estimates, and pass/fail.

- [ ] **Step 4: Update script output**

Update `scripts/evaluate_model.py` to print the existing deterministic table plus the new AI report benchmark table.

### Task 3: Docs and State

**Files:**
- Modify: `README.md`
- Modify: `docs/evals.md`
- Modify: `docs/eval-results.md`
- Modify: `docs/AGENT_STATE.md`

- [ ] **Step 1: Document AI report eval scope**

State that the benchmark uses deterministic/fake-model proxy modes and does not prove real E2B/E4B model quality.

- [ ] **Step 2: Record current eval command/result**

Update `docs/eval-results.md` with the reproducible command and aggregate AI report rows.

### Task 4: Verification and PR

**Files:**
- All changed #101 files

- [ ] **Step 1: Run focused eval tests**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_ai_report_eval_benchmark.py tests/test_golden_sessions_eval.py tests/test_portfolio_claim_discipline.py -q
uv run --python 3.13 python scripts/evaluate_model.py
```

- [ ] **Step 2: Run full quality gate**

Run the required Python, shared, desktop, and Rust gates.

- [ ] **Step 3: Self-review and PR**

Run `git diff --check`, review staged diff, commit, push, open a PR with `Closes #101`, and merge only after checks are green.
