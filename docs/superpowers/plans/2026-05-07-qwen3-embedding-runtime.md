# Qwen3 Embedding Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fakeable local Qwen3 embedding runtime adapter and metadata manifest for `Qwen/Qwen3-Embedding-0.6B` that supports grouping/retrieval helpers without loading heavy model runtimes during recording.

**Architecture:** Keep embedding generation behind a localhost-only HTTP adapter with injectable transport, then bridge it into the existing command embedding pipeline (`embed_command_inputs` and `cluster_similar_commands`) so evidence IDs stay enforced by existing deterministic contracts.

**Tech Stack:** Python 3.13 dataclasses, stdlib `urllib`, pytest, existing model cache/availability helpers, Markdown docs.

---

### Task 1: Red Tests for Qwen Embedding Runtime + Manifest

**Files:**
- Create: `services/local-agent/tests/test_qwen_embedding_runtime.py`
- Read: `services/local-agent/src/worktrace_agent/ai/embeddings.py`
- Read: `services/local-agent/src/worktrace_agent/ai/model_cache.py`
- Read: `services/local-agent/src/worktrace_agent/ai/model_availability.py`

- [ ] **Step 1: Add failing tests for localhost-only runtime and fake transport payload**
- [ ] **Step 2: Add failing tests for command clustering with evidence IDs preserved through the runtime adapter**
- [ ] **Step 3: Add failing tests for empty input safety, redacted payload enforcement, and no heavy imports**
- [ ] **Step 4: Add failing tests for model-unavailable fallback and Qwen cache manifest metadata**
- [ ] **Step 5: Run focused test file to confirm RED**

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_qwen_embedding_runtime.py -q`

Expected: FAIL because `worktrace_agent.ai.qwen_embedding_runtime` does not exist yet.

### Task 2: Implement Qwen Embedding Runtime + Manifest

**Files:**
- Create: `services/local-agent/src/worktrace_agent/ai/qwen_embedding_runtime.py`
- Modify: `services/local-agent/tests/test_qwen_embedding_runtime.py`

- [ ] **Step 1: Add runtime config + localhost URL validation + injectable JSON transport**
- [ ] **Step 2: Implement runtime call to local `/embed` endpoint with redacted input payload and safe failures**
- [ ] **Step 3: Add adapter implementing `CommandEmbeddingModel` for deterministic clustering/search helpers**
- [ ] **Step 4: Add Qwen embedding manifest metadata (model IDs, dimensions, conservative input cap, no auto download)**
- [ ] **Step 5: Add cache/availability config builders for missing-model safe fallback**
- [ ] **Step 6: Run focused tests to confirm GREEN**

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_qwen_embedding_runtime.py -q`

Expected: PASS.

### Task 3: Docs + Policy Sync

**Files:**
- Modify: `README.md`
- Modify: `docs/model-routing.md`
- Modify: `docs/models/embedding.md`
- Modify: `docs/models/qwen.md`
- Modify: `docs/models/local_model_runtime.md`
- Modify: `docs/AGENT_STATE.md`

- [ ] **Step 1: Document embedding adapter-only status and hard limits**
- [ ] **Step 2: Document vector storage decision (SQLite vectors first; file index deferred)**
- [ ] **Step 3: Keep docs explicit about out-of-scope items (no remote embeddings/cloud DB/auto download)**

### Task 4: Verification + PR

**Files:**
- All changed #91 files

- [ ] **Step 1: Run focused model tests**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_qwen_embedding_runtime.py tests/test_model_cache.py tests/test_model_availability.py tests/test_portfolio_claim_discipline.py -q
```

- [ ] **Step 2: Run full required quality gate**

Run all required Python, shared, desktop, and Rust commands from the issue workflow.

- [ ] **Step 3: Self-review and publish**

Run:

```powershell
git diff --check
git diff --cached --check
git diff --stat
```

Then stage scoped #91 files, commit `feat: add qwen embedding runtime adapter`, push, open PR with `Closes #91`, and merge only after checks are green.
