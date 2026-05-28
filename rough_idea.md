Below is the **real build plan** for WorkTrace AI — phased like an engineering project, not a random MVP.

My recommended stack:

```txt
Desktop: Tauri v2 + React + TypeScript + Tailwind
Local AI service: Python FastAPI sidecar
Storage: SQLite + WAL mode
Event processing: Python workers + local queue
Capture: Python first, Rust later
OCR: PaddleOCR PP-OCRv5
Audio: faster-whisper / Distil-Whisper
Embeddings: Qwen3-Embedding-0.6B
Local LLM: Gemma 4 E2B-it Q4
Vision model: Qwen3-VL-2B-Instruct
Deep mode: Gemma 4 E4B-it Q4
Testing: Pytest + Vitest + Playwright + golden session evals
```

Tauri is a good fit because it is designed for small, fast desktop binaries and supports sidecar binaries, which means you can package your Python AI service with the app instead of asking users to install Python manually. ([Tauri][1])
FastAPI is a strong fit for the local service because it is Python-native, type-hint based, production-ready, and easy to expose local endpoints from. ([FastAPI][2])
SQLite is enough for v1; enable WAL mode because SQLite documents WAL as a mode that improves concurrent read/write behavior and persists at the database-file level. ([SQLite][3])

---

# WorkTrace AI build roadmap

## Phase 0 — Product definition and repo setup

Goal: create a serious repo structure before coding randomly.

### Build

```txt
worktrace-ai/
  apps/
    desktop/                 # Tauri + React UI
  services/
    local-agent/              # Python FastAPI sidecar
  packages/
    shared/                   # shared TypeScript schemas/types
  datasets/
    golden-sessions/          # synthetic test sessions
  evals/
    timeline-evals/           # AI output evaluation
  docs/
    architecture.md
    privacy.md
    model-routing.md
    evals.md
```

### Tasks

1. Create repo structure.
2. Add architecture diagram.
3. Define event schema.
4. Define session schema.
5. Define privacy policy.
6. Define what data is stored locally.
7. Define “no cloud upload by default.”
8. Add `README.md` with honest MVP scope.

### Event schema example

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
  "confidence": 0.98
}
```

### Tests

* Schema validation test.
* Invalid event rejection test.
* Timestamp normalization test.
* Local-only storage test.

### Done when

You can create a fake session JSON, validate it, save it, and load it back.

---

# Phase 1 — Non-AI local recorder

Goal: record useful desktop activity **without any AI yet**.

Do not start with LLMs. First build a strong event pipeline.

## Build

### Desktop UI

In Tauri:

```txt
Start recording
Pause recording
Stop recording
View raw timeline
Open session folder
Export raw JSON
```

### Python local agent

FastAPI endpoints:

```txt
GET  /health
POST /sessions/start
POST /sessions/stop
GET  /sessions
GET  /sessions/{id}
GET  /sessions/{id}/events
POST /events/ingest
```

### Capture modules

Start with Windows because that is your laptop environment.

```txt
active_window_tracker.py
screenshot_sampler.py
keyboard_mouse_counter.py
clipboard_watcher.py
file_watcher.py
terminal_command_detector.py
```

### Store in SQLite

Tables:

```txt
sessions
raw_events
screenshots
file_events
clipboard_events
window_events
terminal_events
artifacts
processing_jobs
```

Use batched writes. Do not write every mouse move separately.

### Capture strategy

```txt
Active window: every 1 sec or on change
Screenshot: every 5 sec
Screenshot diff: skip if visually same
Keyboard/mouse: counts only, not keylogging
Clipboard: hash + type, not raw text by default
File watcher: path + operation
Terminal: command text if safe
```

Important: **Do not build a keylogger.** Track activity patterns, not typed secrets.

### Tests

* Start/stop session test.
* 10-minute fake recording simulation.
* SQLite write/read test.
* Screenshot sampling interval test.
* Duplicate screenshot skip test.
* Keyboard/mouse count aggregation test.
* File watcher event normalization test.
* App crash recovery test.

### Done when

You can record a 10-minute coding session and see this:

```txt
09:14 VS Code active
09:18 Chrome active
09:21 Terminal active
09:22 Command ran: pnpm test
09:23 File changed: app/page.tsx
09:28 VS Code active
```

No AI yet.

---

# Phase 2 — Privacy and security layer

Goal: make privacy core, not an afterthought.

This project becomes much more serious if privacy is built before AI.

## Build

### Privacy features

```txt
App allowlist
App blocklist
Private mode
Screenshot blur mode
Secret redaction
Clipboard safe mode
.env ignore
Browser incognito ignore
Raw screenshot deletion policy
Local encryption option
```

### Secret redaction rules

Detect and redact:

```txt
API keys
JWT tokens
.env values
emails
phone numbers
OTP-like numbers
GitHub tokens
Google API keys
AWS keys
password fields
```

### Storage policy

Use this structure:

```txt
~/.worktrace/
  db/worktrace.sqlite
  sessions/{session_id}/
    screenshots/
    audio/
    exports/
