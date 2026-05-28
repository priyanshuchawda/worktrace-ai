# WorkTrace AI Startup Product Brief

## One-Line Pitch

WorkTrace AI is a privacy-first Windows desktop recorder that turns a local work session into an evidence-backed timeline and a cited AI work report.

## MVP Status

The MVP is a working private-beta candidate for internal testing. The core product loop is implemented:

- Record a local desktop work session.
- Capture active-window events, local screenshot metadata/previews, optional file-watch metadata, and explicit terminal command ingestion.
- Keep raw evidence and artifacts local by default.
- Configure privacy controls before recording.
- Review a searchable timeline and evidence.
- Generate evidence-linked reports through the intended local model path, with a development-only Gemini/Gemma shortcut available only when explicitly configured.
- Export private local reports or share-safe Markdown.
- Delete sessions and related local artifacts.
- Export privacy-safe diagnostics for beta support.

Not public-release ready yet:

- Public Windows distribution is not ready.
- Current NSIS output is internal QA only.
- Future public Windows distribution should use the deferred Microsoft Store MSIX/AppX path.
- Longer real-world storage/laptop-impact proof and real local model quality benchmarks remain important private-beta work.

## Product Journey

1. User installs or runs WorkTrace AI on Windows.
2. First launch shows a privacy setup screen before recording is allowed.
3. User selects a preset such as Private/Safe, Coding Session, or Study/Work.
4. User optionally enters a session title, goal, project label, tags, and watched folders.
5. User starts recording.
6. WorkTrace records local evidence from allowed capture paths.
7. User pauses, resumes, or stops the session.
8. User reviews timeline events, screenshot metadata/previews, and evidence IDs.
9. User generates an evidence-linked work report.
10. User exports a private local report or a share-safe Markdown report.
11. User deletes the whole session if they want to remove local evidence.
12. If something breaks, user creates a privacy-safe diagnostics bundle without sending raw work data.

## Primary User Promise

Record a work session locally, then get a trustworthy evidence-linked report of what you worked on, where time went, what blocked you, and what to continue next.

## 4-Slide Pitch Deck

### Slide 1: Problem

Knowledge workers lose track of what they actually worked on.

Pain points:

- Daily standups, timesheets, progress reports, and handoffs are often reconstructed from memory.
- Existing activity trackers can feel invasive or cloud-first.
- Screenshots, terminal activity, files, and app usage are sensitive.
- AI-generated summaries are hard to trust when they do not cite evidence.
- Developers, students, indie hackers, and remote workers need useful work recall without surveillance.

### Slide 2: Solution and Key Features

WorkTrace AI records local work evidence and turns it into a cited work report.

Key features:

- Windows-first desktop recorder.
- Local-first evidence capture.
- First-run privacy setup before recording.
- Start, pause, resume, and stop recording controls.
- Active-window timeline.
- Local screenshot metadata and preview.
- Metadata-only file-watch roots.
- Explicit terminal ingestion only, no global terminal spying.
- Evidence IDs attached to report claims.
- Local AI report path for real product direction.
- Development-only Gemini/Gemma report shortcut for fast iteration.
- Share-safe Markdown export.
- Complete session deletion and privacy-safe diagnostics.

### Slide 3: Tools and Tech Stack

Product architecture:

- React and TypeScript desktop UI.
- Tauri v2 Windows desktop shell.
- Rust Tauri commands and localhost sidecar bridge.
- Python 3.13 FastAPI local-agent sidecar.
- SQLite WAL persistence.
- Local artifact folders for screenshots, exports, and session data.
- Deterministic timeline/export/report layers.
- Local Ollama-compatible AI runtime for intended product reports.
- Gemini API-hosted Gemma used only as an explicitly configured development shortcut.

Development stack:

- PowerShell on Windows.
- pnpm for TypeScript desktop/shared packages.
- uv for Python service tooling.
- cargo for Rust/Tauri checks.
- Local compact validation scripts and deterministic tests.

### Slide 4: ICP

Ideal Customer Profile:

- Developers who want an accurate local record of coding sessions.
- Students who want evidence-backed study/work summaries.
- Indie hackers who need progress notes without manual journaling.
- Remote knowledge workers who need private daily work reviews.
- Freelancers who need local proof of work before writing client updates.

Best early adopters:

- Privacy-conscious technical users.
- Solo builders and small teams.
- People already doing daily standups, client updates, timesheets, learning logs, or project journals.

Initial wedge:

Developers and indie hackers who want a private local session recorder that produces a useful, evidence-cited daily work review.

## Private-Beta Success Criteria

WorkTrace AI becomes beta-usable when:

- A new user understands what is captured before recording.
- Privacy controls are clear and persist across sessions.
- Recording and sidecar lifecycle are reliable.
- The user can review evidence without UI overflow or confusing states.
- Reports are useful and cite valid evidence IDs.
- Share-safe export does not leak screenshots, OCR text, raw events, terminal secrets, prompts, reports, paths, or API keys by default.
- Session deletion removes local evidence and artifacts clearly.
- Diagnostics help debug issues without exposing captured work.

