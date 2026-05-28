# WorkTrace AI Plan

Date: 2026-05-06

## Purpose

WorkTrace AI is a local-first Windows desktop app that records a user's work session, turns raw desktop activity into a trustworthy timeline, and then uses local AI to produce evidence-backed summaries, blockers, repeated-action findings, and reusable workflow recipes.

The core product bet is simple: do not build another chatbot. Build a reliable activity truth layer first, then use AI only after the app has clean evidence.

## Source Audit

Read before this plan:

- `rough_idea.md`: main product idea, stack, roadmap, model routing, phases, MVP scope.
- `docs/tauri_rust_rules.md`: production rules for Tauri v2, Rust, React, TypeScript, sidecars, privacy, storage, and local AI.
- `docs/react_typescript.md`: frontend production rules.
- `docs/python_LLM.md`: Python, FastAPI, ML, LLM, prompt, eval, and security rules.
- `docs/coding.md`: general production AI coding rules.
- `docs/important.md`: local Windows machine paths and build context.
- `docs/path.md`: native Windows C++ toolchain paths.
- `docs/BUILD_NOTES.md`: CMake/Visual Studio build notes.

Important mismatch:

- `docs/important.md` references `idea.md`, but this repo currently contains `rough_idea.md` instead. Treat `rough_idea.md` as the current idea source unless `idea.md` is restored later.

## Current Repo State

This file began as the initial 2026-05-06 implementation plan. The repository is
no longer planning-only. It now contains a Tauri/React desktop app, Rust Tauri
commands, a Python FastAPI local-agent sidecar, SQLite persistence, real Windows
active-window and screenshot capture foundations, privacy controls, deterministic
timeline/export/report paths, local AI provider boundaries, compact validation
tooling, and Windows packaging smoke evidence.

The active productization source of truth is `docs/private-beta.md`. Use this
plan for original architecture principles and quality gates, not as an accurate
file inventory.

## Product Thesis

Most AI productivity tools fail because they ask an LLM to infer everything from incomplete context. WorkTrace AI should win by collecting structured evidence locally:

- active app and window changes
- safe terminal command events
- file change events
- screenshot samples with diff-based skipping
- optional OCR/audio/vision signals
- deterministic timeline chunks
- AI summaries that must cite evidence IDs

The first goal is not "AI magic." The first goal is reliable event truth.

## Non-Negotiable Principles

1. Local-first by default.
2. No cloud upload unless the user explicitly enables it later.
3. No keylogging.
4. No continuous vision model.
5. No continuous audio transcription by default.
6. No raw secrets sent to AI prompts.
7. Every AI finding must cite evidence event IDs.
8. Deterministic timeline first, LLM second.
9. Privacy and deletion controls must exist before impressive AI features.
10. Performance must keep the laptop usable while recording.
11. No phase is complete until its quality gate passes.
12. README and demo claims must be evidence-backed and honest.

## Enterprise-Grade Gates

Every phase must end with an explicit quality gate. If a toolchain exists in that phase, the command must pass before moving forward. If a toolchain does not exist yet, the phase must state why the command is not applicable and add the missing toolchain setup to the next phase.

### Frontend Gate

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

### Python Gate

Use Python 3.13 explicitly until `services/local-agent/pyproject.toml` pins the runtime.

```powershell
uv run --python 3.13 ruff format .
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
```

### Rust/Tauri Gate

