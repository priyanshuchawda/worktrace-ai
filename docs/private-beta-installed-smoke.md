# Installed-App Private Beta Smoke

Status: active local QA workflow for issue #161.

This smoke proves the installed Windows app path, not just unit tests. It is a
local-only validation workflow and must not publish, sign, upload, or distribute
the installer.

## Command

Build the sidecar and NSIS installer, install into ignored validation artifacts,
launch the desktop, health-check the installed sidecar, and silently uninstall:

```powershell
pwsh -File scripts/validation/run-installed-beta-smoke.ps1 -Build
```

Reuse an already-built installer without rebuilding:

```powershell
pwsh -File scripts/validation/run-installed-beta-smoke.ps1
```

The runner writes detailed logs and safe aggregate evidence to:

```text
artifacts/validation/<RUN_ID>/installed-beta-smoke.log
artifacts/validation/<RUN_ID>/installed-beta-smoke.json
```

The latest committed safe aggregate run result is:

```text
docs/evidence/private-beta-installed-smoke-2026-05-26.json
```

Console output stays compact:

```text
PASS | pwsh -File scripts/validation/run-installed-beta-smoke.ps1 -Build | <duration>s | log=artifacts\validation\<RUN_ID>\installed-beta-smoke.log
RUN_ID=<RUN_ID>
RESULT=PASS
```

## What It Checks

- optional sidecar packaging with `pnpm --dir apps/desktop package:sidecar`
- optional Windows NSIS packaging with `pnpm --dir apps/desktop package:windows`
- installer exists under `apps/desktop/src-tauri/target/release/bundle/nsis/`
- silent current-user install into ignored validation artifacts
- installed `worktrace-desktop.exe` starts and stays running during a short
  launch window
- installed `worktrace-local-agent.exe` starts on `127.0.0.1` and returns
  `/health` status `ok`
- local AI stays local-only and points at an unreachable localhost test endpoint
  during the smoke so no model download or hosted request can occur
- silent uninstall exits successfully unless `-SkipUninstall` is explicitly used

## Privacy And Cost Rules

- Do not call Gemini/Gemma live APIs from this smoke.
- Do not download Gemma, Qwen, PaddleOCR, faster-whisper, or other model assets.
- Do not include `.env`, API keys, prompt bodies, raw screenshots, OCR text, raw
  session artifacts, or private local paths in committed evidence.
- Do not spend money, sign binaries, configure updater endpoints, or publish
  release artifacts from this smoke.

## Remaining Manual Product Checks

This runner verifies installed process behavior. A human still needs to complete
the private-beta demo flow before external beta:

- complete first-run onboarding in the installed desktop UI
- start, pause, resume, and stop a recording
- review timeline, screenshots, OCR snippets, export preview, and deletion
- verify local AI report availability or missing-runtime setup state from the UI
- confirm folder-open behavior in Windows Explorer
