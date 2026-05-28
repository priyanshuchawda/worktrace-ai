# Export Review UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire desktop-accessible deterministic Markdown/raw JSON export review for issue #69 without implying a real AI report runtime exists.

**Architecture:** Python owns export generation and writes redacted artifacts under the session artifact root. Rust/Tauri exposes typed localhost-only sidecar bridge commands and safe unavailable fallbacks. React calls only the typed client and renders loading, unavailable, error, success, preview, evidence ID, and AI-report-unavailable states.

**Tech Stack:** FastAPI, Python 3.13, Rust/Tauri v2 command handlers, React, TypeScript, Vitest.

---

### Task 1: Backend API Export Preview

**Files:**
- Modify: `services/local-agent/tests/api/test_sessions.py`
- Modify: `services/local-agent/src/worktrace_agent/api/session_recorder_service.py`
- Modify: `services/local-agent/src/worktrace_agent/api/routes/sessions.py`

- [x] **Step 1: Write failing FastAPI tests**

Add tests that create a session, ingest a redacted terminal command, stop the session, then assert `POST /sessions/{id}/exports/markdown`, `POST /sessions/{id}/exports/raw-json`, and `GET /sessions/{id}/folder` return safe payloads with preview text and evidence IDs.

- [x] **Step 2: Run the focused test to verify it fails**

Run: `uv run --python 3.13 pytest tests/api/test_sessions.py::test_export_session_markdown_and_raw_json_from_api -q`

- [x] **Step 3: Implement the FastAPI service/route methods**

Use existing deterministic exporters, read back a bounded preview, expose evidence IDs from raw events, and map unknown sessions to `404`.

- [x] **Step 4: Run focused API tests**

Run: `uv run --python 3.13 pytest tests/api/test_sessions.py -q`

### Task 2: Tauri Export Bridge

**Files:**
- Modify: `apps/desktop/src-tauri/src/services/sidecar.rs`
- Modify: `apps/desktop/src-tauri/src/commands/sidecar.rs`
- Modify: `apps/desktop/src-tauri/src/lib.rs`

- [ ] **Step 1: Write failing Rust tests**

Add tests around service methods that call a fake localhost sidecar and verify Markdown export, raw JSON export, and session folder lookup return typed available results, redact secret-shaped text, reject empty session IDs, and fail safely when the bridge is unavailable.

- [ ] **Step 2: Run Rust focused tests to verify failure**

Run: `cargo test export --lib`

- [ ] **Step 3: Implement typed bridge methods**

Add `SessionExportResult`, `SessionExportPreview`, and `SessionFolderResult` response types plus service methods for `/sessions/{id}/exports/markdown`, `/sessions/{id}/exports/raw-json`, and `/sessions/{id}/folder`.

- [ ] **Step 4: Register Tauri commands**

Expose `export_session_markdown`, `export_session_raw_json`, and `get_session_folder` through command handlers and `generate_handler!`.

### Task 3: Desktop Review UX

**Files:**
- Modify: `apps/desktop/src/lib/tauri-client.ts`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/App.test.tsx`

- [ ] **Step 1: Write failing React tests**

Add tests that stopped/live sessions enable export buttons, clicking Markdown/raw JSON shows loading then success previews with evidence IDs, failure shows safe unavailable/error text, and the AI report panel states that no real local LLM runtime is installed.

- [ ] **Step 2: Run focused desktop tests to verify failure**

Run: `pnpm --dir apps/desktop test -- --run App.test.tsx`

- [ ] **Step 3: Implement typed client functions**

Add `exportSessionMarkdown`, `exportSessionRawJson`, and `getSessionFolder` wrappers with safe unavailable fallback results.

- [ ] **Step 4: Implement UI states**

Replace disabled export placeholders with accessible buttons, preview panels, evidence ID chips/text, safe folder status, and an honest AI report unavailable panel.

### Task 4: Documentation and Gate

**Files:**
- Modify: `README.md`
- Modify: `docs/AGENT_STATE.md`

- [ ] **Step 1: Update README claims**

State that desktop Markdown/raw JSON export review is wired through a configured sidecar, while AI report generation remains unavailable because there is no real local model runtime.

- [ ] **Step 2: Run focused tests**

Run Python API, Rust export, and React App focused tests.

- [ ] **Step 3: Run full gate**

Run the full quality gate from `docs/agent_continuous_execution.md`.

- [ ] **Step 4: Self-review and publish**

Review `git diff`, commit, push, open PR for #69, wait for checks, then merge and continue to the next issue.