```powershell
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

### Desktop E2E Gate

Run once the app shell exists:

```powershell
pnpm test:e2e
```

### AI/Eval Gate

Run once AI reports or timeline evals exist:

```powershell
uv run --python 3.13 python scripts/evaluate_model.py
uv run --python 3.13 pytest tests/ml_evals
```

## Resource Budgets

These are hard targets for the Windows laptop, not vague goals.

```txt
Recording CPU target: under 10-15% average
RAM target without AI loaded: 500-800 MB
Screenshot interval default: 5 seconds
Screenshot max width: 1280 px
Max screenshot storage per hour: 250 MB before compression/dedup tuning
Normal recording model policy: no LLM, VLM, OCR, or audio model loaded
AI execution policy: after stop or manual request only
Vision policy: selected frames only, never continuous
Audio policy: off by default
SQLite policy: batched writes with WAL mode
UI policy: recording must not freeze the desktop app
```

If a budget fails, the next phase is performance hardening, not feature expansion.

## Crash Recovery

Assume the app, sidecar, or machine can crash mid-session.

Required behavior:

- active sessions use status `recording`
- clean stops use status `stopped`
- crashes or forced exits become status `interrupted`
- partial events remain readable
- partial artifacts remain linked or marked orphaned
- writes are transactional or append-safe
- corrupted writes are avoided through WAL, transactions, and atomic artifact writes
- next launch shows a recovery banner for interrupted sessions
- user can resume review, export partial data, or delete the interrupted session

Recovery tests must simulate:

- sidecar crash during recording
- desktop app crash during recording
- crash during screenshot write
- crash during SQLite batch flush
- next-launch interrupted-session detection

## Migration Strategy

SQLite migrations start on day one.

Rules:

- use versioned migrations
- never mutate DB schema manually
- every migration has an upgrade path
- migrations are idempotent where practical
- destructive migrations require explicit approval
- breaking schema changes require migration tests
- fresh install and upgrade-from-previous-version paths are both tested
- migration failures must leave the previous database readable

Minimum migration tests:

- empty database to latest schema
- v1 database to latest schema
- migration rollback/failure does not corrupt data
- old interrupted session rows remain readable after upgrade

## Local Observability

Use local logs only. Do not add cloud telemetry.

Required observability:

- rotating local log files
- safe log levels: error, warn, info, debug
- operation IDs for sessions, jobs, and model runs
- sidecar lifecycle logs
- capture worker start/stop/error logs
- migration logs
- model load/unload/failure logs
- redacted debug bundle export

Never log:

- secrets
- raw clipboard text
- raw OCR text by default
- full prompts
- screenshots
- auth tokens
- private keys
- full environment variables

Debug bundle export should include:

- app version
- OS/runtime versions
- redacted logs
- database schema version
- job queue summary
- model availability summary
- recent safe error categories

## Model Availability Fallback

Local models can be missing, slow, incompatible, or too large. The app must degrade cleanly.

Required UI states:

```txt
Model not installed
Model loading
Model ready
Model unavailable
Model too slow
Report generation queued
Report generation running
Report generation failed safely
Run without AI
```

Required behavior:

- recording works without any AI model installed
- timeline works without any AI model installed
- export works without any AI model installed
- report generation failure does not damage session data
- user can retry report generation
- model errors are safe and actionable
- model logs include model name/version and safe failure category

## Claim Discipline

The public README, demo, and portfolio description must not overclaim.

Do not claim:

```txt
AI understands your full workflow perfectly.
Automatically knows everything you did.
Fully secure.
Production-ready AI.
Never misses blockers.
```

Preferred claim:

```txt
WorkTrace builds an evidence-backed timeline from local desktop events and generates summaries only from cited session evidence.
```

Every public claim should map to:

- a feature in the app
- a test or eval
- a demo artifact
- a known limitation

## Recommended Stack

Use the stack from `rough_idea.md`, with a few clarifications.

```txt
Desktop shell: Tauri v2
Frontend: React + TypeScript + Tailwind
Native boundary: Rust Tauri commands
Local AI/service layer: Python FastAPI sidecar
Python runtime: Python 3.13.12
Storage: SQLite with WAL mode
Capture v1: Python modules where practical, Rust/native helpers later where needed
OCR: PaddleOCR PP-OCRv5, selectively invoked
Audio: faster-whisper or Distil-Whisper, opt-in only
Embeddings: Qwen3-Embedding-0.6B
Default local LLM: Gemma 4 E2B-it Q4
Deep local LLM: Gemma 4 E4B-it Q4, manual only
Vision: Qwen3-VL-2B-Instruct, selected screenshots only
Testing: Pytest, Vitest, Playwright, Rust tests, golden session evals
```

Why this stack:

- Tauri supports bundled sidecar binaries, including Python API servers packaged with the app. Source: https://v2.tauri.app/develop/sidecar/
- FastAPI is Python-native, type-hint based, and fits a local API service. Source: https://fastapi.tiangolo.com/
- SQLite WAL improves concurrent read/write behavior for local storage. Source: https://www.sqlite.org/wal.html
- PaddleOCR PP-OCRv5 is a strong local OCR candidate, but CPU performance must be measured on this laptop. Source: https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html
- faster-whisper supports CPU int8 and GPU modes, useful for optional local transcription. Source: https://github.com/SYSTRAN/faster-whisper
- Qwen3-Embedding-0.6B supports 100+ languages, 32k context, and up to 1024-dimension embeddings. Source: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- Qwen3-VL-2B-Instruct specifically mentions GUI operation, OCR, spatial understanding, and visual reasoning. Source: https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct
- Gemma 4 E2B/E4B are designed for local/edge usage and multimodal reasoning; still benchmark them locally before committing to a default. Source: https://huggingface.co/google/gemma-4-E2B-it

## Best First MVP

Do not try to build the full roadmap in one pass.

Build MVP 1 as:

```txt
Local desktop recorder
Start/pause/stop sessions
Active app/window tracking
Screenshot sampling every 5 seconds
Duplicate screenshot skipping
File change tracking
Safe terminal command detection
SQLite storage
Raw timeline UI
Rule-based timeline chunks
Privacy controls
Markdown export
Local AI final report after session end
```

Defer these until MVP 1 is stable:

```txt
continuous OCR
audio narration
embeddings
vision model
workflow debugger
automation suggestions
installer/signing
cross-platform capture
cloud sync
remote AI
```

## Architecture

### High-Level Shape

```txt
React UI
  |
  | typed Tauri client
  v
Rust Tauri backend
  |
  | sidecar lifecycle, permissions, path safety
  v
Python FastAPI local agent
  |
  | capture modules, queue, processing workers
  v
SQLite + session artifact folders
  |
  | normalized event streams
  v
