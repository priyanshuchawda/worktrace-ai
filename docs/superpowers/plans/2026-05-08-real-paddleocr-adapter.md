# Real PaddleOCR Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional real PaddleOCR adapter behind existing selective OCR guardrails, with safe unavailable fallback and per-session OCR job caps.

**Architecture:** Keep OCR candidate policy in `SelectiveOcrWorker`, keep runtime availability and lazy PaddleOCR loading in `ocr_runtime.py`, and ensure heavy OCR modules are never imported on normal recording/availability paths.

**Tech Stack:** Python 3.13 stdlib, pytest, existing OCR worker/runtime modules, SQLite OCR repository, Markdown docs.

---

### Task 1: Red Tests for Runtime Adapter + Guardrails

**Files:**
- Modify: `services/local-agent/tests/test_ocr_runtime.py`
- Modify: `services/local-agent/tests/test_selective_ocr_worker.py`

- [x] **Step 1: Add failing tests for PaddleOCR engine binding fallback when unavailable**
- [x] **Step 2: Add failing tests for fake-recognizer parsing through a real adapter class**
- [x] **Step 3: Add failing tests for per-session OCR job cap and runtime-failed safe skip**
- [x] **Step 4: Run focused OCR tests to confirm RED**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_ocr_runtime.py tests/test_selective_ocr_worker.py -q
```

### Task 2: Implement Real PaddleOCR Adapter

**Files:**
- Modify: `services/local-agent/src/worktrace_agent/capture/ocr_runtime.py`
- Modify: `services/local-agent/src/worktrace_agent/capture/ocr_worker.py`

- [x] **Step 1: Add lazy PaddleOCR recognizer factory + engine binding helper**
- [x] **Step 2: Add real adapter class that accepts screenshot bytes and parses PaddleOCR response safely**
- [x] **Step 3: Keep unavailable/failed runtime state safe and redacted**
- [x] **Step 4: Add worker guardrail for per-session OCR cap and runtime failure skip**
- [x] **Step 5: Run focused OCR tests to confirm GREEN**

### Task 3: Docs + State Updates

**Files:**
- Modify: `README.md`
- Modify: `docs/model-routing.md`
- Modify: `docs/models/ocr.md`
- Modify: `docs/models/local_model_runtime.md`
- Modify: `docs/AGENT_STATE.md`

- [x] **Step 1: Document optional real PaddleOCR adapter status and limitations**
- [x] **Step 2: Document OCR cap/no-continuous policy and unavailable fallback**
- [x] **Step 3: Keep docs explicit: no OCR during private mode/blocked apps/secret-risk**

### Task 4: Verification + PR

**Files:**
- All changed #93 files

- [x] **Step 1: Run focused model/OCR tests**
- [x] **Step 2: Run full required quality gate**
- [ ] **Step 3: Self-review, stage scoped files, commit, push, open PR with `Closes #93`, merge only after checks are green**
