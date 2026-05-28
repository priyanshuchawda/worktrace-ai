# Session Browser Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a desktop session browser that lists real sidecar sessions, lets the user select one, opens its safe folder lookup, exports partial/interrupted evidence, and deletes sessions through a typed local-only path.

**Architecture:** Python owns session listing/deletion and artifact cleanup policy; Rust/Tauri exposes localhost-only typed commands with redaction and safe unavailable fallbacks; React switches from `latest`-only review to selected-session review while preserving fixture fallback when no sidecar session list is available.

**Tech Stack:** FastAPI/Python 3.13, SQLite/WAL, Rust/Tauri, React/TypeScript, pytest, cargo tests, Vitest.

---

### Task 1: Backend Session List and Delete

**Files:**
- Modify: `services/local-agent/tests/api/test_sessions.py`
- Modify: `services/local-agent/src/worktrace_agent/db/session_state_repository.py`
- Modify: `services/local-agent/src/worktrace_agent/api/session_recorder_service.py`
- Modify: `services/local-agent/src/worktrace_agent/api/routes/sessions.py`

- [ ] **Step 1: Write failing API tests**

Add tests for `GET /sessions` returning newest-first sessions with event/screenshot counts, `DELETE /sessions/{session_id}` removing DB rows plus default session artifacts, and unknown deletion returning a safe 404.

- [ ] **Step 2: Run focused tests to verify red**

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/api/test_sessions.py::test_list_sessions_returns_newest_first_with_counts tests/api/test_sessions.py::test_delete_session_removes_rows_and_default_artifacts tests/api/test_sessions.py::test_delete_unknown_session_returns_safe_error -q`

Expected: FAIL because list/delete endpoints do not exist.

- [ ] **Step 3: Implement minimal backend**

Add repository/service methods for session summaries and deletion. Delete screenshots through the existing safe screenshot deletion helper before deleting the session row. Remove the default generated session artifact root only when it is under the app-managed `sessions/{session_id}` directory; do not recursively delete arbitrary custom storage paths.

- [ ] **Step 4: Run focused tests to verify green**

Run the focused pytest command again.

### Task 2: Rust/Tauri Session Browser Bridge

**Files:**
- Modify: `apps/desktop/src-tauri/tests/sidecar_service.rs`
- Modify: `apps/desktop/src-tauri/src/services/sidecar.rs`
- Modify: `apps/desktop/src-tauri/src/commands/sidecar.rs`
- Modify: `apps/desktop/src-tauri/src/lib.rs`

- [ ] **Step 1: Write failing Rust tests**

Add tests for missing bridge fallbacks, localhost `GET /sessions`, localhost `DELETE /sessions/{id}`, redaction of session fields, and empty session id rejection.

- [ ] **Step 2: Run focused tests to verify red**

Run: `cd apps/desktop/src-tauri; cargo test session_browser --test sidecar_service`

Expected: FAIL because session-list and delete bridge types/commands do not exist.

- [ ] **Step 3: Implement minimal Rust bridge**

Add `SessionListResult`, `SessionSummary`, `SessionDeletionResult`, service methods, command functions, and command registration. Keep localhost-only parsing and use the existing redaction helper.

- [ ] **Step 4: Run focused tests to verify green**

Run the focused cargo command again.

### Task 3: Desktop Session Browser UI

**Files:**
- Modify: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/lib/tauri-client.ts`
- Modify: `apps/desktop/src/App.tsx`

- [ ] **Step 1: Write failing React tests**

Add tests for loading a live session list, selecting a session and loading its events/screenshot/export context by ID, opening the selected folder, deleting a session, empty list state, unavailable list state, and interrupted/partial session affordances.

- [ ] **Step 2: Run focused tests to verify red**

Run: `pnpm --dir apps/desktop test -- App.test.tsx`

Expected: FAIL because session-list/delete client wrappers and selected-session UI do not exist.

- [ ] **Step 3: Implement minimal React client/UI**

Add typed client wrappers, session-list state, selected session id state, selection controls, delete button/state, and wire existing event/screenshot/export/folder flows to the selected session id instead of only `latest`.

- [ ] **Step 4: Run focused tests to verify green**

Run the focused Vitest command again.

### Task 4: Docs, State, and Full Gate

**Files:**
- Modify: `README.md`
- Modify: `docs/AGENT_STATE.md`

- [ ] Update README to say session browser/delete exists and still note packaging/model/OCR limitations.
- [ ] Update `docs/AGENT_STATE.md` after red tests, implementation, focused tests, full gate, PR, and merge.
- [ ] Run the full required quality gate.
- [ ] Self-review, commit, push, open PR, wait for checks, merge, close #73, delete branch, create/start the next issue.
