# Release Hardening

WorkTrace AI is not ready for public Windows distribution yet. The current NSIS
installer path is useful for local/internal QA and installed-app smoke testing,
but it must not be published as a public unsigned installer. The owner-selected
future public Windows channel is a Microsoft Store-compatible MSIX/AppX path,
deferred until Store packaging, certification, signing, update, and install
evidence are validated.

## Current Release State

- Current internal QA target: Windows NSIS setup executable.
- Future public Windows target: Microsoft Store-compatible MSIX/AppX package.
- Installer status: local install/run QA passed on 2026-05-08.
- Signing status: unsigned.
- Updater status: disabled and not configured.
- Release channels: `dev` and local/internal QA are manual only; source-only
  `alpha` milestones may be published without installable binaries; future
  `store-beta` and `store-stable` channels are deferred. See
  `docs/release-channels.md`.
- Sidecar bundle status: the installer includes the Python sidecar only when
  `pnpm --dir apps/desktop package:sidecar` creates the target-triple binary
  before `pnpm --dir apps/desktop package:windows`.
- Local model bundle status: no AI/OCR/audio/VLM models are bundled.

## Distribution And Signing Decision

Owner decision, 2026-05-27:

- Do not purchase a paid direct-distribution Windows code-signing certificate now.
- Do not implement Azure Artifact Signing / Trusted Signing now.
- Do not pursue direct public download distribution of unsigned NSIS/EXE/MSI
  installers.
- Future public Windows distribution should target Microsoft Store-compatible
  MSIX/AppX packaging. Microsoft Store signing applies only after a Store
  submission passes the required Store processing/certification path.
- Current NSIS artifacts remain local/internal QA artifacts only.
- GitHub Releases may be used for release notes, source milestones, and safe
  verification summaries, but not for public unsigned installer downloads.

This means the existing NSIS `.exe` output is not automatically trusted by the
Store decision. Microsoft Store re-signing is relevant to Store MSIX/AppX
submission, not to public GitHub-hosted NSIS/MSI/EXE downloads.

Do not add a fake signing config to `tauri.conf.json`. A placeholder signing
setting would make the repository look more release-ready than it is.

Reference docs:

- Microsoft MSIX signing options:
  `https://learn.microsoft.com/en-us/windows/msix/package/sign-msix-package-guide`
- Microsoft Windows app code-signing options:
  `https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options`
- Tauri Windows code signing: `https://v2.tauri.app/distribute/sign/windows/`
- Tauri Windows installer targets: `https://v2.tauri.app/distribute/windows-installer/`

## Updater And Release Channel Decision

Automatic updates stay disabled. The expected public update mechanism for a
future Store-distributed channel is Microsoft Store-managed updates unless a
separate trusted direct-distribution channel is deliberately approved later.
The Tauri updater should remain disabled for Store/public distribution unless a
later trusted-channel design explicitly requires and verifies it.

- Release channels:
  - `dev`: local/manual development builds only; NSIS packaging and installed-app
    smoke are allowed locally; no public installer binary; no auto-update.
  - `alpha`: source/release-notes engineering prerelease only; no unsigned
    public Windows installer downloads.
  - `store-beta`: future Microsoft Store MSIX/AppX submission channel; deferred.
  - `store-stable`: future stable Microsoft Store channel after beta evidence;
    deferred.
- Transport: no public direct-update endpoint is configured.
- Signatures: do not publish updater artifacts or disable signature verification.
- Metadata: update manifests must not include API keys, local paths, prompt
  bodies, raw evidence, or user machine details.
- Rollout policy: future Store beta/stable releases require Store-compatible
  package evidence, sidecar health smoke, local recording readiness check,
  privacy smoke, uninstall/update cleanup checks, release notes, and certification
  status.

Do not configure updater endpoints now. Adding endpoints before a trusted public
channel is validated would create a stale or unsafe update surface.

Reference docs:

- Tauri updater plugin: `https://v2.tauri.app/plugin/updater/`

The source-only alpha release checklist is maintained in
`docs/release-checklist.md`. The release-notes template is
`docs/release-notes/alpha-template.md`. Local artifact directories can be checked
with `scripts/release/validate-release-artifacts.ps1`; the guard rejects
installable and update-like artifacts for `alpha` by default.

## Sidecar Bundle Assumptions

The desktop app depends on a local Python FastAPI sidecar. Release builds must
prove the sidecar bundle explicitly:

- Build command:
  `pnpm --dir apps/desktop package:sidecar`
- Expected Windows artifact:
  `apps/desktop/src-tauri/binaries/worktrace-local-agent-x86_64-pc-windows-msvc.exe`
- Installer build command:
  `pnpm --dir apps/desktop package:windows`
- Expected installed files:
  `worktrace-desktop.exe`, `worktrace-local-agent.exe`, `uninstall.exe`
- Runtime boundary:
  the sidecar must bind to `127.0.0.1`, use a local database path, and never
  expose hosted AI credentials through React or Rust.
- Cleanup boundary:
  Tauri-managed stop must terminate the sidecar process tree before uninstall
  QA checks for leftover files.

Bundled sidecar proof is not the same as bundled model proof. The release
installer must not claim to include Gemma, Qwen, PaddleOCR, or faster-whisper
models unless a separate model-bundle issue adds and validates that behavior.

## Release QA Evidence Gate

Before a public Store beta or stable release, create a dated evidence file under
`docs/evidence/` that records only safe aggregate data:

- package scripts, Store/MSIX tooling, and versions used
- Store-compatible package path and hash
- Store signing/certification status after submission processing, or explicit
  local-only self-signed test status
- updater config status and channel
- installed file list
- desktop launch smoke result
- sidecar `/health` result
- sidecar process-tree stop result
- silent uninstall result
- leftover file/process check
- privacy notes confirming no secrets, API keys, raw evidence, screenshot pixels,
  or local private paths are included

The current decision evidence is
`docs/evidence/release-hardening-decision-2026-05-26.json`. It is a policy and
gate record, not a fresh Store submission, MSIX/AppX package, or signed installer
QA run.
