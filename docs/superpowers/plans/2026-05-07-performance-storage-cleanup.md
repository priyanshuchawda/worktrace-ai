# Performance and Storage Cleanup

**Goal:** Bound screenshot storage growth, replace raw RGB screenshot artifacts with deterministic compressed PNG files, and document recording resource guardrails without adding OCR/model runtime work.

**Architecture:** Keep the Python sidecar as the source of truth for capture storage. The screenshot worker encodes downscaled frames to PNG with stdlib code, records compressed byte sizes in SQLite, prunes old screenshots under the safe session artifact root, and treats write/cleanup failures as non-fatal capture skips. Existing resource budget checks continue to prove CPU/RAM/storage/model-loaded policy without importing model runtimes.

## Step 1: Red Tests for Screenshot Storage Policy

Add tests for PNG storage paths, PNG file signatures, compressed byte-size metadata, and a deterministic format policy that documents why JPEG/WebP are not used yet.

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_screenshot_sampler.py tests/test_screenshot_capture_worker.py -q`

Expected: FAIL because artifacts still use `.rgb` raw bytes and no format policy exists.

## Step 2: Implement PNG Artifact Encoding

Add a small stdlib PNG encoder for RGB rows after downscaling. Store screenshots as `.png`, use compressed byte size in metadata, and keep content/visual hashes based on the original frame bytes.

## Step 3: Red Tests for Retention and Safe Cleanup

Add repository tests for pruning oldest screenshots by count and byte budget, deleting only files under the session artifact root, and tolerating already-missing files. Add worker coverage that write failures set a safe error and do not persist partial rows.

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_screenshot_retention.py tests/test_screenshot_capture_worker.py -q`

Expected: FAIL because retention pruning and safe write failure handling do not exist yet.

## Step 4: Implement Retention Cleanup

Add a `ScreenshotRetentionConfig` and `prune_screenshots_for_session` helper. Invoke it after successful screenshot persistence with conservative defaults. Cleanup must remove files first, then rows, and reject paths outside the artifact root.

## Step 5: Docs and Claim Discipline

Update README and packaging/architecture docs to state that screenshots are compressed PNG artifacts with retention cleanup, that JPEG/WebP are not implemented yet, that resource budget checks are deterministic, and that no model/OCR runtime is loaded during normal recording.

## Step 6: Verification

Run focused Python tests first, then the full gate from `docs/agent_continuous_execution.md`. Run `git diff --check` before commit.
