# WorkTrace AI

WorkTrace builds an evidence-backed timeline from local desktop events and generates summaries only from cited session evidence.

## Current Status

WorkTrace AI is a working local-first private-beta candidate for internal and
controlled testing. It is not a public Windows release yet.

The core private-beta loop is implemented:

- first-run privacy onboarding before recording
- local sidecar health and recorder controls
- start, pause, resume, stop, restart, and interrupted-session recovery paths
- Windows active-window capture
- local screenshot capture, metadata review, preview, OCR snippets, and deletion
- metadata-only file-watch roots
- explicit API/manual terminal ingestion only
- local timeline filtering, evidence search, and report evidence jumps
- session goals, tags, project labels, browser, folder-open, and deletion
- evidence-linked AI report UI with provider provenance
- share-safe Markdown export
- privacy-safe diagnostics bundle
- local validation scripts, deterministic tests, CI, and installed-app smoke tooling

The shipped-product direction remains local-first. Local Ollama-compatible
model runtimes are the intended report path for release builds. For fast local
development, the sidecar can use the `gemini_gemma_dev` provider when explicitly
configured with a private `GEMINI_API_KEY`; this is development-only,
report-only hosted inference. Screenshots, raw artifacts, unrestricted OCR text,
and raw events are not sent to hosted models by default. Qwen embeddings,
Qwen-VL, faster-whisper, and PaddleOCR remain optional local-only runtimes.

Public distribution is still deferred. The current NSIS installer output is for
local/internal QA only and must not be published as an unsigned public download.
Future public Windows distribution is intended to use a Microsoft Store
MSIX/AppX path after Store packaging and certification work is approved.

## Product Snapshot

WorkTrace AI helps developers, students, indie hackers, freelancers, and remote
knowledge workers answer: "What did I actually work on, what evidence supports
that, and what should I continue next?"

The product is built around one trusted journey:

1. Choose privacy settings.
2. Record a focused local work session.
3. Review local timeline and screenshot evidence.
4. Generate an evidence-cited report.
5. Export privately or share a redacted Markdown version.
6. Delete the session and local artifacts when done.

For startup positioning and pitch-deck content, see
[`docs/startup-product-brief.md`](docs/startup-product-brief.md).

## Quick Start: Development App

Use two PowerShell windows from the repository root.

Window 1, start the local Python sidecar:

```powershell
cd C:\Users\Admin\Desktop\workaudit-ai\services\local-agent
uv run worktrace-local-agent
```

