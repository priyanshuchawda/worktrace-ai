# Model Routing

Initial Phase 0 placeholder. See `../plan.md` for the detailed AI and model-routing plan.

Current runtime strategy: see `models/runtime-strategy.md`.

MVP model policy:

- no model training in the MVP
- pretrained local models only when AI features are added
- normal recording must work without models installed
- AI report generation runs after session stop or manual request
- selective OCR guardrails may run only on high-value screenshots when explicitly invoked
- PaddleOCR, vision, audio transcription, and deep analysis are deferred as bundled runtimes

This project should never require a model for basic recording, raw timeline review, or local export.

Selective OCR policy:

- no continuous OCR
- no OCR model download in the current implementation
- no OCR package import during normal recording or availability checks
- private or blocked apps skip OCR
- likely secret-risk screens refuse OCR before extraction
- OCR snippets must be redacted and linked to screenshot evidence IDs
- optional real PaddleOCR adapter may run only after availability checks and explicit selective-worker scheduling
- selective OCR enforces a per-session job cap to prevent continuous OCR behavior
- OCR runtime failures must fail safely and skip the candidate without damaging session data

Local report runtime policy:

- report generation uses deterministic timeline evidence first and an LLM second
- localhost-only Ollama-style report runtime calls are adapter-level only
- desktop local AI report controls call only typed Tauri/FastAPI boundary commands
- local Ollama remains available through `WORKTRACE_AI_PROVIDER=local_ollama`
  and `WORKTRACE_LOCAL_OLLAMA_BASE_URL=http://127.0.0.1:11434`
- generated reports must show evidence IDs and model metadata without exposing the full prompt
- non-local model endpoints are rejected
- default report context budget is capped at 8192 tokens, with deep mode capped at 16384 tokens until benchmarks justify more
- prompts are capped before transport and oversized prompts fail safely
- model downloads, model server startup, embeddings, audio, and vision are out of scope for the first report runtime adapter
- `gemini_gemma_dev` is the current development default for report generation
  when a private `GEMINI_API_KEY` is configured, but it is not the shipped
  local-first product default

Embedding runtime policy:

- embeddings are retrieval/grouping helpers only, not source-of-truth evidence
- final report claims still require cited evidence IDs from timeline/session data
- Qwen3 embedding runtime uses localhost-only adapter calls with fakeable transport tests
- embedding payloads are redacted before transport
- no embedding runtime/model loading during normal recording
- no remote embedding endpoint or cloud vector database by default
- vector storage decision: SQLite vectors first for smaller local indexes, local file index later only when benchmarked scale requires it

Selected-frame vision policy:

- Qwen3-VL may run only on an explicitly selected screenshot/frame.
- Continuous VLM loops are forbidden.
- Likely secret-risk screens must refuse detailed extraction before any VLM call.
- Selected-frame analysis must cite screenshot or source event evidence IDs.
- Qwen3-VL-2B is the preferred laptop-safe metadata target.
- Qwen3-VL-4B is manual-only and unavailable until benchmarked safe on the target laptop.
- Qwen3-VL runtime calls must use localhost-only adapters with fakeable transports.
- No Qwen3-VL model download, bundled model, or real runtime startup is enabled by default.

Audio transcription policy:

- audio transcription is off by default and requires explicit opt-in audio segments
- always-on microphone capture is forbidden
- private mode suppresses transcription before any engine call
- transcripts must be redacted and linked to audio/source event evidence IDs
- faster-whisper runtime binding is lazy and must not import heavy packages during normal recording or availability checks
- default audio metadata target is faster-whisper `base` on CPU int8 for laptop safety
- Distil-Whisper is manual-only until benchmarked on the target Windows laptop
- no faster-whisper model download, bundled model, or real runtime startup is enabled by default

Default report model config:

- Default local report model: Gemma 4 E2B-it Q4.
- Ollama-style model tag: `gemma4:e2b`.
- Hugging Face model ID: `google/gemma-4-E2B-it`.
- Default context budget: 8192 tokens.
- First maximum tested budget target: 16384 tokens.
- Default max output tokens: 512.
- Default temperature: 0.2.
- Automatic downloads are disabled; this is manifest/config metadata only.
- Gemma 4 E2B documents a 128K context window, but WorkTrace must not use that full window by default on the target 16 GB Windows laptop.

Manual deep report model config:

- Manual deep local report model: Gemma 4 E4B-it Q4.
- Ollama-style model tag: `gemma4:e4b`.
- Hugging Face model ID: `google/gemma-4-E4B-it`.
- Deep mode is never the default and requires explicit user selection.
- Deep mode is disabled during recording.
- Deep mode falls back to E2B when memory pressure is high or E4B is unavailable.
- Deep mode context budget is capped at 16384 tokens until a Windows benchmark proves more is safe.
- Automatic downloads are disabled; this is manifest/config metadata only.

Development-only hosted report shortcut:

- Provider: `gemini_gemma_dev`.
- Current development defaults: `WORKTRACE_AI_PROVIDER=gemini_gemma_dev` and
  `WORKTRACE_ENABLE_DEV_CLOUD_AI=true`.
- Required secret: `GEMINI_API_KEY`, stored only in private `.env` or shell
  environment. The sidecar entrypoint loads local `.env` values without
  printing them and without overriding already-set shell variables.
- Primary hosted model: `gemma-4-31b-it`.
- Fallback hosted model: `gemma-4-26b-a4b-it`.
- Purpose: fast report development on machines that cannot run large Gemma
  locally.
- Boundary: redacted report context may leave the local machine; screenshots,
  raw artifacts, raw event dumps, and unrestricted OCR text are not sent by
  default.
- This shortcut does not apply to Qwen embeddings, Qwen-VL, PaddleOCR, or
  faster-whisper. Those remain local-only optional runtimes.
