# GitHub Roadmap

Date: 2026-05-06

This file is the GitHub tracking source of truth for WorkTrace AI. Each milestone is intentionally small enough to produce a demoable, testable slice.

## Labels

Use these labels for the initial issue set:

```txt
area:desktop
area:sidecar
area:storage
area:capture
area:privacy
area:timeline
area:ai
area:evals
area:docs
type:feature
type:quality
type:security
type:performance
```

## Milestones

| Milestone | Goal | Exit Criteria |
| --- | --- | --- |
| MVP 0: Foundation | Repo, schemas, SQLite, fake session, Python 3.13 policy | Fake session validates, stores, loads, and exports |
| MVP 1A: Shell and Sidecar | Tauri shell, React UI, FastAPI sidecar health | Desktop app shows sidecar health and safe failure states |
| MVP 1B: Sessions and Raw Timeline | Start/stop, active window capture, raw timeline | Active app/window recording is visible in UI |
| MVP 1C: Capture Expansion | Screenshots, file watcher, terminal commands | Raw timeline has screenshot/file/terminal evidence |
| MVP 1D: Privacy, Recovery, Observability | Redaction, deletion, crash recovery, local logs | Interrupted sessions recover and debug bundle is redacted |
| MVP 1E: Deterministic Timeline and Export | Rule chunks, findings, Markdown/raw JSON export | Non-AI evidence-backed report exports |
| MVP 1F: Local LLM Report | Model availability, fallback states, local AI report | Report cites evidence and fails safely |
| MVP 2A: OCR, Audio, and Embeddings | Selective OCR, optional audio, embeddings | Multimodal evidence is opt-in/selective |
| MVP 2B: Selected Vision Analysis | Manual selected-frame VLM analysis | Vision runs only on selected frames |
| MVP 3: Workflow Debugger | Bottlenecks, repeated loops, recipe replay | Completed session becomes a reusable recipe |
| MVP 4: Evals and Performance Hardening | Golden sessions, resource budgets, benchmarks | README can show honest benchmark results |
| MVP 5: Packaging and Portfolio Demo | Installer, demo artifacts, claim discipline | Portfolio-ready release with truthful claims |

## Issue Backlog

### MVP 0: Foundation

#### Create repo structure and root README

Labels: `area:docs`, `type:feature`

Scope:

- Create `apps/`, `services/`, `packages/`, `datasets/`, `evals/`, and docs folders.
- Add README with local-first scope, limitations, and claim discipline.
- Document Python 3.13 as the local-agent runtime.

Acceptance:

- Repo structure exists.
- README avoids overclaiming.
- README says: "WorkTrace builds an evidence-backed timeline from local desktop events and generates summaries only from cited session evidence."

#### Define event, session, report schemas

Labels: `area:storage`, `type:feature`

Scope:

- Define shared event/session/report contracts.
- Include evidence IDs, confidence, privacy level, timestamps, and source fields.

Acceptance:

- Valid schema tests pass.
- Invalid event tests reject missing IDs, invalid timestamps, and missing source.

#### Add SQLite WAL storage and migrations

Labels: `area:storage`, `type:quality`

Scope:

- Add SQLite setup with WAL mode.
- Add versioned migrations.
- Add migration tests for fresh install and upgrade path.

Acceptance:

- WAL mode is enabled.
- Migration tests pass.
- No schema changes happen outside migrations.

#### Add fake session validation and export

Labels: `area:storage`, `type:feature`

Scope:

- Create fake session fixture.
- Save/load/export fake session.
- Export redacted raw JSON.

Acceptance:

- Fake session round trip passes.
- Export contains no secrets from test corpus.

### MVP 1A: Shell and Sidecar

#### Scaffold Tauri React desktop shell

Labels: `area:desktop`, `type:feature`

Scope:

- Create Tauri v2 app shell.
- Add React, TypeScript, Tailwind.
- Add basic Home screen with status panels.

Acceptance:

- App starts on Windows.
- `pnpm typecheck`, `pnpm lint`, `pnpm test`, and `pnpm build` pass.

#### Scaffold Python 3.13 FastAPI sidecar health

Labels: `area:sidecar`, `type:feature`

Scope:

- Create `services/local-agent`.
- Pin Python 3.13 in `pyproject.toml`.
- Add FastAPI `/health` endpoint.

Acceptance:

- `uv run --python 3.13 pytest` passes.
- `/health` returns app version, schema version, and status.

#### Add typed Tauri sidecar lifecycle client

Labels: `area:desktop`, `area:sidecar`, `type:quality`

Scope:

- Add Rust sidecar lifecycle commands.
- Add typed frontend client.
- Add sidecar loading, healthy, unhealthy, and missing states.

Acceptance:

- UI shows sidecar health.
- Missing sidecar produces safe user-facing error.

### MVP 1B: Sessions and Raw Timeline

#### Implement session start, pause, stop state machine

Labels: `area:capture`, `type:feature`

Scope:

- Implement session statuses: `recording`, `paused`, `stopped`, `interrupted`.
- Persist status transitions.

Acceptance:

- Start/pause/stop tests pass.
- Duplicate start does not corrupt session state.

#### Capture active window events and raw timeline

Labels: `area:capture`, `area:timeline`, `type:feature`

Scope:

- Capture active app/window title at safe interval.
- Store raw events.
- Render raw timeline in UI.

Acceptance:

- 10-minute fake recording simulation passes.
- Raw timeline shows app/window changes in order.

