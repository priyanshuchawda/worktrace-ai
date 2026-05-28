# Selective OCR Runtime

**Goal:** Turn the existing fakeable OCR worker foundation into a guarded selective OCR runtime path that can safely remain disabled/unavailable when no OCR package is installed, while enforcing privacy, secret-risk refusal, and evidence-linked redacted storage.

**Architecture:** Keep OCR in the Python sidecar behind injectable engine/runtime contracts. Do not add model downloads. Do not load PaddleOCR or any heavy module during normal recording. Add runtime availability checks that use lightweight import discovery, and keep real OCR execution optional. The worker must reject private/blocked apps and secret-risk screens before calling an OCR engine.

## Step 1: Red Tests for Privacy and Secret-Risk Guards

Add tests that private mode and blocked apps skip OCR without engine calls, secret-risk screens refuse OCR without engine calls, empty image bytes are rejected, and OCR evidence IDs fall back to the screenshot ID when no source event exists.

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_selective_ocr_worker.py -q`

Expected: FAIL because the current worker has no privacy policy, secret-risk status, or image validation.

## Step 2: Implement Worker Guardrails

Add skip/refusal states, privacy policy injection, request validation, and safe evidence ID metadata. Keep output redacted and stored through the existing OCR repository.

## Step 3: Red Tests for Optional Runtime Availability

Add tests for disabled/unavailable OCR runtime states, no heavy module import during availability checks, and an optional PaddleOCR runtime factory that returns unavailable safely if the package is absent.

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_ocr_runtime.py -q`

Expected: FAIL because no OCR runtime availability module exists.

## Step 4: Implement Optional OCR Runtime

Add a small runtime module with disabled/unavailable/ready states. Use `importlib.util.find_spec` for availability checks. Do not add PaddleOCR dependencies or model downloads in this issue.

## Step 5: Docs and Claim Discipline

Update README, model-routing, and model docs to say selective OCR runtime guardrails exist, real PaddleOCR is optional/unavailable unless installed, continuous OCR is forbidden, and model downloads are still not implemented.

## Step 6: Verification

Run focused Python tests first, then the full gate from `docs/agent_continuous_execution.md`. Run `git diff --check` before commit.
