# WorkTrace AI Manual Testing Guide

This guide is for private-beta manual testing on Windows. It verifies the main
product journey without uploading private work data or exposing secrets.

## Safety Rules

- Do not commit `.env`, API keys, screenshots, OCR text, raw session evidence,
  model files, or validation logs.
- Use synthetic or low-sensitivity work for manual sessions.
- Hosted Gemini/Gemma is development-only and report-only. Raw screenshots and
  raw artifacts must stay local by default.
- Terminal ingestion is explicit/API-based only. WorkTrace must not be described
  as keylogging or global terminal spying.
- Current NSIS installer output is local/internal QA only, not public
  distribution.

## Prerequisites

- Windows development machine.
- PowerShell.
- `pnpm` for desktop tooling.
- `uv` for the Python sidecar.
- Rust/Tauri prerequisites for `pnpm tauri dev`.
- Optional: user-managed local Ollama runtime for local reports.
- Optional for development only: private `GEMINI_API_KEY` for
  `gemini_gemma_dev`.

## Start The App

Use two PowerShell windows.

Window 1, start the sidecar:

```powershell
cd C:\Users\Admin\Desktop\workaudit-ai\services\local-agent
uv run worktrace-local-agent
```

Verify health:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```

Expected:

- `status` is `ok`
- app name is `worktrace-local-agent`
- schema version is shown

Window 2, start the desktop:

```powershell
cd C:\Users\Admin\Desktop\workaudit-ai\apps\desktop
$env:WORKTRACE_SIDECAR_URL="http://127.0.0.1:8765"
pnpm tauri dev
```

Expected:

- Tauri launches the WorkTrace AI desktop app.
- Home shows a ready/idle session state, not a generic unavailable state when
  the sidecar is healthy.
- Local-agent and schema diagnostics are only visible under
  `Settings` -> `Advanced diagnostics`.

## First-Run Privacy Setup

1. Open `Home`.
2. Review first-run privacy setup.
3. Confirm the setup with `Accept safe defaults`.
4. Reset local app data for a second pass if needed, then open
   `Review capture presets` and verify these secondary choices remain
   available:
   - `Private / Safe`
   - `Coding session`
   - `Study / Work`
5. Verify `Start Session` is enabled only after consent.

Expected:

- The app explains local capture before recording starts.
- A new user can accept safe defaults without choosing a preset first.
- Private mode suppresses sensitive capture paths for new recordings.
- The UI does not claim unconditional no-cloud reporting when development cloud
  reports are configured.

## Recording Smoke

1. Click `Start Session`.
2. Optional: open `Advanced options` and add a note, title, project, tags, or
   a file-watch root for a safe test folder.
3. Switch between safe apps such as editor, terminal, browser docs, and File
   Explorer.
4. Click `Pause`.
5. Confirm the UI shows paused state.
6. Click `Resume`.
7. Confirm recording resumes.
8. Click `Finish Session`.

Expected:

- Raw session IDs stay hidden from the normal Home UI.
- Goal/title/project/tags/file-watch setup stays under `Advanced options`.
- Active state changes correctly for recording, paused, resumed, and stopped.
- The default Home flow shows a recap-first result after finish, not raw proof
  and export panels.
- No generic `Recorder unavailable` appears after successful sidecar responses.
- Sidecar logs show session-control requests succeeding.

## Activity And Evidence Review

1. Open `Home`.
2. Click `View Moments` or `Review Activity` from the finished-session recap.
3. Verify `Session moments` opens first.
4. Verify `Captured moments` shows a small local visual gallery.
5. Verify `Activity` uses human wording such as used apps and captured local
   activity.
6. Open `Technical details` only when testing raw proof/debug behavior.
7. Verify event count and visible event count.
8. Search by app, title, type, or proof reference.
9. Filter by source:
   - Active windows
   - Files
   - Terminal
10. Select evidence from the detailed Activity view.
11. Select a screenshot and preview it locally.

Expected:

- Normal review starts with moments and readable activity, not raw timeline,
  exports, hashes, paths, or provider diagnostics.
- Timeline remains available under `Technical details` and is readable on
  laptop width.
- Long evidence IDs are contained and do not overflow cards when technical
  proof is opened.
- Screenshot previews stay local.
- OCR snippets, when present, are redacted and local.
- Hosted development AI details are not shown in the normal session review.

## AI Report Review

Use one of the supported report modes.

Local product path:

- Run user-managed Ollama locally.
- Make sure the required model is available, such as `gemma4:e2b`.
- Keep endpoint on localhost.

Development shortcut:

- Configure `gemini_gemma_dev` only in private `.env` or shell environment.
- Set `GEMINI_API_KEY` privately.
- Use only safe test sessions.

Steps:

1. Stop the recording session.
2. Open `Home`.
3. Confirm the recap-first result is visible.
4. If local AI is ready, verify the summary starts automatically after finish.
5. Click `Create Summary` manually only if automatic generation did not run or
   you want to regenerate.
6. If AI is unavailable, verify Home shows `Smart recap is not set up` and
   prioritizes `View Moments`, `Review Activity`, and `Start New Session`.
7. Review summary sections when a summary exists.
8. Open `Technical details` before testing evidence-reference jumps.
9. Click proof references and verify they jump to supporting evidence.

Expected:

- Summary creation is unavailable while recording is active.
- Missing local runtime setup is explained in normal language.
- `GEMINI_API_KEY`, `gemini_gemma_dev`, model IDs, and development cloud
  generation controls do not appear in the normal Home/session-review flow.
- Provider/model provenance is visible only in advanced/technical views or
  developer settings.
- Every factual claim has evidence IDs.
- Suggestions are labelled as suggestions, not observed facts.
- Full prompts and API keys are not shown.

## Export And Sharing

Private local exports:

1. Open `Home`.
2. Click `View Moments` or `Review Activity`.
3. Open `Technical details`.
4. Click `Export Detailed Notes`.
5. Open `Advanced export` only if you need raw JSON.
6. Open the session folder.

Expected:

- Private exports are clearly labelled as local/evidence-rich.
- Export preview works without hiding that private details may be present.

Share-safe export:

1. Generate an AI summary.
2. Use `Share Update` from the recap-first result or click `View Moments`.
3. Open `Technical details` if the share-safe preview action is not already
   visible from the recap.
4. Click `Preview Shareable Summary`.
5. Review the preview.
6. Copy or download only after review.

Expected:

- Screenshots are omitted.
- OCR snippets are omitted.
- Raw events are omitted.
- Local paths and obvious secrets are redacted.
- Evidence references are IDs only.

## Settings, Privacy And Diagnostics

1. Open `Settings`.
2. Toggle private mode.
3. Open `Custom app lists` only when testing executable allow/block rules.
4. Edit allowed/blocked apps.
5. Save policy.
6. Verify `AI Summary` shows a simple readiness/setup message first.
7. Open `Advanced AI setup` only when testing localhost model endpoint and
   provider details.
8. Open `Advanced diagnostics` only when testing sidecar/schema status.
9. Preview diagnostics.

Expected:

- Policy save result is visible.
- Raw allowed/blocked app textareas stay hidden until `Custom app lists` is
  opened.
- Local model endpoint and provider cards stay hidden until `Advanced AI setup`
  is opened.
- Diagnostics JSON includes safe health/status/count metadata.
- Diagnostics excludes screenshots, OCR text, raw events, terminal commands,
  window titles, prompts, reports, paths, API keys, tokens, and `.env` values.

## Session Deletion

1. Open `History`.
2. Refresh sessions.
3. Verify each card uses a human-readable title, status, duration or activity
   count instead of a raw session ID as the primary label.
4. Open `More` on the test session.
5. Confirm the raw session ID is available only in technical details.
6. Delete the test session from the `More` menu.
7. Review deletion counts.
8. Confirm the session disappears from the list.

Expected:

- Session row is removed.
- Raw events are removed.
- Screenshot/OCR rows are removed.
- Default local artifact folder is removed when safe.
- UI shows honest counts for deleted/missing files.

## Installed-App Smoke

Run only when validating packaging or release-critical desktop/sidecar changes:

```powershell
pwsh -File scripts\validation\run-installed-beta-smoke.ps1 -Build
```

Expected:

- Sidecar package is built.
- Windows app/installer smoke completes locally.
- Evidence is written under ignored `artifacts/validation/<RUN_ID>/`.
- No unsigned installer is published publicly.

## Local Validation Commands

Run focused gates while developing:

```powershell
pwsh -File scripts\validation\run-local-gates.ps1 -Scope Desktop
pwsh -File scripts\validation\run-local-gates.ps1 -Scope Python
pwsh -File scripts\validation\run-local-gates.ps1 -Scope Shared
```

Run Rust checks when Tauri/Rust code changes:

```powershell
pwsh -File scripts\validation\run-local-gates.ps1 -Scope Rust
```

Run complete local gates before broad merges:

```powershell
pwsh -File scripts\validation\run-local-gates.ps1 -Scope All
```

The validation runner prints compact `PASS` / `FAIL` lines and stores full logs
under ignored `artifacts/validation/<RUN_ID>/`.

## Pass Criteria

Manual smoke passes when:

- App launches and sidecar is healthy.
- Recording starts, pauses, resumes, and finishes.
- Activity proof and captured moments are reviewable.
- Summaries are created or clearly unavailable with actionable setup.
- Shareable export redacts private material.
- Session deletion removes local evidence.
- Diagnostics do not include raw captured work or secrets.
- No console errors, obvious text overflow, or misleading cloud/privacy copy is
  visible during the main flow.

