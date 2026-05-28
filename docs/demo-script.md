# WorkTrace AI Demo Script

This script is for a private-beta product demo using safe, synthetic work. Do
not record or publish private desktop content, screenshots, OCR text, terminal
secrets, API keys, or `.env` values.

## Demo Goal

Show that WorkTrace AI can record a local work session, review evidence, and
produce an evidence-linked report without hidden cloud upload or surveillance.

## Setup

Start the local sidecar:

```powershell
cd C:\Users\Admin\Desktop\workaudit-ai\services\local-agent
uv run worktrace-local-agent
```

Start the desktop app:

```powershell
cd C:\Users\Admin\Desktop\workaudit-ai\apps\desktop
$env:WORKTRACE_SIDECAR_URL="http://127.0.0.1:8765"
pnpm tauri dev
```

Optional report runtime:

- Product path: user-managed local Ollama with `gemma4:e2b`.
- Development shortcut: private `GEMINI_API_KEY` with `gemini_gemma_dev`.

## Live Demo Flow

1. Open WorkTrace AI.
2. Point out the status strip:
   - sidecar health
   - recorder state
   - report runtime state
3. Complete first-run privacy setup.
4. Select the `Coding session` preset.
5. Enter:
   - title: `Demo coding session`
   - goal: `Fix one small test and summarize the session`
   - project: `workaudit-ai`
   - tags: `demo, coding`
6. Start recording.
7. Switch through safe demo apps:
   - editor
   - terminal
   - documentation/browser page
8. Pause and resume recording once.
9. Stop recording.
10. Open Timeline.
11. Search/filter evidence and select a timeline event.
12. Open Screenshot evidence and show that previews stay local.
13. Open Reports.
14. Generate a report if the configured runtime is available.
15. Click report evidence IDs and show the supporting timeline evidence.
16. Preview share-safe Markdown.
17. Open Sessions and delete the demo session.
18. Open Privacy and preview a privacy-safe diagnostics bundle.

## Talk Track

Problem:

- People reconstruct work reports from memory.
- Existing trackers often feel invasive or cloud-first.
- AI summaries are hard to trust when they do not cite evidence.

Solution:

- WorkTrace records local session evidence.
- It builds a deterministic timeline.
- AI reports must cite evidence IDs.
- Raw evidence stays local by default.

Privacy:

- No keylogging.
- No global terminal spying.
- No browser history capture.
- No hidden cloud upload.
- Terminal ingestion is explicit only.
- Hosted Gemini/Gemma is development-only and report-only.

Close:

- WorkTrace is a private-beta candidate, not a public Windows release yet.
- NSIS packaging is internal QA only.
- Future public Windows distribution is planned through Microsoft Store
  MSIX/AppX after that path is validated.

## Verification After Demo

Run the manual checklist in [`manual-testing.md`](manual-testing.md) if the demo
is being used as private-beta evidence.
