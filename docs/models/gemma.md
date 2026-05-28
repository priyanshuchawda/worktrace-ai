# Gemma Model Notes

Gemma-style local instruct models are candidates for future evidence-cited report generation.

Current status:

- Not installed by WorkTrace.
- Not downloaded by WorkTrace.
- Not loaded during recording.
- Not used for OCR.
- Default report model config for user-managed local runtimes: Gemma 4 E2B-it Q4.
- Ollama-style tag: `gemma4:e2b`.
- Hugging Face model ID: `google/gemma-4-E2B-it`.
- Quantization assumption for the default config: `Q4_0`.
- Default report context budget: 8192 tokens.
- First maximum tested budget target: 16384 tokens.
- Manual deep-mode config: Gemma 4 E4B-it Q4.
- Deep-mode Ollama-style tag: `gemma4:e4b`.
- Deep-mode Hugging Face model ID: `google/gemma-4-E4B-it`.
- Deep-mode context budget: 16384 tokens.
- Deep mode is manual-only, never the default, disabled during recording, and falls back to E2B when E4B is unavailable or memory pressure is high.
- Default output cap: 512 tokens.
- Default temperature: 0.2.
- Automatic downloads are disabled.
- Gemma 4 E2B/E4B may expose large context windows, but WorkTrace report runtime defaults stay capped at 8192 tokens and deep mode stays capped at 16384 tokens until local benchmarks prove more is safe.

## Development-only hosted Gemma

`gemini_gemma_dev` exists only to speed development when the local laptop cannot
comfortably run larger Gemma report models. It is the current development
default for reports when `GEMINI_API_KEY` is configured, but it is report-only
and must never be the release default.

Development hosted config:

- Provider: `gemini_gemma_dev`.
- Enable flag: `WORKTRACE_ENABLE_DEV_CLOUD_AI=true` by development default.
- API key source: `GEMINI_API_KEY` in private `.env` or shell environment only.
- Primary hosted model: `gemma-4-31b-it`.
- Fallback hosted model: `gemma-4-26b-a4b-it`.

Hosted Gemma sends minimal redacted report context to Google infrastructure. It
must not receive screenshots, raw artifacts, unrestricted OCR text, raw event
dumps, or unredacted terminal/window/file-path evidence by default.

## Real local smoke

On 2026-05-08, the default Gemma E2B tag was smoke-tested through a
user-managed local Ollama runtime:

- Ollama version: `0.23.1`.
- Installed model tag used: `gemma4:e2b`.
- Command: `uv run --python 3.13 python scripts/smoke_gemma_e2b_report.py`.
- Result: passed.
- Evidence ID returned by the report: `evt_gemma_e2b_smoke_terminal`.
- Privacy leak count: `0`.
- Recorded artifact: `docs/evidence/gemma-e2b-smoke-2026-05-08.json`.

This is a tiny local runtime smoke only. It does not mean WorkTrace bundles,
downloads, starts, or requires Gemma, and it does not prove real report quality,
latency, memory use, or long-session behavior.

Future report runtime work must document model size, quantization, disk path, checksum strategy where practical, latency, RAM use, and failure states before enabling any WorkTrace-managed download or inference path.
