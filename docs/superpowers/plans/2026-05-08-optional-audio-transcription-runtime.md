# Optional Audio Transcription Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, lazy faster-whisper audio transcription adapter and model metadata without enabling microphone capture or automatic model downloads.

**Architecture:** Keep opt-in policy enforcement in the existing `audio_transcription.py` layer: disabled/private policy returns before any engine call, transcripts are redacted, and evidence IDs are required. Add a focused `faster_whisper_runtime.py` adapter that implements the existing `TranscriptionEngine` protocol with a fakeable recognizer binding and no heavy import during normal recording or availability checks.

**Tech Stack:** Python 3.13 stdlib, existing audio transcription protocol, existing model availability/cache helpers, pytest, Markdown docs.

---

### Task 1: Red Tests for faster-whisper Runtime

**Files:**
- Create: `services/local-agent/tests/test_faster_whisper_runtime.py`
- Modify: `services/local-agent/tests/test_audio_embeddings.py`

- [x] **Step 1: Add failing tests for manifest/config metadata**

Test that the default metadata target is a laptop-safe faster-whisper `base` CPU int8 configuration, automatic downloads are disabled, and Distil-Whisper is manual-only/optional.

- [x] **Step 2: Add failing tests for fake recognizer parsing**

Test that the adapter writes the opt-in audio segment to a temporary file, calls a fake recognizer with documented faster-whisper-style `transcribe(path, beam_size=..., vad_filter=...)`, consumes the returned segment generator/list, and returns redacted text plus confidence metadata.

- [x] **Step 3: Add failing tests for safe failures**

Test unavailable recognizer binding, recognizer exceptions, empty segment text, invalid confidence metadata, and temporary-file cleanup.

- [x] **Step 4: Add failing tests for no heavy imports and no recording load**

Test that building manifests/availability/config does not import `faster_whisper`, `torch`, `transformers`, or `ctranslate2`.

- [x] **Step 5: Confirm RED**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_faster_whisper_runtime.py tests/test_audio_embeddings.py -q
```

Expected: fail on missing `worktrace_agent.capture.faster_whisper_runtime`.

### Task 2: Implement Lazy faster-whisper Adapter

**Files:**
- Create: `services/local-agent/src/worktrace_agent/capture/faster_whisper_runtime.py`

- [x] **Step 1: Add manifest/config dataclasses**

Create `FasterWhisperManifest`, `DEFAULT_FASTER_WHISPER_MANIFEST`, `DISTIL_WHISPER_MANIFEST`, and `FasterWhisperRuntimeConfig`.

- [x] **Step 2: Add fakeable recognizer binding**

Create a `WhisperRecognizer` protocol and a lazy `FasterWhisperRecognizerBinding` that imports `faster_whisper.WhisperModel` only inside `transcribe_file`.

- [x] **Step 3: Add transcription engine**

Implement `FasterWhisperTranscriptionEngine.transcribe(segment)` returning `TranscriptionEngineResult` from segment text and language probability metadata.

- [x] **Step 4: Add availability/cache builders**

Add `build_faster_whisper_availability_config(...)` and `build_faster_whisper_download_spec(...)` metadata helpers. These must not download, import, or load models.

- [x] **Step 5: Confirm GREEN**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_faster_whisper_runtime.py tests/test_audio_embeddings.py -q
```

### Task 3: Docs and State

**Files:**
- Modify: `README.md`
- Modify: `docs/model-routing.md`
- Modify: `docs/models/local_model_runtime.md`
- Create: `docs/models/audio.md`
- Modify: `docs/AGENT_STATE.md`

- [x] **Step 1: Document opt-in audio behavior**

State that audio transcription is off by default, requires explicit opt-in audio segments, and does not add always-on microphone capture.

- [x] **Step 2: Document faster-whisper model policy**

State that CPU int8 `base` is the laptop-safe metadata default, Distil-Whisper is optional/manual until benchmarked, and no model is auto-downloaded.

- [x] **Step 3: Document limitations**

State whether a real faster-whisper smoke was run. If not run, say the PR uses fake recognizer tests only.

### Task 4: Verification and PR

**Files:**
- All changed #99 files

- [x] **Step 1: Run focused model/audio tests**

Run:

```powershell
cd services/local-agent
uv run --python 3.13 pytest tests/test_faster_whisper_runtime.py tests/test_audio_embeddings.py tests/test_model_availability.py tests/test_model_cache.py tests/test_portfolio_claim_discipline.py -q
```

- [x] **Step 2: Run full quality gate**

Run the required Python, shared, desktop, and Rust gates from `docs/agent_continuous_execution.md`.

- [ ] **Step 3: Self-review and PR**

Run `git diff --check`, review staged diff, commit, push, open a PR with `Closes #99`, and merge only after checks are green.