timeline engine -> reports -> exports
```

### Ownership Boundaries

Frontend owns:

- rendering
- interaction
- forms and filters
- loading/error/empty states
- calls to a typed Tauri client

Rust owns:

- trusted desktop boundary
- sidecar start/stop/health
- path validation
- minimal Tauri capabilities
- safe filesystem access
- app-level settings
- IPC error normalization

Python sidecar owns:

- local API endpoints
- capture workers
- event normalization
- SQLite repositories
- privacy redaction
- deterministic timeline generation
- model routing and inference workers
- eval runners

SQLite owns:

- session metadata
- raw events
- normalized events
- screenshots/artifacts metadata
- timeline chunks
- findings
- model outputs
- eval results

## Project Structure

Target structure:

```txt
worktrace-ai/
  apps/
    desktop/
      src/
        app/
        components/
        features/
          recorder/
          sessions/
          timeline/
          findings/
          privacy/
          settings/
        lib/
          tauri-client.ts
          schemas.ts
          errors.ts
        types/
      src-tauri/
        src/
          commands/
          domain/
          services/
          state.rs
          config.rs
  services/
    local-agent/
      src/
        worktrace_agent/
          api/
          capture/
          core/
          db/
          domain/
          privacy/
          timeline/
          ai/
          evals/
          workers/
      tests/
  packages/
    shared/
      src/
        event-schema.ts
        session-schema.ts
        report-schema.ts
  datasets/
    golden-sessions/
  evals/
    timeline-evals/
  docs/
    architecture.md
    privacy.md
    model-routing.md
    evals.md
    demo-script.md
```

## Core Data Model

### Event

Every captured fact should become an event. AI must never create facts that do not map back to events.

```json
{
  "id": "evt_001",
  "session_id": "sess_001",
  "timestamp": "2026-05-06T15:22:18+05:30",
  "source": "window_tracker",
  "type": "active_window_changed",
  "app": "VS Code",
  "window_title": "metadata.ts - portfolio",
  "metadata": {
    "process_name": "Code.exe"
  },
  "privacy_level": "safe",
  "confidence": 0.98
}
```

### Session

```json
{
  "id": "sess_001",
  "started_at": "2026-05-06T09:14:00+05:30",
  "ended_at": "2026-05-06T09:58:00+05:30",
  "status": "stopped",
  "title": "Portfolio SEO Fix",
  "storage_path": "~/.worktrace/sessions/sess_001",
  "privacy_mode": "standard"
}
```

### Timeline Chunk

```json
{
  "id": "chunk_001",
  "session_id": "sess_001",
  "start": "2026-05-06T09:14:00+05:30",
  "end": "2026-05-06T09:31:00+05:30",
  "label": "coding",
  "summary": "Edited metadata and SEO files",
  "evidence_event_ids": ["evt_001", "evt_002", "evt_003"],
  "confidence": 0.82
}
```

### Finding

```json
{
  "id": "finding_001",
  "session_id": "sess_001",
  "type": "repeated_command",
  "title": "Repeated SEO test loop",
  "description": "The command pnpm test:seo ran 7 times during one debugging block.",
  "evidence_event_ids": ["evt_010", "evt_014", "evt_019"],
  "severity": "medium",
  "confidence": 0.9
}
```

## Storage Plan

Use this local folder:

```txt
~/.worktrace/
  db/
    worktrace.sqlite
  sessions/
    {session_id}/
      screenshots/
      audio/
      exports/
      logs/
```

SQLite tables:

```txt
sessions
raw_events
normalized_events
screenshots
file_events
clipboard_events
window_events
terminal_events
artifacts
processing_jobs
timeline_chunks
findings
workflow_recipes
model_runs
eval_runs
privacy_redaction_results
```

Required database rules:

- enable WAL mode
- use migrations from day one
- use batched writes
- avoid writing every mouse/key event
- store keyboard and mouse counts only
- store clipboard hash/type by default, not raw clipboard text
- store screenshot metadata separately from image files
- add indexes for `session_id`, `timestamp`, `type`, and `source`

## Capture Strategy

MVP capture modules:

```txt
active_window_tracker.py
screenshot_sampler.py
keyboard_mouse_counter.py
file_watcher.py
terminal_command_detector.py
```

Later capture modules:

```txt
clipboard_watcher.py
audio_recorder.py
ocr_worker.py
vision_worker.py
embedding_worker.py
```

Sampling rules:

```txt
Active window: every 1 second or on change
Screenshot: every 5 seconds
Screenshot diff: skip visually similar frames
Keyboard/mouse: aggregate counts only
Clipboard: hash and MIME/type only by default
File watcher: path, operation, timestamp
Terminal commands: safe command text only, redacted before storage/reporting
```

Do not build:

```txt
raw keylogger
password collector
browser history scraper
always-on microphone recorder
continuous VLM loop
unbounded screenshot retention
```

## Privacy Plan

Privacy must ship before advanced AI.

MVP privacy controls:

- app allowlist and blocklist
- private mode
- pause recording
- delete raw screenshots
- export raw JSON/Markdown
- screenshot blur mode
- clipboard safe mode
- `.env` and secrets redaction
- no cloud upload by default
- local-only model mode

Redact these before AI prompts and exports:

```txt
API keys
JWT tokens
GitHub tokens
Google API keys
AWS keys
password-like fields
.env values
emails
phone numbers
OTP-like numbers
credit-card-like numbers
private keys
```

Privacy test corpus:

```txt
OPENAI_API_KEY=sk-test
GITHUB_TOKEN=ghp_test
AWS_SECRET_ACCESS_KEY=test
password=mysecret
email@example.com
+91 9876543210
-----BEGIN PRIVATE KEY-----
```

Acceptance rule:

```txt
privacy_leak_count = 0
```

## Timeline Engine

The timeline engine should be deterministic first.

Pipeline:

```txt
raw events
  -> normalized events
  -> activity blocks
  -> task chunks
  -> basic findings
  -> AI report
