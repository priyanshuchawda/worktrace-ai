# Model Download Cache Manager

**Goal:** Add a safe local model cache policy layer with deterministic paths, manifest states, disk-space checks, and checksum validation without downloading or loading model runtimes.

**Architecture:** Keep model cache behavior in the Python sidecar AI layer. The cache manager is metadata-only: it can resolve local cache paths, inspect existing files, validate hashes, and decide whether a future download would be allowed. It must not perform network downloads, import heavy model packages, or mutate session data.

## Step 1: Red Tests for Cache Path and States

Add tests for required cache statuses, `%LOCALAPPDATA%/WorkTrace/models` default path, `WORKTRACE_MODEL_CACHE` override, and no heavy model imports.

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_model_cache.py -q`

Expected: FAIL because no model cache module exists.

## Step 2: Red Tests for Disk and Hash Decisions

Add fake disk-space provider tests for not-installed/enough-space, insufficient-space failed state, installed matching checksum, and installed checksum mismatch.

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_model_cache.py -q`

Expected: FAIL until cache inspection and disk checks exist.

## Step 3: Implement Metadata-Only Cache Manager

Add typed dataclasses/enums for model specs and cache decisions. Use path helpers and `hashlib` only. Do not add download code, HTTP clients, model dependencies, or runtime imports.

## Step 4: Docs and Claim Discipline

Update README and model docs to say cache manager decisions exist, no automatic downloads exist, no model runtime is loaded, and no model files are committed.

## Step 5: Verification

Run focused Python tests, then the full gate from `docs/agent_continuous_execution.md`. Run `git diff --check` before commit.
