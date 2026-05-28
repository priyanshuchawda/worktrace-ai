# Private Beta Acceptance Criteria

Status: active private-beta productization plan, 2026-05-26.

WorkTrace AI is a working local-first private-beta candidate for internal and
controlled testing. It is not a public-ready startup release yet. The private
beta goal is to make one core workflow reliable and trustworthy for a small set
of technical users before broad distribution.

## Target User

Primary beta users:

- developers
- students
- indie hackers
- remote knowledge workers

They want a private, evidence-backed summary of what they actually worked on
during a focused session without sending their raw desktop history to a cloud
service by default.

## Primary Promise

Record a work session locally, then get a trustworthy evidence-linked report of
what you worked on, where time went, what blocked you, and what to continue next.

## Primary Demo Flow

1. Install WorkTrace AI on Windows.
2. Launch the app and see a clear privacy setup before recording.
3. Choose capture settings:
   - active-window metadata
   - screenshot sampling
   - optional watched folders for metadata-only file events
   - private mode and blocked apps
   - explicit terminal ingestion only when separately configured
4. Start a real coding, study, or work session.
5. Pause, resume, and stop the recording reliably.
6. Review the local timeline, screenshots, OCR snippets, and file/activity
   metadata.
7. Generate a local evidence-cited report through the beta-supported local AI
   path, or see a clear setup path when the runtime is missing.
8. Inspect report evidence IDs and supporting local evidence.
9. Export a local report or keep it private.
10. Delete the whole session and verify local artifacts are removed.

## Private Beta Ready Means

- New users can understand what is captured before pressing Record.
- Recording cannot start before explicit first-run capture consent.
- Privacy settings are persisted and applied to new recordings.
- Start, pause, resume, stop, restart, and interrupted-session recovery work in
  the installed app path.
- Screenshot review, OCR snippets, folder-open, export, and session deletion are
  usable without developer docs.
- Reports are evidence-cited and visibly tied to local session evidence.
- Missing local AI runtime/model states are actionable for a beta user.
- Development Gemini/Gemma remains explicit-enable, labelled, and non-default.
- A private beta smoke proves the installed app can complete the primary demo
  flow without committing private artifacts.
- No paid service, certificate, or external distribution step is required for
  active development unless the owner explicitly approves it.

## Private Beta Foundation Status

The initial P0 safety foundation has been implemented. Remaining private-beta
work is now focused on release trust, CI, product value, navigation, safe
sharing, and longer real-world proof.

| Area | Status |
| --- | --- |
| Product truth and beta checklist | Implemented in #158 |
| First-run onboarding and recording privacy setup | Implemented in #159 |
| Beta-usable local AI report setup path | Implemented in #160 |
| Installed-app end-to-end private beta smoke | Process smoke implemented in #161; manual demo-flow evidence remains required before external beta |
| Complete deletion, retention, and cross-worker privacy proof | Deletion/OCR/artifact regression proof and privacy docs updated in #162 |
| Private-beta security review | Focused review recorded in #163; release and distribution blockers remain #132/#165/#179 |

## External Beta Release Blockers

These block broad external distribution, but not local active development:

| Blocker | Tracking issue |
| --- | --- |
| Minimal CI gates before external beta | Secret-free deterministic GitHub Actions implemented in #132 |
| Future Microsoft Store MSIX/AppX distribution path | #179 |
| Safe release channels and updater policy | Policy, checklist, template, and local artifact guard implemented in #165 |

Owner distribution decision, 2026-05-27:

- Do not buy a paid Windows code-signing certificate now.
- Do not implement Azure Artifact Signing or Trusted Signing now.
- Do not publish unsigned NSIS/MSI/EXE installers as public GitHub Release downloads.
- Future public Windows distribution should target a Microsoft Store-compatible
  MSIX/AppX submission path, where Store signing happens only after Store
  submission/certification processing.
- Current NSIS artifacts remain local/internal QA only.

Do not spend money, enable paid services, reserve Store identity, submit to
Partner Center, or configure public distribution without explicit owner approval.

## Product Value Next

After the P0 blockers, the next value work is:

| Product area | Tracking issue |
| --- | --- |
| Useful daily work review report | #166 |
| Timeline filtering and local evidence search | #167 |
| Session goals, tags, and report organization | #168 |
| Privacy-safe report export/sharing | #169 |
| Real local model quality/latency/memory benchmark | #170 |
| Multi-hour recording storage and laptop impact | #171 |
| Privacy-safe diagnostics bundle | #172 |

## Evidence Required Before Private Beta

- first-run onboarding tests and desktop UX smoke
- local sidecar start/stop/restart evidence
- installed-app smoke evidence from `scripts/validation/run-installed-beta-smoke.ps1`
- primary demo flow manual installed-app smoke
- deletion and retention regression proof
- privacy/security review notes with tracked release blockers
- local AI runtime setup guidance, report availability checks, and installed-app
  smoke evidence
- no-secrets scan over tracked files and committed evidence

## Hard Privacy Boundaries

- No keylogging.
- No global terminal spying.
- No hidden cloud upload.
- No raw screenshots, raw artifacts, unrestricted OCR text, or raw event dumps
  to hosted models by default.
- No API keys in React, Tauri IPC payloads, SQLite reports, logs, exports, issue
  comments, or PR descriptions.
- AI claims must cite known evidence IDs.
- Captured evidence is untrusted input; model output is untrusted output.
