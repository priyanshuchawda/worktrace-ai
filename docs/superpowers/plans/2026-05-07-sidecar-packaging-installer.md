# Sidecar Packaging Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested, packaging-ready Windows sidecar executable path so the desktop can launch the Python local agent from a bundled artifact without a manual `WORKTRACE_SIDECAR_URL`.

**Architecture:** Keep Rust as the trusted launcher and localhost policy boundary. Keep Python as the FastAPI app owner, adding only a thin executable entrypoint and deterministic path helpers; do not add OCR/model/runtime downloads.

**Tech Stack:** Tauri v2, Rust, React/TypeScript/Vitest, Python 3.13, FastAPI, uv, PyInstaller-ready packaging script.

---

## Understanding

Issue #75 asks for Windows installer sidecar packaging, local-only sidecar launch, deterministic DB/artifact defaults, safe missing states, and honest README limitations. The current repo already has manual `WORKTRACE_SIDECAR_BIN` and `WORKTRACE_SIDECAR_PORT` support, safe missing states, and NSIS packaging, but it does not yet expose a Python executable entrypoint or configure Tauri `bundle.externalBin`.

## Relevant Files

- Modify: `apps/desktop/src-tauri/src/services/sidecar.rs`
- Modify: `apps/desktop/src-tauri/tauri.conf.json`
- Test: `apps/desktop/src-tauri/tests/sidecar_service.rs`
- Modify: `services/local-agent/pyproject.toml`
- Create: `services/local-agent/src/worktrace_agent/__main__.py`
- Test: `services/local-agent/tests/test_packaging_entrypoint.py`
- Modify: `README.md`
- Modify: `docs/packaging.md`
- Modify: `docs/AGENT_STATE.md`

## Current Behavior

- `WORKTRACE_SIDECAR_URL` overrides the base URL if it is localhost.
- `WORKTRACE_SIDECAR_PORT` builds `http://127.0.0.1:<port>`.
- `WORKTRACE_SIDECAR_BIN` can start a configured binary.
- A private bundled lookup checks `sidecars/worktrace-local-agent.exe` or `worktrace-local-agent.exe` next to the app executable.
- Missing binary returns a safe `missing` health state.
- Python app defaults the DB to `~/.worktrace/db/worktrace.sqlite`; artifacts default under the DB parent.
- Tauri config has no `externalBin`.
- Python package has no `python -m worktrace_agent` entrypoint.

## Plan

- [x] **Step 1: Reconcile branch and state**

Run:

```powershell
git status -sb
git branch --show-current
git fetch origin
gh issue list --state open
gh pr list --state open
gh pr list --state closed --limit 8
```

Expected: issue #75 open, no open PRs, #74 merged, branch `feat/75-sidecar-packaging-installer`.

- [ ] **Step 2: Add Rust red tests**

Add tests to `apps/desktop/src-tauri/tests/sidecar_service.rs` that call new testable helpers:

```rust
#[test]
fn sidecar_binary_lookup_prefers_configured_worktrace_sidecar_bin() {
    let temp_root = unique_temp_dir("configured_bin");
    let configured = touch_file(&temp_root.join("configured-sidecar.exe"));
    let bundled = touch_file(&temp_root.join("sidecars").join("worktrace-local-agent.exe"));

    let found = resolve_sidecar_binary_for_test(Some(configured.clone()), temp_root.clone());

    assert_eq!(found, Some(configured));
    assert!(bundled.is_file());
}

#[test]
fn sidecar_binary_lookup_finds_bundled_worktrace_local_agent_exe() {
    let temp_root = unique_temp_dir("bundled_bin");
    let bundled = touch_file(&temp_root.join("sidecars").join("worktrace-local-agent.exe"));

    let found = resolve_sidecar_binary_for_test(None, temp_root);

    assert_eq!(found, Some(bundled));
}

#[test]
fn start_sidecar_launch_environment_is_local_only_and_deterministic() {
    let env = sidecar_launch_environment_for_test(4567);

    assert!(env.contains(&("WORKTRACE_SIDECAR_HOST".to_string(), "127.0.0.1".to_string())));
    assert!(env.contains(&("WORKTRACE_SIDECAR_PORT".to_string(), "4567".to_string())));
}
```

Run:

```powershell
cd apps/desktop/src-tauri
cargo test sidecar_binary_lookup sidecar_launch_environment --test sidecar_service
```

Expected: fail because the helper functions do not exist yet.

