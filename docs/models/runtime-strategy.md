# Model Runtime Strategy

Status: accepted for active development on 2026-05-26.

WorkTrace must keep basic recording, raw timeline review, screenshot review,
privacy controls, deterministic exports, and deterministic evals working with no
AI model installed.

## Runtime Modes

| Mode | Provider/config | Product role | Network boundary |
| --- | --- | --- | --- |
| Local report runtime | `WORKTRACE_AI_PROVIDER=local_ollama` | Product-direction default for release builds and evidence-cited reports | Localhost only |
| Development hosted report runtime | `WORKTRACE_AI_PROVIDER=gemini_gemma_dev` plus `WORKTRACE_ENABLE_DEV_CLOUD_AI=true` | Current development default when local Gemma is too heavy | Sends minimal redacted report context to Google infrastructure |
| Local embeddings | `WORKTRACE_QWEN_EMBEDDING_BASE_URL=http://127.0.0.1:<port>` | Retrieval/grouping helper only | Localhost only |
| Local selected-frame vision | `WORKTRACE_QWEN_VL_BASE_URL=http://127.0.0.1:<port>` | Manual selected screenshot analysis only | Localhost only |
| Local audio transcription | `WORKTRACE_FASTER_WHISPER_MODEL_PATH=<local path>` | Explicit audio segment transcription only | Local filesystem/runtime only |
| Local OCR | optional PaddleOCR runtime | Selective screenshot OCR only | Local runtime only |

## Development Shortcut

For fast development on a laptop that cannot comfortably run the larger Gemma
report model locally, the sidecar defaults to the hosted Gemini API Gemma
provider for report generation. Keep the API key only in a private `.env` or
shell environment:

```powershell
WORKTRACE_AI_PROVIDER=gemini_gemma_dev
WORKTRACE_ENABLE_DEV_CLOUD_AI=true
GEMINI_API_KEY=<set only in private .env or shell>
WORKTRACE_GEMMA_PRIMARY_MODEL=gemma-4-31b-it
WORKTRACE_GEMMA_FALLBACK_MODEL=gemma-4-26b-a4b-it
```

Rules:

- The sidecar entrypoint loads a local `.env` file without printing values and
  does not override variables already set in the shell.
- Do not commit `.env`, API keys, prompt bodies, or smoke logs containing secrets.
- Do not send screenshots, raw artifacts, unrestricted OCR text, or raw event
  dumps to Gemini/Gemma by default.
- Send only the redacted evidence context produced by the development-cloud
  report policy.
- Label reports as `gemini_gemma_dev` and record requested/actual model metadata.
- Treat captured evidence as untrusted input and model output as untrusted output.
- Use the live smoke only with synthetic safe evidence:
  `pwsh -File scripts/validation/run-local-gates.ps1 -Scope GeminiSmoke`.

## Local Product Direction

For the real product path, the report model should run locally through a
user-managed localhost model service. The current local report model metadata is:

- default: Gemma 4 E2B-it Q4 via Ollama-style tag `gemma4:e2b`
- manual deep mode: Gemma 4 E4B-it Q4 via Ollama-style tag `gemma4:e4b`
- default context budget: 8192 tokens
- deep context cap: 16384 tokens until benchmark evidence justifies more
- no automatic model download or server startup

Runtime configuration:

```powershell
WORKTRACE_AI_PROVIDER=local_ollama
WORKTRACE_LOCAL_OLLAMA_BASE_URL=http://127.0.0.1:11434
```

`WORKTRACE_LOCAL_OLLAMA_BASE_URL` is optional and defaults to
`http://127.0.0.1:11434`. It must remain a localhost URL with no credentials,
paths, query strings, or fragments. The local agent checks `/api/tags` for the
configured default model before enabling report generation.

Qwen, faster-whisper, PaddleOCR, and Qwen-VL remain local-only optional runtimes.
They must not become cloud fallbacks because they process retrieval, audio,
OCR, or screenshot-derived evidence.

## Official Reference Notes

Google's Gemma 4 launch material describes 31B dense and 26B MoE variants for AI
Studio experimentation, while the DeepMind Gemma page also lists local/download
ecosystem routes such as Hugging Face, Ollama, Kaggle, LM Studio, and Docker.
The Gemini API reference documents standard/streaming API endpoints and SDK
references. Before any live smoke or release copy, re-check Google AI Studio or
the Gemini API model listing for the exact hosted model IDs configured here.

References:

- https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/
- https://deepmind.google/models/gemma/gemma-4/
- https://ai.google.dev/api

## Not Yet Implemented

- WorkTrace-managed model downloads.
- WorkTrace-managed local model server startup.
- Bundled Gemma, Qwen, PaddleOCR, or faster-whisper model weights.
- A 30-minute production local-model benchmark.
- Cloud fallback for local-only OCR, audio, embeddings, or selected-frame vision.