```

Initial labels:

```txt
coding
terminal
browser_research
debugging
testing
deployment
writing
meeting
idle
unknown
```

Initial rules:

- same app active for 5+ minutes creates one activity block
- terminal command failure starts or extends a debugging block
- same command repeated 3+ times creates repeated-command finding
- VS Code/Chrome switching more than 20 times in 30 minutes creates context-switching finding
- no input plus no window change for threshold period creates idle block
- file changes near terminal tests connect files to testing/debugging chunks

## AI Plan

AI should be added in layers.

### Layer 1: Structured Final Report

Run after session stop. Input should be:

```txt
deterministic chunks
redacted terminal commands
redacted OCR snippets
file event summaries
basic findings
evidence IDs
```

Output must be validated JSON:

```json
{
  "session_title": "string",
  "summary": "string",
  "timeline": [],
  "blockers": [],
  "repeated_actions": [],
  "important_files": [],
  "commands": [],
  "workflow_steps": [],
  "confidence": 0.0
}
```

Hard AI rules:

- invalid JSON retries once, then fails safely
- every finding needs evidence IDs
- no evidence, no claim
- do not prompt with raw screenshots unless visual analysis is explicitly requested
- do not prompt with raw secrets
- model output is stored with model name, version, prompt version, input hash, and timestamp

### Layer 2: OCR

Only OCR changed or high-value frames:

- terminal windows
- error dialogs
- test failure screens
- browser warning pages
- popups

Do not OCR every screenshot.

### Layer 3: Embeddings

Use embeddings for:

- similar command grouping
- repeated workflow detection
- session search
- clustering related chunks

Do not use embeddings as a source of truth. They are retrieval and grouping signals only.

### Layer 4: Vision

Use Qwen3-VL only when:

- OCR confidence is low
- an error dialog appears
- the user manually asks what happened on screen
- deep analysis is requested

Do not run it continuously.

## UI Plan

MVP pages:

```txt
Home / Recorder
Sessions
Session Detail
Timeline
Findings
Privacy Center
Model Settings
Export Report
```

Session detail layout:

```txt
Left: timeline list and filters
Middle: selected chunk/event evidence
Right: findings and workflow recipe
Bottom: screenshots/OCR/audio evidence drawer
```

Must-have controls:

- start recording
- pause recording
- stop recording
- live event count
- current privacy mode
- CPU/RAM indicator
- open session folder
- export Markdown
- export raw JSON
- delete session
- delete raw screenshots
- regenerate report
- deep analysis button, disabled until prerequisites are met

Design direction:

- utility dashboard, not a marketing landing page
- dense but readable
- small focused panels
- clear timeline hierarchy
- strong empty/error/loading states
- accessible keyboard navigation
- no nested decorative cards

## Roadmap

The roadmap is intentionally split smaller than a normal "MVP 1" because this project touches desktop capture, privacy, local AI, storage, UI, evals, and packaging. Each milestone should be independently demoable, testable, and issue-trackable.

### Milestone Map

| GitHub Milestone | Purpose | Demo Outcome |
| --- | --- | --- |
| MVP 0: Foundation | Repo, schemas, SQLite, fake session, Python 3.13 policy | Validate and store a fake session locally |
| MVP 1A: Shell and Sidecar | Tauri shell, React UI, FastAPI sidecar health | Desktop app shows local sidecar health |
| MVP 1B: Sessions and Raw Timeline | Start/stop, active window capture, raw events | Record active app/window changes |
| MVP 1C: Capture Expansion | Screenshots, file watcher, safe terminal commands | Show richer raw timeline evidence |
| MVP 1D: Privacy, Recovery, Observability | Redaction, deletion, crash recovery, local logs | Recover interrupted sessions and export redacted debug bundle |
| MVP 1E: Deterministic Timeline and Export | Rule-based chunks, findings, Markdown/raw JSON export | Export an evidence-backed non-AI session report |
| MVP 1F: Local LLM Report | Model availability, fallback states, evidence-cited report | Generate a local AI report after stop/manual request |
| MVP 2A: OCR, Audio, and Embeddings | Selective OCR, optional audio, embeddings | Add multimodal signals without slowing recording |
| MVP 2B: Selected Vision Analysis | Manual selected-frame VLM analysis | Explain selected screenshots with safety checks |
| MVP 3: Workflow Debugger | Bottlenecks, repeated loops, workflow recipes | Turn one solved task into a reusable recipe |
| MVP 4: Evals and Performance Hardening | Golden sessions, resource budgets, benchmarks | Show measurable quality and laptop performance |
| MVP 5: Packaging and Portfolio Demo | Installer, demo artifacts, README claim discipline | Share a truthful portfolio-ready release |

### GitHub Issue Plan

Create one GitHub milestone for each roadmap milestone above. Issues should be small enough that each can be implemented, reviewed, tested, and closed independently.

Recommended issue labels:

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

Initial GitHub issues:

| Issue | Milestone | Labels |
| --- | --- | --- |
| Create repo structure and root README | MVP 0 | `area:docs`, `type:feature` |
| Define event, session, report schemas | MVP 0 | `area:storage`, `type:feature` |
| Add SQLite WAL storage and migrations | MVP 0 | `area:storage`, `type:quality` |
| Add fake session validation and export | MVP 0 | `area:storage`, `type:feature` |
| Scaffold Tauri React desktop shell | MVP 1A | `area:desktop`, `type:feature` |
| Scaffold Python 3.13 FastAPI sidecar health | MVP 1A | `area:sidecar`, `type:feature` |
| Add typed Tauri sidecar lifecycle client | MVP 1A | `area:desktop`, `area:sidecar` |
| Implement session start, pause, stop state machine | MVP 1B | `area:capture`, `type:feature` |
| Capture active window events and raw timeline | MVP 1B | `area:capture`, `area:timeline` |
| Add screenshot sampler with diff skipping | MVP 1C | `area:capture`, `type:performance` |
| Add file watcher and safe terminal command capture | MVP 1C | `area:capture`, `type:feature` |
| Add privacy redaction and deletion controls | MVP 1D | `area:privacy`, `type:security` |
| Add crash recovery and interrupted session banner | MVP 1D | `area:storage`, `type:quality` |
| Add rotating local logs and redacted debug bundle | MVP 1D | `area:privacy`, `type:quality` |
| Build deterministic timeline chunker | MVP 1E | `area:timeline`, `type:feature` |
| Add Markdown and raw JSON export | MVP 1E | `area:timeline`, `type:feature` |
| Add local model availability and fallback states | MVP 1F | `area:ai`, `type:quality` |
| Generate evidence-cited local LLM report | MVP 1F | `area:ai`, `type:feature` |
| Add selective OCR worker | MVP 2A | `area:ai`, `area:capture` |
| Add optional audio transcription and embeddings | MVP 2A | `area:ai`, `type:feature` |
| Add selected-frame vision analysis | MVP 2B | `area:ai`, `type:feature` |
| Add workflow debugger and recipe replay | MVP 3 | `area:timeline`, `area:ai` |
| Add golden sessions and eval runner | MVP 4 | `area:evals`, `type:quality` |
| Enforce resource budgets on Windows laptop | MVP 4 | `type:performance`, `type:quality` |
| Package Windows demo and portfolio README | MVP 5 | `area:docs`, `area:desktop` |

### Phase 0: Foundation

Goal: make the repo serious before app code grows.

#### Phase 0.1: Repo and Documentation Baseline

- repo structure
- README with honest MVP scope
- architecture doc
- privacy doc
- model-routing doc
- Python 3.13 runtime policy for the local agent

#### Phase 0.2: Shared Contracts

- event/session/report schemas
- golden session folder
- CI skeleton

#### Phase 0.3: Local Toolchain Proof

- prove Python 3.13 runtime through `uv run --python 3.13`
- document installed package compatibility for FastAPI, Pydantic, SQLAlchemy, aiosqlite, pytest, ruff, pyright
- document local ML package proof for Torch CPU, PaddlePaddle, PaddleOCR, and faster-whisper
- add `pyproject.toml` target runtime once the local agent exists

Tests:

- schema validation
- invalid event rejection
- timestamp normalization
- local-only storage policy check

Quality gate:

```powershell
uv run --python 3.13 python --version
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
```

Done when:

- a fake session can be validated, saved, loaded, and exported
- docs clearly explain what is local and what is not
- Python 3.13 is the documented local-agent runtime

### Phase 1: Desktop Shell and Sidecar

Goal: boot the app and local service reliably.

#### Phase 1.1: Tauri Shell

- Tauri app shell
- React UI skeleton
- typed Tauri client

#### Phase 1.2: Sidecar Lifecycle

- Rust sidecar lifecycle service
- Python FastAPI health endpoint
- local-only sidecar binding
- safe sidecar logs

#### Phase 1.3: Failure States

- sidecar missing state
- sidecar loading state
- sidecar unhealthy state
- run-without-AI state

Tests:

- Tauri command contract tests where possible
- FastAPI `/health` test
- sidecar missing/error manual test
- UI renders home page

Quality gate:

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Done when:

- desktop app starts
- sidecar starts
- UI can show sidecar health
- failures are visible and safe
- app can launch without AI models installed

### Phase 2: Non-AI Recorder

Goal: record useful activity without AI.

#### Phase 2.1: Session State Machine

- session start/pause/stop
- session statuses: `recording`, `paused`, `stopped`, `interrupted`
- recovery banner on next launch after interrupted session

#### Phase 2.2: Capture Workers

- active window tracking
- screenshot sampling
- screenshot diff skip
- keyboard/mouse count aggregation
- file watcher
- terminal command detection

#### Phase 2.3: Storage and Raw Timeline

- SQLite persistence
- raw timeline view
- crash-safe batch flush
- orphan artifact detection

Tests:

- start/stop session
- 10-minute fake recording simulation
- SQLite write/read
- screenshot interval
- duplicate screenshot skip
- keyboard/mouse aggregation
- file event normalization
- crash recovery

Quality gate:

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Done when:

```txt
09:14 VS Code active
09:18 Chrome active
09:21 Terminal active
09:22 Command ran: pnpm test
09:23 File changed: app/page.tsx
09:28 VS Code active
```

is visible in the app from a real recording.

Resource gate:

```txt
Recording CPU average under 10-15%
RAM without AI loaded under 500-800 MB
Screenshot interval defaults to 5 seconds
No model loaded during normal recording
```

### Phase 3: Privacy and Retention

Goal: prevent the recorder from becoming dangerous.

#### Phase 3.1: Capture Policy

- allowlist/blocklist
- private mode
- screenshot blur mode
- clipboard safe mode

#### Phase 3.2: Redaction and Export Safety

- secret redaction
- raw screenshot deletion policy
- export redaction
- local storage path policy

#### Phase 3.3: Deletion and Retention UX

- delete raw screenshots
- delete session
- retention settings
- deletion audit log without sensitive content

Tests:

- fake secrets are redacted
- private mode suppresses configured sources
- screenshot deletion removes files and DB references
- blocked apps are not recorded
- AI prompt builder refuses unredacted secrets

Quality gate:

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Done when:

- no AI or export receives raw secrets in the privacy test corpus
- debug logs and exports contain zero known test secrets

### Phase 4: Rule-Based Timeline

Goal: turn noisy raw events into understandable work chunks.

#### Phase 4.1: Normalization

- event normalizer
- activity block builder

#### Phase 4.2: Chunking

- task chunk builder
- deterministic findings
- evidence ID linking

#### Phase 4.3: Timeline Review UX

- timeline filters
- evidence viewer for each chunk
- unknown/low-confidence chunk state

Tests:

- golden raw events to expected chunks
- repeated command detector
- idle detector
- app-switching detector
- failed command detector
- evidence IDs required

Quality gate:

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Done when:

- raw sessions become basic timelines without any LLM
- no timeline item is created without source events

### Phase 5: MVP UI Dashboard

Goal: make the recorder usable end to end.

#### Phase 5.1: Session Navigation

- sessions list
- session detail
- timeline filters
- evidence viewer

#### Phase 5.2: Export and Deletion

- export Markdown
- export raw JSON
- delete session
- delete screenshots

#### Phase 5.3: Control Centers

- privacy center
- model availability and settings screen
- local debug logs screen
- recovery banner and interrupted-session actions

Tests:

- Playwright start/stop flow
- session opens correctly
- timeline filters work
- export report works
- delete session removes artifacts
- privacy mode visibly active

Quality gate:

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
pnpm test:e2e
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Done when:

- user can record, review, export, and delete a session from UI
- interrupted sessions are recoverable from UI

### Phase 6: Local LLM Report

Goal: add AI where evidence already exists.

#### Phase 6.1: Model Router and Availability

- model router
- model not installed/loading/ready/unavailable states
- run-without-AI path

#### Phase 6.2: Prompt and Output Contracts

- prompt templates
- Pydantic output schemas
- invalid JSON retry
- hallucination guard

#### Phase 6.3: Report Generation UX

- evidence-required report builder
- report regeneration
- failed-safe report state
- model logs with safe failure categories

Tests:

- invalid JSON retry
- hallucination guard
- no finding without evidence
- same input produces stable enough output
- prompt redaction test
- 5 golden sessions with report expectations

Quality gate:

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
uv run --python 3.13 python scripts/evaluate_model.py
uv run --python 3.13 pytest tests/ml_evals
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Done when:

- session produces evidence-backed summary, blockers, repeated actions, important files, commands, and workflow steps
- report generation can fail without damaging session data

### Phase 7: OCR, Audio, and Embeddings

Goal: enrich evidence selectively.

#### Phase 7.1: OCR

- OCR worker
- OCR trigger policy

#### Phase 7.2: Optional Audio

- optional audio transcription

#### Phase 7.3: Embeddings

- embedding worker
- workflow clustering
- session search

#### Phase 7.4: Package Compatibility Lock

- pin Python 3.13-compatible versions after local proof
- record Torch CPU, PaddlePaddle, PaddleOCR, and faster-whisper package versions
- add model/package availability check endpoint

Tests:

- OCR extracts terminal error text
- OCR skips unchanged screenshots
- audio produces timestamped segments when enabled
- embeddings group similar commands
- raw screenshots are not sent to LLM unless visual analysis is enabled

Quality gate:

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
uv run --python 3.13 pytest tests/ml_evals
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Done when:

- app can detect terminal/test error text and group repeated workflow patterns
- normal recording still runs with no model loaded

### Phase 8: Vision Analysis

Goal: understand selected GUI/screenshots only when needed.

#### Phase 8.1: Selected-Frame Pipeline

- selected-frame visual analysis
- error dialog detection

#### Phase 8.2: Safety and Evidence

- secret-screen refusal
- visual evidence linking

#### Phase 8.3: Deep Analysis UX

- manual deep-analysis flow
- model too slow/unavailable state
- cancellation

Tests:

- error dialog screenshot recognized
- VS Code test failure identified
- browser warning page classified
- secret screen does not get detailed extraction

Quality gate:

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
uv run --python 3.13 pytest tests/ml_evals
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Done when:

- app can add useful visual context without becoming a continuous screen spy
- selected-frame analysis can be cancelled safely

### Phase 9: Workflow Debugger and Recipe Replay

Goal: make the product more than a recorder.

#### Phase 9.1: Findings Engine

- context switching findings
- repeated command findings
- test-fix-test loop detection
- unclear blocker period detection
- deployment verification gap detection

#### Phase 9.2: Recipe Generator

- reusable workflow recipe generator
- command/file/verification extraction
- common failure point extraction

#### Phase 9.3: Evidence Review

- every recipe step cites source events
- UI can jump from recipe step to evidence

Tests:

- repeated command precision
- context switching threshold
- blocker detection
- automation suggestion requires evidence
- recipe steps come only from events

Quality gate:

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
pnpm test:e2e
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
uv run --python 3.13 python scripts/evaluate_model.py
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Done when:

- a completed session becomes a reusable checklist with commands, files, verification steps, and common failure points
- no recipe step is invented without evidence

### Phase 10: Evals and Performance Hardening

Goal: prove quality and keep the laptop fast.

#### Phase 10.1: Golden Evals

- 20 golden sessions
- eval runner
- benchmark table generator

#### Phase 10.2: Resource Monitoring

- resource monitor
- model unload policy
- screenshot cap
- OCR/model batching

#### Phase 10.3: Local Observability

- rotating local logs
- redacted debug bundle export
- migration/job/model run diagnostics

Metrics:

```txt
timeline_accuracy
blocker_precision
blocker_recall
repeated_action_precision
workflow_step_accuracy
hallucinated_event_count
privacy_leak_count
average_latency
peak_ram_usage
db_size_per_hour
screenshot_storage_per_hour
```

Performance targets for MVP:

```txt
Recording CPU average under 10-15%
RAM without AI loaded under 500-800 MB
Max screenshot storage per hour under 250 MB
No UI freeze during recording
No model loaded while idle
No continuous VLM
Screenshots capped and compressed
OCR only on changed/high-value frames
AI report runs after session stop or manual request
```

Quality gate:

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
pnpm test:e2e
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
uv run --python 3.13 python scripts/evaluate_model.py
uv run --python 3.13 pytest tests/ml_evals
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Done when:

- README can show eval metrics honestly
- 30-minute recording does not make the laptop unpleasant to use
- resource budgets pass on the target Windows laptop

### Phase 11: Packaging and Demo

Goal: make it portfolio-ready.

#### Phase 11.1: Packaging

- Windows installer
- sidecar packaging
- model availability setup flow

#### Phase 11.2: Portfolio Artifacts

- demo session
- sample exported reports
- architecture diagrams
- privacy notes
- eval results
- limitations section

#### Phase 11.3: Claim Discipline Review

- README avoids overclaims
- demo script states local/evidence-backed scope
- limitations are visible
- eval table is reproducible

Demo script:

```txt
1. Start WorkTrace.
2. Record a real portfolio bug fix.
3. Run failing test.
4. Fix issue.
5. Run passing test.
6. Stop recording.
7. Generate report.
8. Show timeline, blocker, repeated actions, and workflow recipe.
9. Export Markdown.
10. Delete raw screenshots.
```

Quality gate:

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
pnpm test:e2e
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
uv run --python 3.13 python scripts/evaluate_model.py
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Done when:

- a recruiter/open-source viewer can understand the project in two minutes
- public claims match evidence, tests, and limitations

## First 31 Implementation Tasks

These are the first concrete tasks once coding starts:

1. Create repo folders.
2. Add root README with MVP scope and local-first promise.
3. Add `docs/architecture.md`.
4. Add `docs/privacy.md`.
5. Add `docs/model-routing.md`.
6. Add shared event/session/report schemas.
7. Add schema validation tests.
8. Scaffold Tauri v2 desktop app.
9. Add React/TypeScript/Tailwind setup.
10. Add typed Tauri client wrapper.
11. Scaffold Python FastAPI sidecar.
12. Pin the local agent to Python 3.13 in `services/local-agent/pyproject.toml`.
13. Add `/health` endpoint.
14. Add Rust sidecar start/stop/health command.
15. Add sidecar error display in UI.
16. Add SQLite migration setup.
17. Add sessions table and repository.
18. Add raw events table and repository.
19. Add `POST /sessions/start`.
20. Add `POST /sessions/stop`.
21. Add start/stop UI.
22. Add active window tracker.
23. Add screenshot sampler.
24. Add duplicate screenshot detector.
25. Add file watcher.
26. Add terminal command detector.
27. Add raw timeline endpoint.
28. Add raw timeline UI.
29. Add privacy redaction module.
30. Add rule-based timeline builder.
31. Add Markdown export.

## Testing Strategy

### Python

Use:

```txt
pytest
ruff
pyright or mypy
bandit
pip-audit
```

Run Python checks with Python 3.13 explicitly until `services/local-agent/pyproject.toml` pins the runtime:

```txt
uv run --python 3.13 pytest
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
```

Test:

- API routes
- repositories
- capture normalizers
- privacy redaction
- timeline rules
- model output validators
- eval runner

### Rust/Tauri

Use:

```txt
cargo fmt
cargo clippy
cargo test
```

Test:

- input validation
- path policy
- sidecar lifecycle state
- error mapping
- command contracts

### Frontend

Use:

```txt
pnpm typecheck
pnpm lint
pnpm test
pnpm build
pnpm test:e2e
```

Test:

- start/stop flow
- session list
- timeline filters
- evidence viewer
- privacy mode
- export/delete actions
- error/loading/empty states

### Golden Sessions

Start with these 10, then expand to 20:

1. SEO metadata fix
2. React accessibility bug
3. Python script debugging
4. Git merge conflict
5. failed deployment
6. writing a blog post
7. resume update
8. browser research only
9. terminal-heavy coding
10. long idle/distraction session

## Build Notes for This Machine

Local machine:

```txt
OS: Windows 11 Home
CPU: Intel, 12 logical processors
Workspace: C:\Users\Admin\Desktop\screen-ai
Project Python: Python 3.13.12 at C:\Python313\python.exe
Project pip: pip 26.1.1 at C:\Python313\Lib\site-packages\pip
Python launcher default: Python 3.13.12
uv: 0.10.7
uv note: plain `uv run python --version` currently resolves to Python 3.11.11; use `uv run --python 3.13 ...`
uv workflow: use uv as the default Python workflow for the local agent
MSVC: Visual Studio 18 Build Tools / Community
Windows SDK: 10.0.26100.0
```

Python 3.13 local proof:

```txt
Python 3.13.12 works locally with the planned basic sidecar stack:
FastAPI, Pydantic, SQLAlchemy, aiosqlite, pytest, ruff, and pyright.