- [ ] **Step 3: Implement Rust helper functions**

Add small public helper functions in `sidecar.rs` and route existing private lookup/start code through them:

```rust
pub fn sidecar_base_url_from_port(port: u16) -> String {
    format!("http://127.0.0.1:{port}")
}

pub fn resolve_sidecar_binary(configured_path: Option<PathBuf>, app_dir: PathBuf) -> Option<PathBuf> {
    if let Some(path) = configured_path {
        if path.is_file() {
            return Some(path);
        }
    }
    bundled_sidecar_binary_in_dir(app_dir)
}

pub fn sidecar_launch_environment(port: u16) -> [(String, String); 2] {
    [
        ("WORKTRACE_SIDECAR_HOST".to_string(), "127.0.0.1".to_string()),
        ("WORKTRACE_SIDECAR_PORT".to_string(), port.to_string()),
    ]
}
```

Run:

```powershell
cd apps/desktop/src-tauri
cargo test sidecar_binary_lookup sidecar_launch_environment --test sidecar_service
```

Expected: pass.

- [ ] **Step 4: Add Python red tests**

Add `services/local-agent/tests/test_packaging_entrypoint.py`:

```python
from pathlib import Path

from worktrace_agent.api.app import _default_artifact_root, _default_db_path


def test_python_module_entrypoint_imports_cleanly() -> None:
    import worktrace_agent.__main__ as entrypoint

    assert callable(entrypoint.main)


def test_default_db_path_respects_configured_env(monkeypatch, tmp_path: Path) -> None:
    configured = tmp_path / "db" / "worktrace.sqlite"
    monkeypatch.setenv("WORKTRACE_DB_PATH", str(configured))

    assert _default_db_path() == configured


def test_default_artifact_root_is_local_and_deterministic(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WORKTRACE_DB_PATH", str(tmp_path / "db" / "worktrace.sqlite"))

    assert _default_artifact_root("sess_packaged_001") == tmp_path / "sessions" / "sess_packaged_001"
```

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_packaging_entrypoint.py -q
```

Expected: fail because `__main__.py` and `_default_artifact_root` do not exist yet.

- [ ] **Step 5: Implement Python packaging entrypoint**

Add `services/local-agent/src/worktrace_agent/__main__.py` with a thin `main()` that reads:

```python
host = os.environ.get("WORKTRACE_SIDECAR_HOST", "127.0.0.1")
port = int(os.environ.get("WORKTRACE_SIDECAR_PORT", "8765"))
if host not in {"127.0.0.1", "localhost"}:
    raise SystemExit("WORKTRACE_SIDECAR_HOST must be 127.0.0.1 or localhost")
uvicorn.run("worktrace_agent.api.app:app", host=host, port=port, log_level="info")
```

Add `uvicorn` runtime dependency and a `worktrace-local-agent = "worktrace_agent.__main__:main"` console script in `pyproject.toml`.

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_packaging_entrypoint.py -q
```

Expected: pass.

- [ ] **Step 6: Configure Tauri external binary artifact**

Update `apps/desktop/src-tauri/tauri.conf.json`:

```json
"externalBin": [
  "binaries/worktrace-local-agent"
]
```

Document expected Windows build output:

```txt
apps/desktop/src-tauri/binaries/worktrace-local-agent-x86_64-pc-windows-msvc.exe
```

Do not claim the installer bundles the sidecar unless the artifact exists and package smoke passes.

- [ ] **Step 7: Update docs and state**

Update README and `docs/packaging.md` to say:

- configured sidecar launch path exists
- packaging-ready sidecar binary lookup exists
- Tauri external binary path is configured
- sidecar bundling into the installer requires producing the target-triple executable first
- Windows installer smoke status is recorded under Testing/Not Run
- no OCR/model runtime/model downloads are included

- [ ] **Step 8: Run full verification**

Run the required quality gate from the issue. If `pnpm --dir apps/desktop package:windows` cannot run because the sidecar artifact is absent or local packaging tooling blocks it, document the exact reason in the PR `Not Run` section.

## Risks

- Tauri `externalBin` requires target-triple-suffixed binaries. A config-only path is not a real bundled sidecar unless the artifact exists before `tauri build`.
- Adding PyInstaller now may increase issue size. Prefer a documented executable entrypoint plus packaging-ready artifact location unless local build time remains small.
- Sidecar host/port must remain local-only; reject non-localhost URL/host configuration.
- README must avoid production-ready, signed, OCR/model, or distribution claims.