```

### Tests

Create fake screenshots/text containing:

```txt
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
password=mysecret
email@example.com
+91 9876543210
```

Then test:

```txt
redaction_success = true
privacy_leak_count = 0
```

### Done when

No AI model receives raw secrets in prompts.

---

# Phase 3 — Rule-based timeline builder

Goal: convert raw noisy events into useful chunks **without LLM dependency**.

## Build

Create a deterministic timeline engine:

```txt
raw events
  ↓
normalized events
  ↓
activity blocks
  ↓
task chunks
  ↓
basic findings
```

### Activity labels

Start simple:

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

### Chunking rules

Example:

```txt
If same app active for 5+ minutes → one block
If terminal command fails → debugging block starts
If same command repeats 3+ times → repeated action finding
If browser ↔ VS Code switches > 20 times in 30 min → context switching finding
```

### Output example

```json
{
  "session_title": "Portfolio SEO Fix",
  "chunks": [
    {
      "start": "09:14",
      "end": "09:31",
      "label": "coding",
      "summary": "Edited metadata and SEO files",
      "evidence_event_ids": ["evt_1", "evt_2"]
    },
    {
      "start": "09:31",
      "end": "09:38",
      "label": "testing",
      "summary": "Ran SEO tests and hit title length failure",
      "evidence_event_ids": ["evt_3", "evt_4"]
    }
  ]
}
```

### Tests

* Golden raw events → expected chunks.
* Repeated command detector test.
* Idle detector test.
* App-switching detector test.
* Failed command detector test.
* No false “AI hallucinated” events because this phase has no AI.

### Done when

A raw session becomes a basic timeline automatically.

---

# Phase 4 — OCR, audio, and embeddings

Goal: add multimodal extraction, but still keep laptop fast.

## OCR

Use **PaddleOCR PP-OCRv5**. It is designed for multi-scenario text recognition and supports mainstream text types including English, Chinese variants, Pinyin, and Japanese. ([PaddlePaddle][4])

Use OCR only on:

```txt
screenshots with big visual diff
terminal windows
browser error pages
dialog boxes/popups
VS Code test failure screens
```

Do not OCR every frame blindly.

## Audio

Use **faster-whisper** in int8 mode for local transcription. It is a CTranslate2-based Whisper implementation that reports up to 4× faster inference than OpenAI Whisper with lower memory use, and 8-bit quantization further improves efficiency. ([GitHub][5])

Use audio only if user enables narration.

## Embeddings

Use **Qwen3-Embedding-0.6B** for event similarity, workflow clustering, and finding repeated patterns. Qwen3 Embedding provides sizes from 0.6B to 8B and is built for embedding/ranking tasks with multilingual and long-text support. ([Hugging Face][6])

### Build

Tables:

```txt
ocr_results
audio_transcripts
event_embeddings
workflow_clusters
```

### Tests

* OCR extracts terminal error text.
* OCR skips unchanged screenshots.
* Audio transcription produces timestamped segments.
* Embedding similarity groups similar commands.
* No raw screenshot sent to LLM unless user enables visual analysis.

### Done when

You can detect:

```txt
Test failed: expected title length <= 70
Command repeated: pnpm test:seo
User said: "I need to fix Bing title warning"
```

---

# Phase 5 — Local LLM timeline summarizer

Goal: use LLM for structured reasoning, not raw recording.

## Default model

Use **Gemma 4 E2B-it Q4** as the default local brain. Google’s Gemma 4 docs list Q4 memory for E2B at about **3.2 GB**, and E4B at about **5 GB**, which makes E2B the better always-available option for a 16 GB RAM laptop. ([Google AI for Developers][7])

Gemma 4 also uses hybrid attention with local sliding-window and full global attention layers to support long-context efficiency. ([Hugging Face][8])

## Do not feed raw data

Bad:

```txt
Send 2 hours of raw events to model.
```

Good:

```txt
2-minute raw event chunks
  ↓
rule summary
  ↓
OCR snippets
  ↓
Gemma E2B structured JSON
  ↓
