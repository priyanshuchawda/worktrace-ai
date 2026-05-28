# Private Beta Security Review

Date: 2026-05-26

Scope: private-beta readiness review for the local evidence recorder, desktop
bridge, sidecar API, local AI report path, development-only cloud switch,
stored artifacts, exports, logs, and deletion controls.

## Threat Model

Assets:

- local session database and WAL files
- screenshot PNG artifacts and OCR snippets
- redacted exports and generated reports
- API keys and local environment variables
- sidecar process boundary and localhost API
- Windows install directory and bundled sidecar executable

Trust boundaries:

- React desktop UI to Tauri IPC commands
- Tauri Rust bridge to local FastAPI sidecar over localhost
- FastAPI sidecar to SQLite and local artifact folders
- optional local model services on localhost
- development-only Gemini/Gemma provider when explicitly enabled
- user-controlled captured evidence flowing into reports and exports

Attacker-controlled inputs:

- window titles, app names, file paths, terminal command text, OCR text
- model endpoint configuration values
- privacy allow/block entries
- local sidecar HTTP request payloads
- model responses returned by local or development-only hosted providers
- local files under configured watched folders

Required invariants:

- no hidden cloud upload
- no keylogging or global terminal spying
- no API key in React, Tauri IPC, SQLite reports, logs, exports, issues, or PRs
- no arbitrary remote model endpoint from the desktop UI
- local sidecar binds to `127.0.0.1` or `localhost`
- screenshots/raw artifacts are not sent to hosted providers by default
- report claims cite known evidence IDs
- captured evidence is treated as untrusted input and model output as untrusted output
- session deletion removes local DB rows and default artifacts

## Reviewed Surfaces

| Surface | Evidence | Result |
| --- | --- | --- |
| Sidecar bind host | `services/local-agent/src/worktrace_agent/__main__.py`, `services/local-agent/tests/test_packaging_entrypoint.py` | Localhost-only host validation exists. |
| Tauri sidecar URL and command bridge | `apps/desktop/src-tauri/src/services/sidecar.rs`, `apps/desktop/src-tauri/tests/sidecar_service.rs` | Command responses are redacted; local sidecar boundary is tested. |
| Local model endpoint | `apps/desktop/src/components/dashboard-utils.ts`, `services/local-agent/src/worktrace_agent/ai/provider_config.py`, `services/local-agent/src/worktrace_agent/ai/local_http.py` | Localhost-only validation exists in UI and backend config. |
| Development Gemini/Gemma provider | `docs/adr/0001-local-first-and-development-cloud-ai.md`, `services/local-agent/src/worktrace_agent/ai/dev_cloud_report_policy.py`, `services/local-agent/tests/test_dev_cloud_report_policy.py` | Explicit env enablement, redacted minimal context, no screenshot/raw upload by default. |
| Evidence-cited reports | `services/local-agent/src/worktrace_agent/ai/reporting.py`, `services/local-agent/tests/test_evidence_cited_report.py` | Unknown evidence IDs are rejected. |
| Markdown/raw JSON exports | `services/local-agent/src/worktrace_agent/exporters/`, `services/local-agent/tests/test_markdown_export.py` | Exports are redacted and deterministic. |
| Screenshot/OCR evidence | `services/local-agent/src/worktrace_agent/api/session_recorder_service.py`, `services/local-agent/tests/api/test_sessions.py` | Preview snippets are redacted; deletion clears screenshot/OCR rows. |
| Logs and diagnostics | `services/local-agent/src/worktrace_agent/observability/`, `services/local-agent/tests/test_observability.py` | Logs and debug bundle fields are redacted. |
| Desktop report rendering | `apps/desktop/src/components/dashboard-panels.tsx` | React renders text nodes; no `dangerouslySetInnerHTML` use found. |
| Installed-app process smoke | `docs/evidence/private-beta-installed-smoke-2026-05-26.json` | Installed desktop launch and sidecar `/health` passed locally. |

## Findings

No new P0/P1 security defect was found in this focused private-beta review.

Existing release blockers remain:

- #132 minimal CI before external beta
- #179 future Microsoft Store MSIX/AppX distribution path
- #165 updater/release-channel policy
- #169 privacy-safe report export/sharing workflow
- #172 privacy-safe diagnostics bundle UX

## Security Notes For Private Beta

- The sidecar API is localhost-only but does not yet have per-user auth. That is
  acceptable for local private beta only while the app remains local desktop
  software, but public distribution should re-evaluate local API abuse risk.
- Development Gemini/Gemma must remain explicit-enable only. It is not a public
  privacy-first product mode.
- A trusted public Windows distribution path and minimal CI are required before
  broad external beta. The owner-selected public Windows path is now a future
  Microsoft Store-compatible MSIX/AppX channel, with current NSIS builds limited
  to local/internal QA.
- Manual private-beta QA should still verify the UI demo flow with safe data:
  onboarding, record, pause/resume/stop, review, export, delete, restart.

## Validation

```text
PASS | pwsh -File scripts/validation/run-local-gates.ps1 -Scope Python | 89.4s | log=artifacts\validation\20260526-203000\
PASS | pwsh -File scripts/validation/run-installed-beta-smoke.ps1 -Build | 983.9s | log=artifacts\validation\20260526-195712\installed-beta-smoke.log
```

Secret scan review found only existing test fixtures, redaction corpus examples,
and placeholder configuration strings. No real `.env`, API key, prompt body,
raw screenshot, or private session artifact was committed.
