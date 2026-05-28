# Qwen3-VL Selected-Frame Vision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local, selected-frame-only Qwen3-VL analyzer adapter and metadata manifests without enabling continuous vision or model downloads.

**Architecture:** Keep policy enforcement in existing `vision_analysis.py`: selected frame required, secret-risk refusal, cancellation, and evidence ID generation. Add a new `qwen_vl_runtime.py` adapter that implements the existing `VisionAnalyzer` protocol through a localhost-only OpenAI-style JSON transport. Keep model metadata explicit: Qwen3-VL-2B is the laptop-safe default, Qwen3-VL-4B is manual/unavailable until benchmarked.

**Tech Stack:** Python 3.13 stdlib, existing `VisionAnalyzer` protocol, fakeable JSON transport, existing model availability helpers, pytest, Markdown docs.

---

### Task 1: Red Tests for Qwen3-VL Runtime

**Files:**
- Create: `services/local-agent/tests/test_qwen_vl_runtime.py`
- Modify: `services/local-agent/tests/test_selected_frame_vision_analysis.py`

- [x] **Step 1: Add failing tests for localhost-only runtime config**

Test that `QwenVlSelectedFrameAnalyzer` rejects non-localhost base URLs, credentials, and path-prefixed URLs.

- [x] **Step 2: Add failing tests for Qwen3-VL manifests**

Test that the default manifest is `Qwen/Qwen3-VL-2B-Instruct`, is marked laptop safe, has automatic downloads disabled, and that the 4B manifest is manual-only and not the default.

- [x] **Step 3: Add failing tests for fake transport request shape and response parsing**

Test that selected-frame analysis sends one image data URL, redacted context text, model name, low temperature, and output token cap to `/v1/chat/completions`, then parses JSON content into `VisionAnalyzerResult`.

- [x] **Step 4: Add failing tests for safe failures and no heavy imports**

Test unavailable/malformed runtime responses, oversized images, missing model availability, and no import of `torch`, `transformers`, or `qwen_vl_utils`.

- [x] **Step 5: Confirm existing selected-frame policy still covers non-selected, cancellation, secret-risk, evidence ID, and no continuous loop**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_qwen_vl_runtime.py tests/test_selected_frame_vision_analysis.py -q
```

Expected: fail on missing `worktrace_agent.ai.qwen_vl_runtime`.

### Task 2: Implement Qwen3-VL Runtime Adapter

**Files:**
- Create: `services/local-agent/src/worktrace_agent/ai/qwen_vl_runtime.py`

- [x] **Step 1: Add manifest/config dataclasses**

Create `QwenVlManifest`, `DEFAULT_QWEN_VL_MANIFEST`, `QWEN_VL_4B_MANIFEST`, and `QwenVlRuntimeConfig`.

- [x] **Step 2: Add localhost-only transport**

Add `QwenVlJsonTransport`, `UrllibQwenVlTransport`, and strict base URL normalization matching existing report/embedding runtime policy.

- [x] **Step 3: Add selected-frame analyzer**

Implement `QwenVlSelectedFrameAnalyzer` with analyzer metadata and `analyze(request)` returning `VisionAnalyzerResult`.

- [x] **Step 4: Add safe request/response handling**

Base64 encode selected screenshot bytes, cap image bytes, redact text context, parse OpenAI-style `choices[0].message.content`, support JSON and plain text model content, and map all runtime errors to `QwenVlRuntimeError`.

- [x] **Step 5: Add availability builders**

Add `build_qwen_vl_runtime_config(...)` and `build_qwen_vl_availability_config(...)`. Availability uses local file metadata only and does not import or load VLM packages.

- [x] **Step 6: Run focused tests to confirm GREEN**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_qwen_vl_runtime.py tests/test_selected_frame_vision_analysis.py -q
```

### Task 3: Docs and State

**Files:**
- Modify: `README.md`
- Modify: `docs/model-routing.md`
- Modify: `docs/models/qwen.md`
- Modify: `docs/models/local_model_runtime.md`
- Modify: `docs/AGENT_STATE.md`

- [x] **Step 1: Document selected-frame-only Qwen3-VL behavior**

State that Qwen3-VL runs only for manually selected screenshots through the existing guardrails.

- [x] **Step 2: Document model policy**

State that Qwen3-VL-2B is the preferred laptop-safe target, 4B is manual/unavailable until benchmarked, and no models are downloaded or bundled.

- [x] **Step 3: Document limitations**

State that this PR is an adapter/fake-transport slice, with no real Qwen3-VL smoke, desktop UI, continuous VLM, or secret extraction.

### Task 4: Verification and PR

**Files:**
- All changed #97 files

- [x] **Step 1: Run focused model/vision tests**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_qwen_vl_runtime.py tests/test_selected_frame_vision_analysis.py tests/test_model_availability.py tests/test_portfolio_claim_discipline.py -q
```

- [x] **Step 2: Run full quality gate**

Run the required Python, shared, desktop, and Rust gates from `docs/agent_continuous_execution.md`.

- [ ] **Step 3: Self-review and PR**

Run `git diff --check`, review staged diff, commit, push, open a PR with `Closes #97`, and merge only after checks are green.