final session report
```

### LLM tasks

```txt
summarize_chunk()
infer_task_name()
detect_blocker()
generate_workflow_recipe()
write_final_report()
suggest_automation()
```

### Prompt style

Force JSON output:

```json
{
  "task": "string",
  "summary": "string",
  "blockers": [],
  "repeated_actions": [],
  "important_files": [],
  "commands": [],
  "workflow_steps": [],
  "confidence": 0.0
}
```

Validate with Pydantic/Zod.

### Tests

* Invalid JSON retry test.
* Hallucination guard test.
* Evidence ID required test.
* No finding without event evidence.
* Same input → stable output.
* 20 golden sessions → timeline accuracy score.

### Done when

A session produces:

```txt
Timeline
Blockers
Repeated commands
Important files
Workflow recipe
Suggested automation
```

With evidence.

---

# Phase 6 — Vision model for selected screenshots

Goal: understand GUI/screen context only when needed.

Use **Qwen3-VL-2B-Instruct** for screenshot understanding. Its model card highlights PC/mobile GUI operation, visual agents, OCR improvements, spatial understanding, and visual reasoning, which directly matches WorkTrace’s screen-understanding use case. ([Hugging Face][9])

## When to call vision model

Only call Qwen3-VL if:

```txt
OCR confidence is low
new error dialog appears
browser page changed heavily
user asks "what happened on screen?"
final deep analysis is requested
```

Do not run it continuously.

### Visual tasks

```txt
describe_screen_state()
detect_error_popup()
detect_app_context()
detect_form/password/secret risk
identify important UI element
```

### Tests

* Error dialog screenshot → correct label.
* VS Code test failure screenshot → identifies test failure.
* Browser search screenshot → identifies research phase.
* Secret screen screenshot → refuses detailed extraction.

### Done when

WorkTrace can say:

```txt
09:33 — A test failure appeared in the terminal.
09:41 — Browser showed Bing Webmaster title warning.
09:52 — Deployment dashboard indicated success.
```

---

# Phase 7 — Workflow debugger

Goal: make the killer feature.

This is what makes WorkTrace more than a recorder.

## Build findings engine

Find:

```txt
context switching
repeated commands
long idle gaps
failed commands
same file reopened many times
too much browser searching
test-fix-test loops
deployment verification gaps
unclear blocker period
```

### Example findings

```txt
Finding 1:
You switched between Chrome and VS Code 42 times in 28 minutes.

Finding 2:
pnpm test:seo was run 7 times.

Finding 3:
The blocker was likely unclear test error messaging.

Finding 4:
Suggested automation:
Create a pre-deploy SEO validation script.
```

### Tests

* Repeated command precision.
* Context switching threshold.
* False positive check.
* Known blocker detection.
* Automation suggestion must cite evidence events.

### Done when

The app gives useful insights, not generic productivity advice.

---

# Phase 8 — Replay as recipe

Goal: convert completed work into reusable workflows.

## Build

Generate:

```txt
Workflow title
Goal
Prerequisites
Step-by-step recipe
Commands used
Files changed
Verification steps
Common failure points
Automation opportunity
```

### Example

```txt
Workflow: Deploy portfolio SEO fix

1. Run pnpm test:seo
2. Fix metadata title under 70 chars
3. Fix meta description length
4. Run pnpm build
5. Deploy
6. Verify live HTML title
7. Submit IndexNow URL
```

### Tests

* Recipe steps must come from real events.
* Commands must match captured terminal commands.
* Files must match file watcher events.
* No invented deployment step unless evidence exists.

### Done when

You can record yourself solving a task once, then WorkTrace creates a repeatable checklist.

---

# Phase 9 — UI dashboard

Goal: make it look like a real product.

## Pages

```txt
Home
Sessions
Session detail
Timeline
Findings
Workflow recipe
Privacy center
Model settings
Export report
```

## Session detail layout

```txt
Left: timeline
Middle: selected event/chunk
Right: findings + evidence
Bottom: screenshots/audio/OCR evidence
```

## Must-have UI features

```txt
Start/stop recording
Live event count
CPU/RAM indicator
Privacy mode status
Timeline filter
Export Markdown
Delete raw screenshots
Regenerate report
Deep analysis button
```

### Tests

* Start/stop flow with Playwright.
* Session opens correctly.
* Timeline filters work.
* Export report works.
* Delete session removes artifacts.
* Privacy mode visibly active.

### Done when

You can record, analyze, review, export, and delete a session from UI.

---

# Phase 10 — AI eval system

Goal: prove you understand AI engineering, not just prompting.

## Create 20 golden sessions

Examples:

```txt
1. SEO metadata fix
2. React accessibility bug
3. Python script debugging
4. Git merge conflict
5. Failed deployment
6. Writing a blog
7. Resume update
8. Browser research only
9. Terminal-heavy coding
10. Long idle/distraction session
```

Each golden session has:

```json
{
  "input_events": [],
  "expected_timeline": [],
  "expected_blockers": [],
  "expected_repeated_actions": [],
  "expected_workflow_steps": []
}
```

## Metrics

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
```

### Test command

```bash
pnpm eval:timeline
```

### Done when

You can show a benchmark table in README:

