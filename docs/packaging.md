# Packaging

See `../plan.md` for the full packaging roadmap.

## Windows installer target

The desktop package now has an explicit NSIS packaging command:

```powershell
pnpm --dir apps/desktop package:windows
```

This maps to:

```powershell
tauri build --bundles nsis
```

The Tauri config targets the NSIS installer and uses `currentUser` install mode.
This follows the current internal QA path. NSIS is not the public distribution
target for WorkTrace AI. Future public Windows distribution is intended to use a
Microsoft Store-compatible MSIX/AppX path after Store packaging and certification
are explicitly validated.

## Python sidecar executable target

The Python local agent now has a thin executable entrypoint:

```powershell
cd services/local-agent
uv run --python 3.13 python -m worktrace_agent
```

The entrypoint reads only local sidecar launch settings:

- `WORKTRACE_SIDECAR_HOST`, defaulting to `127.0.0.1` and rejecting non-local hosts.
- `WORKTRACE_SIDECAR_PORT`, defaulting to `8765`.
- `WORKTRACE_DB_PATH`, defaulting to `~/.worktrace/db/worktrace.sqlite`.

Session artifacts default under the local database root. For example, with the
default database path, session artifacts live under:

```txt
~/.worktrace/sessions/{session_id}/
```

The desktop package has a sidecar build helper:

```powershell
pnpm --dir apps/desktop package:sidecar
```

That command uses PyInstaller through the uv-managed Python 3.13 local-agent
environment and prepares the target-triple binary expected by Tauri. On the
current Windows target, the expected output is:

```txt
apps/desktop/src-tauri/binaries/worktrace-local-agent-x86_64-pc-windows-msvc.exe
```

The generated binary directory is git-ignored because it is a local build
artifact, not source code.

Tauri is configured with:

```json
"externalBin": [
  "binaries/worktrace-local-agent"
]
```

Tauri v2 requires the on-disk sidecar artifact to include the current target
triple suffix before `tauri build` runs. Packaging-ready sidecar binary lookup exists.
The Rust sidecar service checks a configured `WORKTRACE_SIDECAR_BIN`, a sidecar
beside the app executable, or a sidecar under a sibling `sidecars/` folder.

## Sidecar launch status

The Tauri sidecar service can now use a configured local Python sidecar bridge
without requiring a manual `WORKTRACE_SIDECAR_URL` in the normal code path:

- `WORKTRACE_SIDECAR_PORT` selects the localhost port for health, event, and
  recorder-control requests.
- `WORKTRACE_SIDECAR_BIN` selects a local sidecar executable/script to start.
  If it is absent, the desktop looks for a packaged `worktrace-local-agent`
  executable next to the desktop app or under a sibling `sidecars/` folder.
- `WORKTRACE_SIDECAR_ARGS` passes simple whitespace-separated arguments without
  invoking a shell.
- `WORKTRACE_DB_PATH` can point the Python sidecar at a specific SQLite file;
  session artifacts are stored under the database parent by the current Python
  session service.

When a configured sidecar binary is started, Tauri sets
`WORKTRACE_SIDECAR_HOST=127.0.0.1`, sets `WORKTRACE_SIDECAR_PORT`, suppresses
sidecar stdio, inherits the local process environment for DB path configuration,
and can stop the managed process. Missing or unhealthy sidecars still return
safe missing/unhealthy states instead of panicking.

Successful local builds create an ignored artifact like:

```txt
apps/desktop/src-tauri/target/release/bundle/nsis/WorkTrace AI_0.1.0_x64-setup.exe
```

## Local smoke result

On 2026-05-07, the following local packaging smoke passed on Windows:

```powershell
pnpm --dir apps/desktop package:sidecar
pnpm --dir apps/desktop package:windows
```

The sidecar build produced:

```txt
apps/desktop/src-tauri/binaries/worktrace-local-agent-x86_64-pc-windows-msvc.exe
```

The packaged sidecar executable was also started directly with
`WORKTRACE_SIDECAR_HOST=127.0.0.1`, `WORKTRACE_SIDECAR_PORT=8876`, and a
temporary `WORKTRACE_DB_PATH`; `/health` returned `status: ok` and schema
`003_ocr_results.sql`.

## Installer install/run QA result

On 2026-05-08, the following local installer QA passed on Windows:

```powershell
pnpm --dir apps/desktop package:sidecar
pnpm --dir apps/desktop package:windows
```

The generated NSIS installer was installed silently into a temporary repo-local
QA directory:

