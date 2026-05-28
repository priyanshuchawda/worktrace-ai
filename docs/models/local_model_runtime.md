# Local Model Runtime Policy

See `runtime-strategy.md` for the current product-vs-development runtime
decision. This file records lower-level runtime guardrails.

Local model runtimes are optional workers, not dependencies for the recorder.

Rules:

- Normal recording must not load OCR, LLM, embedding, audio, or VLM models.
- Heavy runtimes must be lazy and explicit.
- Runtime availability checks should avoid importing heavy modules where practical.
- Runtime errors must be categorized safely and redacted before reaching the UI or logs.
- Cancellation and timeout behavior must be added before long-running inference becomes user-facing.
- AI report generation must run only after stop or manual request.

For #83, a localhost-only report runtime adapter may call a user-managed local model service through an injectable transport. WorkTrace still does not bundle, download, start, or manage model files or model servers in this issue.

For #85, the desktop local AI report panel is wired through React, Tauri, and FastAPI boundary commands for status, generate, and cancel. The default service remains unavailable without a configured local runtime. The UI must not show full prompts and must not fake success.

For #87, the default report model config is Gemma 4 E2B-it Q4. WorkTrace maps it to `gemma4:e2b` for Ollama-style localhost runtimes and records `google/gemma-4-E2B-it` as the Hugging Face source ID. This is manifest/config metadata only: no model is downloaded, loaded, started, or smoke-tested by WorkTrace.

For #89, WorkTrace can manually install a user-supplied local model file into the cache after disk-space, size, and checksum checks, and can uninstall the exact cached file. This does not perform network downloads, start model servers, import heavy runtime packages, or load models during recording.

For #91, WorkTrace adds a localhost-only Qwen3 embedding runtime adapter for retrieval/grouping helpers. The adapter redacts text before transport, validates response dimensions, and can be fully tested with fake transport. It still does not run during recording, does not auto-download models, and does not allow embeddings to bypass evidence-ID claim discipline.

For #93, WorkTrace adds an optional real PaddleOCR adapter path behind selective-worker guardrails. Runtime binding is lazy, unavailable runtimes degrade safely, and per-session OCR jobs are capped so OCR cannot become continuous capture.

For #95, WorkTrace adds manual-only Gemma 4 E4B-it Q4 deep-mode metadata and selection guardrails. E4B is never the default, is disabled during recording, falls back to E2B when memory pressure is high or E4B is unavailable, and remains capped at 16384 context tokens until benchmark evidence justifies more.

For #97, WorkTrace adds a localhost-only Qwen3-VL selected-frame adapter for user-managed local VLM services. Qwen3-VL-2B is the laptop-safe metadata default, Qwen3-VL-4B is manual-only until benchmarked, and VLM analysis remains selected-frame only with no model download, bundled weights, or continuous loop.

For #99, WorkTrace adds an optional faster-whisper transcription adapter behind explicit audio opt-in. The adapter uses lazy runtime binding, keeps audio off by default, suppresses transcription in private mode, defaults metadata to CPU int8 `base`, and leaves Distil-Whisper manual-only until benchmarked. No model is downloaded, bundled, loaded during recording, or smoke-tested by default.

For #103, a tiny real Gemma E2B smoke passed against user-installed Ollama
`0.23.1` with installed tag `gemma4:e2b`. The smoke used the existing
localhost-only Ollama report adapter and produced an evidence-cited report with
privacy leak count `0`. This is not a benchmark, not a CI requirement, and not a
model download/startup feature.

#83 runtime budgets:

- default mode context budget: 8192 tokens
- deep mode context budget limit: 16384 tokens
- default max output tokens: 512
- default temperature: 0.2
- prompts over the configured character cap fail safely before any transport call

The Gemma/Qwen docs mention larger context windows, but WorkTrace must not use full long-context windows by default on the target 16 GB Windows laptop.

For #185, `gemini_gemma_dev` is the development-default hosted report provider
when a private `GEMINI_API_KEY` is configured. It is not a replacement for local
product runtime design, does not apply to Qwen, PaddleOCR, faster-whisper, or
Qwen-VL, and must still pass the development-cloud redaction policy before any
network request.
