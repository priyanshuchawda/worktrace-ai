# Screenshot Metadata UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a desktop screenshot evidence review surface that lists screenshot metadata, shows a safe metadata preview, and deletes screenshots through the existing local sidecar endpoint.

**Architecture:** Keep screenshot bytes and OCR out of scope. The Python API remains the source of truth for screenshot metadata and deletion; Rust/Tauri exposes typed localhost-only commands; React renders loading, empty, unavailable, success, preview, and delete-result states.

**Tech Stack:** FastAPI/Python 3.13, Rust/Tauri command bridge, React/TypeScript, Vitest, pytest, cargo tests.

---

### Task 1: Backend Latest Alias Deletion

**Files:**
- Modify: `services/local-agent/tests/api/test_sessions.py`
- Modify: `services/local-agent/src/worktrace_agent/api/session_recorder_service.py`

- [ ] **Step 1: Write the failing test**

Add a pytest case that starts/stops a session with a screenshot, lists `/sessions/latest/screenshots`, deletes `/sessions/latest/screenshots`, and verifies the real session has no screenshot rows left.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/api/test_sessions.py::test_latest_session_screenshots_can_be_listed_and_deleted -q`

Expected: FAIL because deletion currently uses the literal `latest` artifact root/session id.

- [ ] **Step 3: Write minimal implementation**

Resolve `latest` in `SessionRecorderService.delete_session_screenshots` before calling `delete_screenshots_for_session`; return an empty deletion result for unknown latest instead of raising.

- [ ] **Step 4: Run test to verify it passes**

Run the focused pytest command again.

### Task 2: Rust Screenshot Bridge

**Files:**
- Modify: `apps/desktop/src-tauri/tests/sidecar_service.rs`
- Modify: `apps/desktop/src-tauri/src/services/sidecar.rs`
- Modify: `apps/desktop/src-tauri/src/commands/sidecar.rs`
- Modify: `apps/desktop/src-tauri/src/lib.rs`

- [ ] **Step 1: Write failing Rust tests**

Add tests for missing bridge safe fallbacks, localhost GET `/sessions/{id}/screenshots`, DELETE `/sessions/{id}/screenshots`, redaction of metadata/path text, and empty session id rejection.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/desktop/src-tauri; cargo test screenshots --test sidecar_service`

Expected: FAIL because screenshot result types, service methods, and commands do not exist.

- [ ] **Step 3: Implement minimal Rust bridge**

Add typed screenshot metadata and delete-result structs, service methods, unavailable fallbacks, command functions, and command registration. Keep endpoint parsing localhost-only and reuse existing redaction.

- [ ] **Step 4: Run tests to verify they pass**

Run the focused cargo command again.

### Task 3: Desktop Screenshot Review Panel

**Files:**
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/lib/tauri-client.ts`
- Modify: `apps/desktop/src/App.tsx`

- [ ] **Step 1: Write failing React tests**

Add Vitest coverage for live-session screenshot loading, safe metadata preview with evidence IDs, delete success with count/empty state, and unavailable bridge messaging.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm --dir apps/desktop test -- App.test.tsx`

Expected: FAIL because typed client wrappers and screenshot UI state do not exist.

- [ ] **Step 3: Implement minimal React client/UI**

Add typed Tauri client wrappers for listing/deleting screenshots and replace the disabled screenshot placeholder with a panel that fetches metadata for the review session id, shows preview details, and deletes through the bridge.

- [ ] **Step 4: Run tests to verify they pass**

Run the focused Vitest command again.

### Task 4: Docs and Gate

**Files:**
- Modify: `README.md`
- Modify: `docs/AGENT_STATE.md`

- [ ] Update README to honestly say screenshot metadata review/delete exists, but OCR/image-content review is not implemented.
- [ ] Update `docs/AGENT_STATE.md` after implementation and test phases.
- [ ] Run the full required quality gate.
- [ ] Self-review the diff, commit, push, open PR, wait for checks, merge, close issue, update state, then create/start the next issue in sequence.