```txt
Timeline accuracy: 0.86
Blocker precision: 0.81
Hallucinated events: 0
Privacy leak count: 0
Average summary latency: 7.4 sec
```

This will impress people because most student AI projects have no evals.

---

# Phase 11 — Laptop performance hardening

Goal: keep your laptop fast.

## Runtime rules

```txt
No model loaded while idle
No continuous VLM
No continuous audio transcription
Batch SQLite writes
Skip duplicate screenshots
Compress screenshots
Use OCR only on changed frames
Unload model after report generation
Cap session raw screenshot count
```

## Suggested limits

```txt
Screenshot interval: 5 sec
OCR interval: only changed frames
Max screenshot width: 1280 px
Audio: off by default
Gemma E2B: session-end or 5-min chunks
Qwen3-VL: selected frames only
Deep mode: manual click only
```

## Performance tests

```txt
30-minute recording test
CPU average under target
RAM average under target
DB size under target
Screenshot folder size under target
No UI freeze
No memory leak
```

### Done when

You can use your laptop normally while recording.

---

# Phase 12 — Packaging and portfolio demo

Goal: make it presentable.

## Build

```txt
Installer
Signed app later
Demo video
Sample exported reports
Architecture docs
Privacy docs
Model-routing docs
Eval results
```

## Demo script

Record yourself doing:

```txt
Fix one bug in your portfolio
Run failing test
Fix issue
Deploy
Verify
Stop recording
Generate WorkTrace report
Show bottlenecks + replay recipe
```

## README sections

```txt
What is WorkTrace AI?
Why local-first?
Architecture
Tech stack
Model router
Privacy design
Demo session
Evaluation results
Limitations
Roadmap
```

### Done when

A recruiter/open-source viewer can understand the project in 2 minutes.

---

# Final implementation order

Do it in this exact order:

```txt
1. Repo + schemas
2. Tauri UI shell
3. FastAPI sidecar
4. SQLite storage
5. Start/stop recording
6. Active window tracking
7. Screenshot sampling
8. File watcher
9. Terminal command detection
10. Privacy redaction
11. Rule-based timeline
12. OCR
13. Audio transcription
14. Embeddings
15. Gemma E2B summaries
16. Workflow debugger
17. Replay recipe
18. Qwen3-VL selected-frame analysis
19. Evals
20. Packaging + demo
```

---

# Best MVP scope

Do **not** try to build full WorkTrace in one shot.

Your first serious MVP should only do this:

```txt
Record desktop session
Track active apps/windows
Capture screenshots every 5 sec
Track file changes
Detect terminal commands
Store in SQLite
Build rule-based timeline
Use Gemma E2B for final report
Export Markdown
```

That alone is already impressive.

---

# Best version for your laptop

Use this model mode:

```txt
Default:
Gemma 4 E2B-it Q4

Only when screenshot understanding is needed:
Qwen3-VL-2B-Instruct

Only when user enables narration:
faster-whisper small/base int8

Only for deep final report:
Gemma 4 E4B-it Q4
```

Gemma 4 E2B is the safest default because its Q4 memory requirement is much lower than E4B, while E4B is better kept as an on-demand “deep mode.” ([Google AI for Developers][7])

---

# What makes this project elite

Most people build:

```txt
chatbot
RAG app
PDF assistant
AI wrapper
```

You build:

```txt
local desktop recorder
event processing engine
privacy redaction system
multimodal extraction pipeline
local model router
workflow debugger
AI eval benchmark
```

That is a **real AI engineering project**.

Final recommendation:

> Build **WorkTrace AI v1 as a local-first desktop recorder + timeline engine**, then add AI gradually.
> Your first goal is not “AI magic.”
> Your first goal is **reliable event truth**.
> Then AI becomes useful instead of fake.

[1]: https://v2.tauri.app/start/?utm_source=chatgpt.com "What is Tauri?"
[2]: https://fastapi.tiangolo.com/?utm_source=chatgpt.com "FastAPI"
[3]: https://sqlite.org/wal.html?utm_source=chatgpt.com "Write-Ahead Logging"
[4]: https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html?utm_source=chatgpt.com "PP-OCRv5 Introduction - PaddleOCR Documentation"
[5]: https://github.com/SYSTRAN/faster-whisper?utm_source=chatgpt.com "Faster Whisper transcription with CTranslate2"
[6]: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B?utm_source=chatgpt.com "Qwen/Qwen3-Embedding-0.6B"
[7]: https://ai.google.dev/gemma/docs/core?utm_source=chatgpt.com "Gemma 4 model overview | Google AI for Developers"
[8]: https://huggingface.co/google/gemma-4-E2B-it?utm_source=chatgpt.com "google/gemma-4-E2B-it"
[9]: https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct?utm_source=chatgpt.com "Qwen/Qwen3-VL-2B-Instruct"