Python 3.13.12 also installed and imported the planned local AI/OCR packages:
Torch CPU 2.11.0, PaddlePaddle 3.3.1, PaddleOCR 3.5.0, faster-whisper 1.2.1, and onnxruntime 1.25.1.

PaddlePaddle run_check passed on 1 CPU.
```

Important native build note from existing docs:

```txt
For CMake native Windows projects, use:
cmake -B build -G "Visual Studio 18 2026" -A x64
cmake --build build --config Debug

Avoid Ninja for this repo's native CMake path because docs report manifest.rc failures.
```

For Tauri/Rust work, prefer the normal Tauri toolchain first. Use the CMake notes only if native C++ capture helpers are added later.

## Key Risks

### Privacy Risk

The app records sensitive desktop context. Mitigation:

- local-first defaults
- no keylogging
- no raw clipboard by default
- redaction before AI/export
- private mode
- deletion controls
- no remote telemetry

### Performance Risk

Screenshots, OCR, models, and embeddings can slow the laptop. Mitigation:

- batch writes
- skip duplicate screenshots
- lazy-load models
- unload models after use
- cap screenshot count/size
- run AI after session stop by default

### AI Hallucination Risk

LLMs can invent steps. Mitigation:

- evidence IDs required
- deterministic timeline first
- schema validation
- golden evals
- hallucinated event count metric

### Scope Risk

The rough idea is large. Mitigation:

- ship recorder first
- add privacy before AI
- add one model layer at a time
- keep each phase independently demoable

### Packaging Risk

Bundling Python, OCR, and local models can become difficult. Mitigation:

- start with sidecar health only
- package the Python sidecar before adding heavy models
- keep model downloads/config separate from app core
- support "model unavailable" UI states

## What Not To Build Yet

Avoid these until the core recorder works:

- cloud sync
- team accounts
- paid billing
- browser extension
- mobile app
- always-on VLM
- always-on audio
- full autonomous agent actions
- automatic shell command execution
- remote telemetry
- cross-platform capture abstractions
- fine-tuning

## Definition of Done by Milestone

### MVP 0

- repo structure exists
- README states local-first scope and limitations
- event/session/report schemas exist
- fake session validates, stores, loads, and exports
- SQLite WAL and versioned migrations are in place
- Python 3.13 is pinned or explicitly selected with `uv run --python 3.13`
- Python quality gate passes for created Python code

### MVP 1A

- app starts on Windows
- sidecar starts and reports health
- UI shows healthy, loading, missing, and unhealthy sidecar states
- app can launch without AI models installed
- frontend, Python, and Rust gates pass where toolchains exist

### MVP 1B

- user can start, pause, and stop recording
- session state machine persists `recording`, `paused`, `stopped`, and `interrupted`
- active window events are captured
- raw timeline is visible
- duplicate start/stop actions cannot corrupt session state

### MVP 1C

- screenshots are sampled every 5 seconds by default
- visually duplicate screenshots are skipped
- file changes are captured
- safe terminal commands are captured without keylogging
- recording CPU and RAM stay within the laptop budgets

### MVP 1D

- privacy mode works
- allowlist/blocklist works
- secrets are redacted in prompts, exports, and logs
- session and raw screenshot deletion work
- interrupted sessions recover after crash/restart
- local logs rotate
- redacted debug bundle export contains no known test secrets

### MVP 1E

- deterministic timeline chunks are generated without an LLM
- every timeline chunk cites source events
- basic findings are generated by rules
- Markdown export works
- raw JSON export works
- no export includes unredacted test secrets

### MVP 1F

- model not installed/loading/ready/unavailable/failure states work
- app can run without AI
- local LLM report runs only after stop or manual request
- report claims cite evidence IDs
- invalid JSON and hallucination guard tests pass
- report generation failure does not damage session data

### MVP 2A

- OCR runs only on changed/high-value screenshots
- audio transcription is off by default and opt-in
- embeddings group similar commands/workflows
- normal recording still loads no AI model

### MVP 2B

- vision analysis runs only on selected frames
- secret-risk screens refuse detailed extraction
- vision analysis can be cancelled safely
- no continuous VLM path exists

### MVP 3

- repeated commands, context switching, blocker periods, and test-fix-test loops are detected
- workflow recipe generation works
- every recipe step cites evidence
- no invented recipe step appears in golden evals

### MVP 4

- 20 golden sessions exist
- eval runner produces reproducible metrics
- resource monitor tracks CPU, RAM, DB size, screenshot storage, and model load state
- 30-minute recording stays under resource budgets on the target Windows laptop

### MVP 5

- Windows packaging works
- demo script exists
- sample reports and architecture diagrams exist
- README claim discipline has been reviewed
- public claims match evidence, tests, evals, and limitations

## Final Recommendation

Build WorkTrace AI as a local-first desktop recorder and timeline engine first. Make the evidence layer boring, typed, tested, and private. Then add AI as a report generator that is forced to cite evidence.

The best version of this project is not the one with the most models. It is the one where a viewer can trust every timeline item, every blocker, and every workflow recipe because the app can point to the exact local evidence behind it.
