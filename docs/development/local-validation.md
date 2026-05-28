# Local Validation

Use the local validation runner during active development before opening PRs.
GitHub Actions provide deterministic repository gates on pull requests and
pushes to `main`, while local gates keep iteration fast and store detailed
command output under `artifacts/validation/<RUN_ID>/`.

```powershell
pwsh -File scripts/validation/run-local-gates.ps1 -Scope Python
pwsh -File scripts/validation/run-local-gates.ps1 -Scope Desktop
pwsh -File scripts/validation/run-local-gates.ps1 -Scope Shared
pwsh -File scripts/validation/run-local-gates.ps1 -Scope Rust
pwsh -File scripts/validation/run-local-gates.ps1 -Scope All
```

`All` runs Shared, Desktop, and Python gates. Rust/Tauri checks are explicit
because this repository's Tauri build expects a packaged sidecar binary under
`apps/desktop/src-tauri/binaries/`; run `-Scope Rust` when Rust/Tauri code is
touched and the sidecar precondition is satisfied.

Packaging checks are intentionally separate because they are slower and only
needed for packaging changes:

```powershell
pwsh -File scripts/validation/run-local-gates.ps1 -Scope Packaging
```

Installed-app private beta smoke is even more explicit because it installs and
launches local build artifacts:

```powershell
pwsh -File scripts/validation/run-installed-beta-smoke.ps1 -Build
```

This smoke writes safe aggregate evidence under `artifacts/validation/<RUN_ID>/`
and is documented in `docs/private-beta-installed-smoke.md`. It does not sign,
publish, upload, call Gemini, or download model assets.

Gemini/Gemma live smoke is separate and explicit:

```powershell
pwsh -File scripts/validation/run-local-gates.ps1 -Scope GeminiSmoke
```

This scope runs the development-only Gemini/Gemma smoke script with synthetic
safe evidence. The development defaults select `gemini_gemma_dev` and enable
development cloud reports, but the smoke still skips unless `GEMINI_API_KEY` is
configured in a private `.env` or shell environment.
Ordinary tests must use fake clients and must not make live external requests.

The runner redacts common secret patterns before printing failure tails. Full
logs remain local and ignored by git.

The workspace explicitly allows the `esbuild` postinstall build used by the
desktop/Vite/Vitest toolchain. Without that pnpm 11 approval, local TypeScript
and desktop gates fail before project code runs.

## GitHub CI

`.github/workflows/ci.yml` runs secret-free deterministic gates:

- shared TypeScript typecheck and tests
- desktop TypeScript typecheck, lint, tests, and build
- Python sidecar Ruff format/check, Pyright, and Pytest on Windows to match
  the product's Windows-first runtime assumptions
- Rust/Tauri fmt, clippy, and tests after the sidecar binary precondition is
  built with `pnpm --dir apps/desktop package:sidecar`

CI sets `WORKTRACE_ENABLE_DEV_CLOUD_AI=false` and does not require Gemini,
Ollama, downloaded models, signing credentials, screenshots, or private session
evidence.

`.github/workflows/packaging-smoke.yml` is manual-only. It may build unsigned
NSIS artifacts for internal smoke validation, but it does not upload artifacts
or publish releases. The release artifact guard is expected to reject those
unsigned packaging outputs for alpha release distribution.