### MVP 1C: Capture Expansion

#### Add screenshot sampler with diff skipping

Labels: `area:capture`, `type:performance`

Scope:

- Capture screenshots every 5 seconds by default.
- Resize to max width 1280 px.
- Skip visually similar screenshots.
- Cap screenshot storage per hour.

Acceptance:

- Duplicate screenshot skip tests pass.
- Recording CPU average remains under 10-15%.

#### Add file watcher and safe terminal command capture

Labels: `area:capture`, `type:feature`

Scope:

- Capture file path and operation metadata.
- Capture safe terminal commands after redaction.
- Avoid keylogging.

Acceptance:

- File event normalization tests pass.
- Terminal commands redact secrets before storage/reporting.

### MVP 1D: Privacy, Recovery, Observability

#### Add privacy redaction and deletion controls

Labels: `area:privacy`, `type:security`

Scope:

- Add allowlist/blocklist, private mode, clipboard safe mode, and screenshot deletion.
- Add secret redaction for prompts, exports, and logs.

Acceptance:

- Privacy leak count is 0 against test corpus.
- Deleting screenshots removes files and database references.

#### Add crash recovery and interrupted session banner

Labels: `area:storage`, `type:quality`

Scope:

- Mark crash-affected sessions `interrupted`.
- Preserve readable partial events.
- Show recovery banner on next launch.

Acceptance:

- Simulated sidecar crash test passes.
- Interrupted session can be reviewed, exported, or deleted.

#### Add rotating local logs and redacted debug bundle

Labels: `area:privacy`, `type:quality`

Scope:

- Add local rotating logs.
- Add redacted debug bundle export.
- Include schema version, model availability, and safe error categories.

Acceptance:

- Debug bundle contains no secrets from test corpus.
- Logs never include raw screenshots, clipboard text, or full prompts.

### MVP 1E: Deterministic Timeline and Export

#### Build deterministic timeline chunker

Labels: `area:timeline`, `type:feature`

Scope:

- Normalize events.
- Build activity blocks and task chunks.
- Require evidence IDs for every chunk.

Acceptance:

- Golden raw events produce expected chunks.
- No chunk exists without source events.

#### Add Markdown and raw JSON export

Labels: `area:timeline`, `type:feature`

Scope:

- Export deterministic timeline to Markdown.
- Export redacted raw JSON.
- Include evidence references.

Acceptance:

- Export tests pass.
- Markdown report does not include unredacted secrets.

### MVP 1F: Local LLM Report

#### Add local model availability and fallback states

Labels: `area:ai`, `type:quality`

Scope:

- Add states for model not installed, loading, ready, unavailable, too slow, failed safely, and run without AI.

Acceptance:

- Recording, timeline, and export work with no model installed.
- Model failure does not damage session data.

#### Generate evidence-cited local LLM report

Labels: `area:ai`, `type:feature`

Scope:

- Build prompt templates.
- Validate JSON output with Pydantic.
- Require evidence IDs for every claim.

Acceptance:

- Invalid JSON retry test passes.
- Hallucination guard rejects claims without evidence.

### MVP 2A: OCR, Audio, and Embeddings

#### Add selective OCR worker

Labels: `area:ai`, `area:capture`, `type:feature`

Scope:

- Run OCR only on changed/high-value screenshots.
- Store OCR results with evidence links.

Acceptance:

- OCR extracts terminal error text.
- OCR skips unchanged screenshots.

#### Add optional audio transcription and embeddings

Labels: `area:ai`, `type:feature`

Scope:

- Add opt-in audio transcription.
- Add embedding worker for search and workflow grouping.

Acceptance:

- Audio off by default.
- Similar commands cluster correctly in tests.

### MVP 2B: Selected Vision Analysis

#### Add selected-frame vision analysis

Labels: `area:ai`, `type:feature`

Scope:

- Analyze selected screenshots only.
- Detect error dialogs and secret-risk screens.
- Support cancellation.

Acceptance:

- Secret screen refuses detailed extraction.
- Vision never runs continuously.

### MVP 3: Workflow Debugger

#### Add workflow debugger and recipe replay

Labels: `area:timeline`, `area:ai`, `type:feature`

Scope:

- Detect repeated commands, context switching, test-fix-test loops, blockers, and deployment gaps.
- Generate workflow recipe from evidence.

Acceptance:

- Every recipe step cites event evidence.
- No invented workflow step appears in golden evals.

### MVP 4: Evals and Performance Hardening

#### Add golden sessions and eval runner

Labels: `area:evals`, `type:quality`

Scope:

- Create 20 golden sessions.
- Track timeline accuracy, blocker precision/recall, hallucinated event count, privacy leak count, latency, RAM, and storage.

Acceptance:

- Eval command produces reproducible benchmark table.

#### Enforce resource budgets on Windows laptop

Labels: `type:performance`, `type:quality`

Scope:

- Add resource monitor.
- Enforce no model loaded during recording.
- Track CPU, RAM, DB size, and screenshot storage per hour.

Acceptance:

- 30-minute recording stays under CPU/RAM/storage budgets.

### MVP 5: Packaging and Portfolio Demo

#### Package Windows demo and portfolio README

Labels: `area:docs`, `area:desktop`, `type:feature`

Scope:

- Build Windows installer.
- Add demo script, sample reports, diagrams, privacy notes, eval results, and limitations.

Acceptance:

- A viewer can understand the project in two minutes.
- Public claims match evidence, tests, and limitations.