Check health:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```

Window 2, start the Tauri desktop app:

```powershell
cd C:\Users\Admin\Desktop\workaudit-ai\apps\desktop
$env:WORKTRACE_SIDECAR_URL="http://127.0.0.1:8765"
pnpm tauri dev
```

For development hosted Gemma reports, keep the API key only in private `.env` or
shell environment. Do not commit `.env` or print secrets. See
[`docs/models/runtime-strategy.md`](docs/models/runtime-strategy.md).

## How To Test The App Manually

Follow the full checklist in
[`docs/manual-testing.md`](docs/manual-testing.md). The short smoke path is:

1. Confirm sidecar health is `ok`.
2. Launch desktop and confirm `Home` shows the app is ready.
3. Complete first-run privacy setup.
4. Start a session with an optional goal.
5. Pause, resume, then finish the session.
6. Open `View Moments` / `Review Activity` and verify normal review starts with
   captured moments and readable activity.
7. Open `Technical details` only for raw timeline filters, exports, evidence
   IDs, hashes, local previews, and provider diagnostics.
8. Create a Summary when a configured runtime is available.
9. Verify every factual summary claim has proof references.
10. Preview the shareable summary and confirm screenshots/raw evidence are omitted.
11. Open `History`, delete the test session from `More`, and verify deletion counts.
12. Open `Settings`, preview diagnostics, and confirm no raw evidence or secrets are included.

For local quality gates:

```powershell
pwsh -File scripts\validation\run-local-gates.ps1 -Scope Desktop
pwsh -File scripts\validation\run-local-gates.ps1 -Scope Python
pwsh -File scripts\validation\run-local-gates.ps1 -Scope Shared
```

Use the installed-app smoke only when validating packaging or release-critical
flows:

```powershell
pwsh -File scripts\validation\run-installed-beta-smoke.ps1 -Build
```

MVP 0 now includes shared contract schemas for events, sessions, reports, evidence IDs, privacy levels, confidence, and model run metadata.

MVP 0 now also includes a Python 3.13 SQLite migration foundation with WAL mode for local persistence.

MVP 0 now includes a fake-session validation, SQLite round-trip, and redacted raw JSON export proof.

MVP 1A now includes an initial Tauri v2 React desktop shell with status-only Home panels.

MVP 1A now includes a minimal Python 3.13 FastAPI app foundation with a tested `/health` endpoint for sidecar status.

MVP 1A now includes typed desktop sidecar health commands and UI states for loading, missing, and unhealthy sidecar conditions.

MVP 1A now includes a desktop session dashboard foundation with a sessions panel, session detail surface, source-filtered raw timeline, recorder start/pause/resume/stop controls for a configured local sidecar, screenshot evidence unavailable state, disabled export/retention actions for commands that are not wired yet, and a privacy status panel.

MVP 1B now includes a persisted Python session state machine for recording, paused, stopped, and interrupted statuses. This does not start capture workers yet.

MVP 1B now includes deterministic fake active-window raw events, SQLite raw-event read/write helpers, and a raw timeline UI preview. This is not live OS capture yet.

MVP 1B now includes real Windows active-window polling in the Python sidecar, with a provider abstraction, change-only raw-event persistence, session start/stop API wiring, and safe provider failure handling. This records app/process/window-title changes only; screenshots, file watcher, terminal capture, OCR, and model runtimes are handled by later guarded layers.

MVP 1B now includes Tauri commands that can start, pause, resume, stop, and load events from a configured localhost Python sidecar bridge and otherwise return safe unavailable states so the desktop can fall back to fixture preview data.

MVP 1B now includes a Tauri sidecar launch abstraction for a configured local sidecar binary and localhost port. It starts the process with local-only sidecar host/port environment, suppresses sidecar stdio, stops the managed process safely, and still returns safe missing/unhealthy states when no configured binary is available. Packaging-ready sidecar binary lookup exists, Tauri is configured for a `worktrace-local-agent` external binary, and the Python sidecar has a local-only executable entrypoint. A local Windows package smoke has produced a PyInstaller sidecar artifact and NSIS installer with the sidecar artifact present, and installer install/run QA passed locally on 2026-05-08 with the installed desktop executable starting and the installed sidecar returning `/health`. Python sidecar packaging is not bundled into the installer unless the target-triple sidecar artifact is produced before the Windows package build.

MVP 1C now includes real Windows screenshot capture with 5-second interval defaults, 1280px max-width compressed PNG artifact storage, duplicate skipping, SQLite screenshot metadata, nearby active-window evidence linking, bounded retention cleanup, and safe screenshot deletion under the session artifact root. JPEG/WebP screenshot encoding is not implemented yet.

MVP 1C now includes a metadata-only file watcher worker for configured folders. It polls filesystem snapshots, emits created/modified/deleted/renamed raw events, ignores noisy build/dependency folders, marks sensitive file paths, and does not store file contents.

MVP 1C now includes explicit safe terminal command ingestion through the local API. It accepts command, shell, exit code, timestamp, and session ID from a manual/logger path, redacts secrets before persistence, stores a redacted command hash, and exposes terminal events in the raw timeline stream. This is not terminal spying, keylogging, or global shell capture.

MVP 1D now includes foundational privacy policy decisions, prompt/export/log redaction helpers, stronger JWT/GitHub/Google/AWS/private-key/password-style redaction, optional generic email/phone redaction controls, private-mode suppression for active-window/screenshot/file-watcher workers, screenshot deletion that removes SQLite/OCR references and files under a session artifact root, sidecar-backed privacy policy persistence, a desktop privacy center baseline, and a focused private-beta security review.

MVP 1D now includes crash recovery helpers that mark active sessions as interrupted, keep partial raw events readable, and show an initial interrupted-session banner preview. This is not live crash monitoring yet.

MVP 1D now includes local rotating log and redacted debug bundle foundations for safe diagnostics. This does not add cloud telemetry.

MVP 1E now includes a deterministic Python timeline chunker that turns raw events into activity blocks, evidence-backed chunks, and basic repeated-command findings without an LLM.

MVP 1E now includes deterministic Markdown export with evidence references plus the existing redacted raw JSON export path.

MVP 1F now includes typed local model availability, fallback states, and a metadata-only model cache manager with deterministic local cache paths, disk-space checks, and checksum validation. Deterministic recording, timeline, and export paths can run without an AI model installed. This does not implement model downloads, local model loading, or LLM report generation yet.

MVP 1F now includes manual local-file model install/uninstall helpers. The install path checks disk space, copies a user-supplied local file into the model cache through a temp file, validates expected size and checksum when provided, and atomically renames the verified file into place. It still does not perform network downloads or load models, and there is no download UI yet.

MVP 1F now includes an evidence-cited local LLM report generation foundation with prompt construction, Pydantic output validation, invalid JSON retry, hallucination guards, and a localhost-only Ollama-style report runtime adapter with fakeable transport tests. The adapter sends conservative generation options by default, caps prompts before transport, and does not use full long-context model windows by default. No model is bundled or downloaded. A tiny real local Gemma E2B smoke passed on 2026-05-08 against user-installed Ollama `0.23.1` and `gemma4:e2b`; this is not a benchmark or CI requirement.

MVP 1F now includes a default report-model manifest for Gemma 4 E2B-it Q4. The manifest maps user-managed Ollama-style runtimes to `gemma4:e2b`, records the Hugging Face model ID `google/gemma-4-E2B-it`, keeps the default context budget at 8192 tokens, records 16384 tokens as the first maximum tested budget target, and disables automatic downloads. It is configuration metadata only, not a bundled model.

MVP 1F now includes a manual deep-mode report-model manifest for Gemma 4 E4B-it Q4. The deep manifest maps user-managed Ollama-style runtimes to `gemma4:e4b`, records the Hugging Face model ID `google/gemma-4-E4B-it`, caps deep context at 16384 tokens, and falls back to E2B unless the user explicitly selects deep mode while recording is stopped, memory pressure is acceptable, and E4B is available. It is configuration metadata only, not a bundled model.

MVP 2A now includes a selective OCR worker/runtime foundation that processes changed high-value screenshot candidates, skips private or blocked apps, refuses likely secret-risk screens, redacts OCR text, stores OCR results with screenshot evidence links, and reports optional OCR runtime availability without importing heavy OCR packages. It now includes an optional real PaddleOCR adapter path with lazy runtime binding, safe unavailable fallback, per-session OCR job caps, and a local-sample smoke command. PaddleOCR is not bundled, downloaded, or required for normal recording/export; the 2026-05-08 local smoke skipped because PaddleOCR is not installed in this uv environment.

MVP 2A now includes optional audio transcription and command embedding foundations with fakeable engine/model contracts. Audio transcription is disabled by default, private mode suppresses transcription, transcript text is redacted and evidence-linked, command clusters keep evidence event IDs, and no real audio capture or model download is implemented yet.

MVP 2A now includes an optional faster-whisper transcription adapter with lazy runtime binding, a fakeable recognizer contract, a CPU int8 `base` metadata default, and manual-only Distil-Whisper metadata. The real binding requires an explicit local model path before importing faster-whisper so it cannot trigger faster-whisper's model-size auto-download path. The adapter writes only explicit opt-in audio segments to temporary files for transcription and deletes those files after the call. It now has a skip-safe smoke command that reads `WORKTRACE_FASTER_WHISPER_MODEL_PATH` only when explicitly configured and keeps public output free of raw audio bytes, transcript text, and absolute local paths; the 2026-05-08 local smoke skipped because no model path is configured, so no real faster-whisper pass has been recorded yet.

MVP 2A now includes a localhost-only Qwen3 embedding runtime adapter (`Qwen/Qwen3-Embedding-0.6B`) with fakeable JSON transport, redacted embedding payloads, explicit localhost endpoint validation, and a `QwenCommandEmbeddingModel` bridge for deterministic command clustering/search helpers. It now has a skip-safe smoke command that reads `WORKTRACE_QWEN_EMBEDDING_BASE_URL` only when explicitly configured; the 2026-05-08 local smoke skipped because no endpoint is configured, so no real embedding runtime pass has been recorded yet.

MVP 2B now includes a selected-frame vision analysis foundation with secret-risk refusal, cancellation, and fakeable VLM analyzer contracts. It now includes a localhost-only Qwen3-VL selected-frame adapter for user-managed OpenAI-style local VLM services, with Qwen3-VL-2B as the laptop-safe default metadata target and Qwen3-VL-4B left manual-only until benchmarked. It now has a skip-safe smoke command that reads `WORKTRACE_QWEN_VL_BASE_URL` only when explicitly configured; the 2026-05-08 local smoke skipped because no endpoint is configured, so no real Qwen3-VL selected-frame runtime pass has been recorded yet. This does not implement continuous vision, model downloads, bundled VLM weights, or UI deep analysis yet.

MVP 3 now includes a deterministic workflow debugger foundation that derives evidence-cited recipe steps and workflow findings from local timeline events. This does not implement autonomous replay, command execution, UI recipe review, or the formal golden eval runner yet.

MVP 4 now includes 20 compact golden sessions and a deterministic eval runner that prints a reproducible benchmark table for timeline accuracy, blocker metrics, hallucinated evidence, privacy leaks, and estimated resource columns. This is paired with live laptop readiness runner profiles for short recorder smokes and a 30-minute local recorder production-readiness pass; cloud inference and model quality benchmarks remain separate.

MVP 4 now includes an AI report eval benchmark that compares deterministic reports, fake Gemma E2B local report output, fake Gemma E4B deep-mode output, and model-unavailable fallback behavior across the golden sessions. It verifies evidence citation validity, generated-report evidence-ID coverage, privacy leak count, no model call during recording, unavailable fallback handling, summary usefulness proxy, blocker precision/recall proxy, and deterministic latency/memory estimates. It does not prove real Gemma quality or performance; the separate real Gemma E2B smoke is only a tiny end-to-end runtime proof.

MVP 4 now includes deterministic recording resource budget checks, screenshot retention cleanup tests, a fake 30-minute recording budget simulation for CPU, RAM, DB growth, screenshot storage, and model-loaded policy, plus live laptop readiness benchmark profiles that start the real recorder workers in a temporary workspace and emit aggregate metrics only. The benchmark output does not store private screenshots in the repository and keeps cloud/model inference out of scope.

MVP dashboard work now includes desktop-accessible deterministic Markdown and raw JSON export review through the configured local sidecar bridge. The desktop shows preview text, export paths, evidence IDs, safe unavailable/error states, session-folder lookup status, and a local AI report panel with generate/regenerate/cancel controls wired through the typed sidecar boundary. Without a configured local runtime, the panel reports a safe unavailable state and does not fake success.

MVP dashboard work now includes desktop session browser, session deletion, and folder-open integration through the configured local sidecar bridge. The desktop lists all past sessions with event and screenshot counts, allows deleting any session (removing rows and artifact files), shows honest deletion result counts, and launches Windows Explorer for validated session folders.

## Two-Minute Review

WorkTrace AI is a local-first desktop recorder and evidence timeline project. The implemented repo currently proves the foundations: typed contracts, SQLite WAL migrations, fake session storage/export, a Tauri shell, sidecar health, deterministic timeline/export/report foundations, model fallback states, selective AI-worker contracts, workflow debugging rules, golden evals, and deterministic resource budget checks.

The project is a working local-first private-beta candidate for internal/testing use. It now has real Windows active-window polling, compressed PNG screenshot capture with bounded cleanup, metadata-only file watcher capture, explicit safe terminal command ingestion, desktop recorder controls through a configured local sidecar bridge, desktop export review/screenshot metadata/delete UI, a session browser with session deletion through the sidecar bridge, and short plus 30-minute live Windows readiness benchmark paths. It is not publicly distributed through a trusted Windows channel yet, and the readiness benchmark is not a real model quality or cloud inference benchmark.

## Evidence and Verification

- Shared schema tests validate event, session, timeline, finding, report, privacy, confidence, evidence ID, and model metadata contracts.
- Python tests validate storage, migrations, fake sessions, session state, privacy redaction, exports, timeline chunks, report guards, optional AI-worker contracts, workflow debugger rules, golden evals, AI report eval proxies, and resource budgets.
- Desktop tests validate the status shell, sidecar health states, recovery banner preview, raw timeline preview, safe/live session-event bridge states, export review controls, local AI report UI states with a fake bridge response, model settings localhost validation, screenshot metadata/delete states, and session browser list/delete behavior.
- `docs/eval-results.md` records the reproducible golden-session eval command and current aggregate result.
- `docs/evidence/laptop-readiness-2026-05-13.md` records a short local laptop readiness benchmark with aggregate metrics only. It excludes raw active-window titles and deletes temporary screenshots by default.
- `docs/evidence/production-readiness-30-minute-2026-05-26.md` records a 30-minute local recorder readiness benchmark with aggregate metrics only. It keeps cloud inference and model quality out of scope.
- `docs/evidence/gemma-e2b-smoke-2026-05-13.json` records the latest bounded tiny real Gemma E2B Ollama smoke result. The older `docs/evidence/gemma-e2b-smoke-2026-05-08.json` result is retained for history.
- `docs/evidence/paddleocr-smoke-2026-05-08.json` records the PaddleOCR sample smoke result, currently `skipped` because the optional runtime is not installed.
- `docs/evidence/qwen-embedding-smoke-2026-05-08.json` records the Qwen3 embedding smoke result, currently `skipped` because no local endpoint is configured.
- `docs/evidence/qwen-vl-smoke-2026-05-08.json` records the Qwen3-VL selected-frame smoke result, currently `skipped` because no local endpoint is configured.
- `docs/evidence/faster-whisper-smoke-2026-05-08.json` records the faster-whisper local-path smoke result, currently `skipped` because no local model path is configured.
- `docs/evidence/windows-installer-install-run-qa-2026-05-08.json` records the local Windows installer install/run QA result.
- `docs/evidence/private-beta-installed-smoke-2026-05-26.json` records the latest local installed-app private-beta smoke result.
- `docs/release-hardening.md`, `docs/release-channels.md`, `docs/release-checklist.md`, and `docs/evidence/release-hardening-decision-2026-05-26.json` record the current release-channel decision: NSIS is local/internal QA only, source-only alpha milestones are allowed without installable binaries, public Windows distribution is deferred to a future Microsoft Store-compatible MSIX/AppX path, and this is not a fresh Store submission or signed installer QA pass.
- `.github/workflows/ci.yml` runs minimal deterministic GitHub CI for shared contracts, desktop TypeScript, Python sidecar, and Rust/Tauri without secrets, hosted model calls, local model downloads, signing, or release publishing. `.github/workflows/packaging-smoke.yml` is manual-only and does not upload unsigned installer artifacts.
- `docs/private-beta.md` defines the private-beta user promise, demo flow, blockers, release blockers, and evidence required before external beta users.
- `docs/private-beta-installed-smoke.md` documents the local installed-app smoke runner for private-beta installer QA.
- `docs/security/private-beta-security-review-2026-05-26.md` records the focused private-beta security review and remaining release blockers.
- `docs/sample-report.md` shows a deterministic evidence-cited sample report from local fixture-style data.

## Current Limitations

- Active-window, screenshot, configured-folder file watcher, explicit terminal command ingestion, selective OCR guardrails, and desktop start/pause/resume/stop controls are wired through the Python sidecar. The Tauri recorder and event bridge still require a configured localhost sidecar URL or configured local sidecar binary/port; PaddleOCR and model runtimes are not bundled or downloaded.
- Screenshot artifacts are currently stored as compressed PNG files with conservative retention cleanup. JPEG/WebP encoding decisions are documented as deferred until a dedicated image-encoding/runtime issue.
- Terminal command ingestion is manual/API-based only. It does not spy on terminals, keylog, or capture commands unless an explicit logger/hook posts them.
- Privacy hardening covers implemented redaction, private-mode worker suppression, sidecar-backed desktop privacy policy persistence for allow/block lists and clipboard-safe mode, regression proof that session deletion clears session/event/screenshot/OCR rows plus default artifact folders, and a focused private-beta security review. Storage/retention UX hardening remains private-beta work.
- The desktop app now has a session dashboard foundation, sidecar-backed recorder controls, configured sidecar launch/stop handling, deterministic Markdown/raw JSON export review, local AI report controls, screenshot metadata/delete/preview UI, OCR snippets for stored screenshot previews, a session browser with session deletion, and Windows Explorer folder-open integration through the local sidecar bridge.
- The desktop AI report UI is wired through React, Tauri, and FastAPI boundary commands. The current development default is `gemini_gemma_dev`: the sidecar uses `gemma-4-31b-it` through the Gemini API when `GEMINI_API_KEY` is present in a private `.env` or shell environment, and safely reports a missing key when it is unavailable. `local_ollama` remains available for the intended local product path and checks a user-managed localhost Ollama service for `gemma4:e2b` before enabling local report generation. The model settings panel shows localhost setup for local runtimes, beta setup steps, Gemma E2B/E4B status, and explicit unavailable reasons while rejecting remote arbitrary endpoints. It shows model metadata, run time, input hash, and evidence IDs only when the sidecar returns a validated report result, and it never shows full prompt text.
- A localhost-only local report runtime adapter exists for evidence-cited report generation tests and the default sidecar report path, Gemma 4 E2B-it Q4 is the default report-model config (`gemma4:e2b` / `google/gemma-4-E2B-it`), and Gemma 4 E4B-it Q4 is manual deep-mode config only (`gemma4:e4b` / `google/gemma-4-E4B-it`). This only talks to a user-managed local model service, refuses oversized prompts, caps deep mode at 16384 tokens, and falls back to E2B under guardrails. A tiny Gemma E2B Ollama smoke passed locally, but WorkTrace still does not download models or start a model server.
- A model cache manager exists for local paths, disk checks, checksum validation, manual local-file install simulation, and uninstalling exact cached model files. It does not perform network downloads or load models.
- A localhost-only Qwen3 embedding runtime adapter exists for grouped search/retrieval helpers and keeps redacted payloads plus evidence-ID discipline. A Qwen3 embedding smoke command exists and skips safely here because `WORKTRACE_QWEN_EMBEDDING_BASE_URL` is not configured; no real Qwen3 embedding pass has been recorded yet. Persistent vector indexing is still limited to the documented SQLite-first plan.
- An optional faster-whisper transcription adapter exists for explicit audio segments only. It is off by default, private mode suppresses it, `base` CPU int8 is the laptop-safe metadata default, Distil-Whisper is manual-only until benchmarked, and the real binding still requires an explicit local model path before import. A faster-whisper local-path smoke command exists and skips safely here because `WORKTRACE_FASTER_WHISPER_MODEL_PATH` is not configured; no real faster-whisper pass has been recorded yet.
- A localhost-only Qwen3-VL selected-frame adapter exists for fakeable local VLM tests. It requires explicit selected screenshot evidence, refuses likely secret-risk screens through the selected-frame policy layer, and keeps public smoke output free of image bytes, data URLs, and full prompt text. A Qwen3-VL selected-frame smoke command exists and skips safely here because `WORKTRACE_QWEN_VL_BASE_URL` is not configured; no real Qwen3-VL selected-frame pass has been recorded yet.
- Gemini/Gemma hosted inference is a development-only report shortcut. Qwen embeddings, Qwen-VL, faster-whisper, and PaddleOCR remain local-only optional runtimes.
- Selective OCR remains optional backend/runtime work. The desktop screenshot panel can show redacted OCR snippets for stored screenshot previews, but continuous OCR and bundled PaddleOCR are still out of scope. A PaddleOCR sample smoke command exists and skips safely here because PaddleOCR is not installed; no real PaddleOCR pass has been recorded yet.
- Python sidecar packaging is not bundled into the installer unless `pnpm --dir apps/desktop package:sidecar` first produces the expected target-triple sidecar executable for Tauri. The Windows installer build smoke and installer install/run QA passed locally with that artifact present. Direct sidecar QA exposed a cleanup caveat: a PyInstaller child process can remain if the sidecar is launched directly outside Tauri supervision, and silent uninstall left that executable until the process was stopped and the temp QA directory was removed manually. Tauri-managed sidecar stop now uses Windows process-tree cleanup before the normal child kill/wait fallback.
- Local model runtimes are user-managed through localhost services; automatic model downloads are not integrated.
- Installer output is not code-signed and not production-distributed yet. Current NSIS output is for local/internal QA only and must not be attached as a public unsigned GitHub Release installer. `docs/release-hardening.md` now records the future Microsoft Store MSIX/AppX distribution decision, release-channel policy, updater boundary, and sidecar-bundle evidence gate that must pass before public distribution.
- Resource budget checks include deterministic fake samples, storage cleanup tests, a short 5-10 minute live laptop readiness smoke, and a 30-minute local recorder readiness benchmark profile. This does not prove model quality, cloud inference behavior, or public-release readiness.
- AI report eval rows for Gemma E2B/E4B are fake-runtime proxy checks, not real local model benchmarks.
- The real Gemma E2B smoke is a short local proof only; it is not a quality benchmark, memory benchmark, or CI dependency.

## What It Is

WorkTrace AI is a local-first Windows desktop activity recorder and timeline engine. The product direction is to capture local session evidence, build a deterministic timeline, and then use AI only where it can cite the session evidence it used.

## What It Is Not

- Not a chatbot
- Not a cloud surveillance tool
- Not a keylogger
- Not production-ready yet
- Not training or fine-tuning an LLM in the MVP

## Core Principles

- Local-first by default
- No cloud upload by default
- Hosted AI is development-only unless a later product decision changes this
- No keylogging
- Deterministic timeline first, LLM second
- Every AI finding must cite evidence IDs
- Privacy and deletion controls before advanced AI

## Planned Stack

- Tauri v2
- React + TypeScript + Tailwind
- Rust Tauri commands
- Python 3.13 FastAPI sidecar
- SQLite WAL
- Pytest, Vitest, Playwright, Rust tests
- Local pretrained models later, not training in MVP

## MVP Scope

The first realistic MVP is planned to include:

- start/pause/stop session
- active window tracking
- screenshot sampling with duplicate skipping and compressed PNG artifact storage
- file events
- safe terminal command detection
- SQLite storage
- raw timeline
- rule-based chunks
- privacy controls
- Markdown export
- local AI report after session stop/manual request

## Deferred

These are intentionally deferred until the recorder, privacy layer, and deterministic timeline are reliable:

- continuous OCR
- audio narration
- embeddings
- vision model
- workflow debugger
- installer/signing
- cloud sync
- remote AI for shipped product defaults
- fine-tuning

## Local Runtime

- Python 3.13 is the target local-agent runtime.
- Use `uv run --python 3.13 ...` until `services/local-agent/pyproject.toml` pins runtime.
- Default sidecar installs keep heavy model packages out of the laptop-safe path. Use
  `uv sync --extra local-model-runtimes` only when intentionally testing direct local model
  package integrations; the localhost adapters, deterministic timeline, exports, and normal
  tests do not require that extra.
- Short local recorder readiness smoke:
  `uv run --python 3.13 worktrace-laptop-readiness --duration-seconds 300 --sample-interval-seconds 10 --output ..\..\docs\evidence\laptop-readiness-2026-05-13.md`
- 30-minute local recorder readiness benchmark:
  `uv run --python 3.13 worktrace-laptop-readiness --profile production-30-minute --sample-interval-seconds 10 --output ..\..\docs\evidence\production-readiness-30-minute-2026-05-26.md`
- Installed-app private beta smoke:
  `pwsh -File scripts/validation/run-installed-beta-smoke.ps1 -Build`

## Development Rules

Contributors and AI coding agents must read these before making changes:

- `plan.md`
- `docs/coding.md`
- `docs/tauri_rust_rules.md`
- `docs/react_typescript.md`
- `docs/python_LLM.md`

Do not add Tauri, React, Rust, Python, FastAPI, SQLite, capture, OCR, model, or AI runtime code unless the relevant issue explicitly asks for it.

## Roadmap

- MVP 0: Foundation
- MVP 1A: Shell and Sidecar
- MVP 1B: Sessions and Raw Timeline
- MVP 1C: Capture Expansion
- MVP 1D: Privacy, Recovery, Observability
- MVP 1E: Deterministic Timeline and Export
- MVP 1F: Local LLM Report

See `plan.md` and `docs/github-roadmap.md` for the detailed milestone breakdown.
