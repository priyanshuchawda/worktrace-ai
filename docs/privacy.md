# Privacy

WorkTrace AI is a local-first Windows desktop recorder. Privacy is part of the
core product contract, not a later polish task.

## Current Capture Boundaries

- Active-window metadata is captured locally by the Python sidecar.
- Screenshot sampling stores local PNG artifacts under the session folder.
- Optional watched folders emit metadata-only file events for configured roots.
- Terminal command ingestion is explicit API/manual ingestion only; WorkTrace
  does not keylog or globally spy on shells.
- OCR is selective/local-only and stores redacted snippets when available.
- Gemini/Gemma hosted inference is development-only, explicit-enable, and not
  the shipped default path.

## User Controls

- First-run onboarding must be accepted before recording.
- Private mode suppresses implemented capture workers.
- Persisted allow/block policy controls are applied to active-window,
  screenshot, and file-watcher workers for new recordings.
- Screenshot metadata, previews, OCR snippets, exports, and session deletion are
  exposed through the local desktop/sidecar flow.

## Deletion Contract

Deleting a session must remove:

- the session row
- raw event rows
- screenshot rows
- OCR rows linked to the session/screenshots
- screenshot artifact files
- default session artifact folders, including generated exports

The regression tests in `services/local-agent/tests/api/test_sessions.py` verify
that session deletion clears SQLite rows for `sessions`, `raw_events`,
`screenshots`, and `ocr_results`, and removes default session artifact folders.
Screenshot-only deletion also verifies linked OCR rows are cleared through the
SQLite foreign-key cascade.

## Still Not Public-Release Complete

- The focused private-beta security review is recorded in #163.
- Storage/retention UX needs more user-facing polish beyond the existing
  screenshot retention cleanup and local deletion controls.
- Public distribution still requires signing, release-channel/updater decisions,
  Microsoft Store-compatible distribution path, release-channel policy, and
  minimal CI gates.
