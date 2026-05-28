# Real Model Download Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit, manual-assisted model install/uninstall manager for local model files without auto-downloading, loading model runtimes, or touching recording paths.

**Architecture:** Extend the existing Python `model_cache` module. Keep the first install flow local-file based: the user or future UI supplies a downloaded file, WorkTrace checks disk space, copies to a temp file under the cache, verifies size/checksum, atomically renames into place, and can uninstall the exact cached file. No HTTP downloader or model runtime startup is added.

**Tech Stack:** Python 3.13 stdlib (`hashlib`, `os.replace`, `shutil`, `pathlib`), pytest, existing model cache helpers, Markdown docs.

---

### Task 1: Red Tests for Install Manager

**Files:**
- Modify: `services/local-agent/tests/test_model_cache.py`
- Read: `services/local-agent/src/worktrace_agent/ai/model_cache.py`
- Read: `.gitignore`

- [ ] **Step 1: Add state and manifest tests**

Add tests that expect:

```python
assert "verifying" in {status.value for status in ModelCacheStatus}

spec = ModelDownloadSpec(
    model_id="report/fake-report",
    filename="fake-report.gguf",
    expected_bytes=10,
    sha256=None,
    source_url="https://example.test/fake-report.gguf",
    manual_install_instructions="Download the model manually and select the file.",
)
```

The spec must validate `source_url` and manual instructions without requiring a download.

- [ ] **Step 2: Add failing local-file install tests**

Add tests for:

```python
install_model_from_local_file(
    spec,
    source_path=source_path,
    cache_root=tmp_path / "models",
    disk_space=FakeDiskSpace(free_bytes=1_000),
)
```

Expected behavior:

- insufficient disk returns `FAILED` and leaves target absent
- checksum mismatch returns `FAILED`, deletes temp file, and leaves existing target untouched
- successful install copies bytes into the cache path and returns `INSTALLED`

- [ ] **Step 3: Add failing uninstall and gitignore tests**

Add tests for:

- `uninstall_model(spec, cache_root=cache_root)` deletes only the exact cached model file and returns `NOT_INSTALLED`
- `.gitignore` contains model artifact protections such as `models/`, `*.gguf`, `*.safetensors`, `*.onnx`, `*.tflite`, `*.task`, and `*.bin`

- [ ] **Step 4: Verify RED**

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_model_cache.py -q`

Expected: FAIL for missing `VERIFYING`, missing spec fields, missing install/uninstall functions, and missing `.gitignore` patterns.

### Task 2: Implement Manual Install and Uninstall

**Files:**
- Modify: `services/local-agent/src/worktrace_agent/ai/model_cache.py`
- Modify: `.gitignore`

- [ ] **Step 1: Extend metadata types**

Add `VERIFYING = "verifying"` to `ModelCacheStatus`.

Extend `ModelDownloadSpec` with:

```python
source_url: str | None = None
manual_install_instructions: str | None = None
```

Validate non-empty optional instructions, http/https URLs, no URL credentials, relative model IDs, single filenames, positive sizes, and 64-character checksum strings.

- [ ] **Step 2: Add install function**

Implement:

```python
def install_model_from_local_file(
    spec: ModelDownloadSpec,
    *,
    source_path: Path,
    cache_root: Path,
    disk_space: DiskSpaceProvider,
    disk_safety_margin_bytes: int = DEFAULT_DISK_SAFETY_MARGIN_BYTES,
) -> ModelCacheState:
    ...
```

Rules:

- no network access
- fail if source is missing or not a file
- check disk space before copying
- copy to `target.with_suffix(target.suffix + ".tmp")`
- verify expected byte count and checksum before `os.replace`
- delete temp file on failed verification
- preserve existing target on checksum/size mismatch

- [ ] **Step 3: Add uninstall function**

Implement:

```python
def uninstall_model(
    spec: ModelDownloadSpec,
    *,
    cache_root: Path,
) -> ModelCacheState:
    ...
```

Rules:

- validate spec first
- delete only the exact model file from `_model_path`
- do not recursively delete directories
- return `NOT_INSTALLED` for already-missing model files
- fail safely if the cache path is a directory

- [ ] **Step 4: Verify GREEN**

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_model_cache.py -q`

Expected: PASS.

### Task 3: Docs and Agent State

**Files:**
- Modify: `README.md`
- Modify: `docs/models/model_download_policy.md`
- Modify: `docs/models/local_model_runtime.md`
- Modify: `docs/AGENT_STATE.md`

- [ ] **Step 1: Document honest behavior**

State:

- WorkTrace now has manual local-file install/uninstall helpers.
- It still does not auto-download models.
- It does not start/load model runtimes.
- Network downloader, resume support, and UI are not implemented.
- Install verifies disk space, expected size, and checksum when available.

- [ ] **Step 2: Run claim discipline**

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_portfolio_claim_discipline.py -q`

Expected: PASS.

### Task 4: Verification and PR

**Files:**
- All changed #89 files

- [ ] **Step 1: Run focused tests**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_model_cache.py tests/test_gemma_model_manifest.py tests/test_model_availability.py tests/test_portfolio_claim_discipline.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full quality gate**

Run the full Python, shared, desktop, and Rust gate from the issue prompt.

- [ ] **Step 3: Publish**

Run `git diff --check`, stage only #89 files, commit `feat: add manual model install manager`, push, open PR with `Closes #89`, and merge only after checks are green.