```txt
apps/desktop/src-tauri/target/installer-qa/WorkTraceAI
```

Installed files included:

```txt
uninstall.exe
worktrace-desktop.exe
worktrace-local-agent.exe
```

The installed `worktrace-desktop.exe` started and remained running for a
six-second launch smoke window. The installed `worktrace-local-agent.exe` also
started with `WORKTRACE_SIDECAR_HOST=127.0.0.1`, `WORKTRACE_SIDECAR_PORT=8891`,
and a temporary `WORKTRACE_DB_PATH`; `/health` returned `status: ok` and schema
`003_ocr_results.sql`.

The smoke result is recorded in
`docs/evidence/windows-installer-install-run-qa-2026-05-08.json`.

Uninstall/cleanup caveat:

- Silent uninstall exited `0`.
- Directly launching the PyInstaller sidecar left a child
  `worktrace-local-agent` process after the launcher process exited.
- While that child process was running, silent uninstall left
  `worktrace-local-agent.exe` behind.
- The QA cleanup stopped the remaining process and removed the temporary QA
  directory manually.

Follow-up fix:

- Tauri-managed sidecar stop now uses Windows process-tree cleanup
  (`taskkill /PID <pid> /T /F`) before the normal `Child::kill`/`wait` fallback.
- Regression evidence is recorded in
  `docs/evidence/sidecar-process-tree-cleanup-2026-05-08.json`.

## Release hardening decision

The release-hardening policy is recorded in `docs/release-hardening.md` and
`docs/evidence/release-hardening-decision-2026-05-26.json`.

Current decision:

- Do not buy a paid direct-distribution Windows code-signing certificate now.
- Do not implement Azure Artifact Signing / Trusted Signing now.
- Do not publish unsigned NSIS/MSI/EXE installers as public GitHub Release
  downloads.
- Future public Windows distribution should target Microsoft Store-compatible
  MSIX/AppX packaging, where Store signing applies only after successful Store
  submission/certification processing.
- Current NSIS output remains local/internal QA only.
- Signing credentials, Store credentials, private keys, PFX files, certificate
  passwords, vault credentials, signing-service tokens, or secret-bearing signing
  logs must never be committed or placed in runtime app configuration.
- Do not add placeholder signing fields to `tauri.conf.json`; the current app is
  intentionally unsigned.
- Do not enable the Tauri updater for Store/public distribution unless a later
  trusted-channel design explicitly requires and verifies it.
- Public channels should separate manual/local `dev` builds, source-only
  `alpha` milestones, future `store-beta`, and future `store-stable`.

Release candidates must record safe evidence for:

- package hash and Store/MSIX certification/signing status
- updater configuration and release channel
- installed file list
- desktop launch smoke
- sidecar `/health`
- sidecar process-tree stop and silent uninstall cleanup
- privacy check confirming no secrets, API keys, raw evidence, screenshot pixels,
  or private local paths are included

The 2026-05-26 release-hardening evidence is a policy/gate record, not a fresh
Store submission, MSIX/AppX package, or signed installer QA pass. A fresh
installed-app smoke is still required after any future Store packaging, updater,
sidecar packaging, or release-channel configuration change.

## Current limits

- The NSIS installer is not code-signed and is local/internal QA only.
- The installer does not bundle the Python sidecar yet unless the
  `package:sidecar` command has produced the target-triple sidecar executable
  before `package:windows` is run. The local Windows package build smoke has
  passed with that artifact present.
- The configured sidecar launch path exists, Packaging-ready sidecar binary
  lookup exists, and installer install/run QA passed locally, but this is not a
  release-ready bundled sidecar installer until signing, updater/release channel,
  and another installer QA pass confirms the managed process-tree cleanup in the
  packaged desktop path.
- The installer does not bundle local AI models.
- The app is still a desktop shell and preview UI.
- There is no updater configuration.
- There is no Store-compatible MSIX/AppX package, Store certification evidence,
  or production distribution process.

## Verification

Run this before presenting packaging status:

```powershell
pnpm --dir apps/desktop typecheck
pnpm --dir apps/desktop lint
pnpm --dir apps/desktop test
pnpm --dir apps/desktop build
pnpm --dir apps/desktop package:sidecar
pnpm --dir apps/desktop package:windows
```

If the packaging command fails because local NSIS/WebView2/build tools are
missing, report that as a packaging environment blocker. Do not publish a release
claim without a successful local packaging command and reviewed artifact.
