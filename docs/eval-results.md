# Eval Results

See `../plan.md` and `evals.md` for the evaluation strategy.

## Reproduce

```powershell
cd services/local-agent
uv run --python 3.13 python scripts/evaluate_model.py
```

## Current aggregate

The current deterministic golden-session runner uses 20 compact local sessions.
The deterministic aggregate result from the latest local run is:

```txt
| aggregate | 1.00 | 1.00 | 1.00 | 0 | 0 | 104.00 | 0.017 | 18555 | yes |
```

Columns:

```txt
session_id
timeline_accuracy
blocker_precision
blocker_recall
hallucinated_event_count
privacy_leak_count
estimated_latency_ms
estimated_ram_mb
storage_bytes
passed
```

## AI report eval aggregate

The same command also prints deterministic AI report eval rows. The latest local run produced:

```txt
| mode | sessions | hallucinated_evidence_count | evidence_citation_valid | privacy_leak_count | generated_report_evidence_id_coverage | model_unavailable_fallback | summary_usefulness_proxy | blocker_precision_proxy | blocker_recall_proxy | estimated_latency_ms | estimated_memory_mb | model_call_count | model_called_during_recording | passed |
| deterministic_report | 20 | 0 | yes | 0 | 1.000 | no | 1.000 | 1.000 | 1.000 | 104.000 | 0.001 | 0 | no | yes |
| fake_gemma_e2b | 20 | 0 | yes | 0 | 1.000 | no | 1.000 | 1.000 | 1.000 | 364.000 | 3276.800 | 20 | no | yes |
| fake_gemma_e4b_deep | 20 | 0 | yes | 0 | 1.000 | no | 1.000 | 1.000 | 1.000 | 572.000 | 5120.000 | 20 | no | yes |
| model_unavailable | 20 | 0 | yes | 0 | 0.000 | yes | 0.500 | 1.000 | 1.000 | 20.000 | 0.000 | 0 | no | yes |
```

AI report eval columns:

```txt
mode
sessions
hallucinated_evidence_count
evidence_citation_valid
privacy_leak_count
generated_report_evidence_id_coverage
model_unavailable_fallback
summary_usefulness_proxy
blocker_precision_proxy
blocker_recall_proxy
estimated_latency_ms
estimated_memory_mb
model_call_count
model_called_during_recording
passed
```

## Interpretation

- `timeline_accuracy`, blocker precision, and blocker recall currently measure deterministic rules on compact local fixtures.
- `hallucinated_event_count = 0` means generated workflow evidence IDs are known event IDs in the fixture.
- `privacy_leak_count = 0` means the eval output did not include the known privacy test corpus.
- Latency, RAM, and storage values are deterministic estimates for regression tracking.
- AI report rows use deterministic and fake-runtime proxy outputs only; `fake_gemma_e2b` and `fake_gemma_e4b_deep` do not represent real Gemma runtime quality or speed.
- `model_called_during_recording = no` means the eval path did not mark any report model as called during a recording session.
- `model_unavailable` proves the unavailable fallback row is represented without calling a model.
- These numbers are not real Windows profiling and do not prove live recorder performance.

## 30-minute local recorder readiness benchmark

The production-readiness recorder profile is intentionally separate from AI
report quality and hosted-provider smoke tests. It starts the real local
recorder workers in a temporary workspace, samples aggregate CPU/RAM/storage
growth, counts privacy/report violations, and deletes temporary screenshot
artifacts by default.

```txt
command: cd services/local-agent; uv run --python 3.13 worktrace-laptop-readiness --profile production-30-minute --sample-interval-seconds 10 --output ..\..\docs\evidence\production-readiness-30-minute-2026-05-26.md
scope: local recorder pipeline only
cloud_request_count: 0
privacy_violation_count: 0
duration_minutes: 30.17 / 30.00 passed
average_cpu_percent: 2.96 / 15.00 passed
peak_ram_mb: 40.80 / 800.00 passed
db_growth_mb: 0.18 / 100.00 passed
screenshot_mb_per_hour: 15.46 / 250.00 passed
model_loaded_during_recording: 0.00 / 0.00 passed
```

The result is recorded in
`docs/evidence/production-readiness-30-minute-2026-05-26.md`. The older
`docs/evidence/laptop-readiness-2026-05-13.md` result remains as a short
5-minute smoke.

Interpretation:

- This is a 30-minute local recorder readiness benchmark, not a real model
  quality, hosted Gemini/Gemma, OCR, VLM, audio, installer, or public-release
  benchmark.
- The evidence file contains aggregate metrics only. It does not include raw
  active-window titles, screenshot pixels, raw OCR text, prompts, or API keys.
- Cloud inference benchmarks must stay separate from local recording pipeline
  benchmarks.

## Real Gemma E2B smoke

On 2026-05-13, a bounded tiny local smoke passed against user-installed Ollama
and the configured default Gemma E2B tag:

```txt
command: cd services/local-agent; uv run --python 3.13 python scripts/smoke_gemma_e2b_report.py
status: passed
ollama_version: ollama version is 0.23.2
model_name: gemma4:e2b
evidence_ids: evt_gemma_e2b_smoke_terminal
privacy_leak_count: 0
smoke_budget: timeout 90s, context 4096 tokens, output 256 tokens
```

The smoke result is recorded in
`docs/evidence/gemma-e2b-smoke-2026-05-13.json`. The older
`docs/evidence/gemma-e2b-smoke-2026-05-08.json` result is retained for
history.

Interpretation:

- This proves the existing localhost Ollama report adapter can produce a
  Pydantic-validated, evidence-cited report from the installed `gemma4:e2b`
  model on this Windows machine.
- This is not a quality benchmark, memory benchmark, latency benchmark, or CI
  requirement.
- Models are still not loaded during recording, and normal tests still use fake
  runtimes or skip-safe smoke behavior.

## PaddleOCR sample smoke

On 2026-05-08, the optional PaddleOCR sample smoke command was run on this
Windows machine:

```txt
command: cd services/local-agent; uv run --python 3.13 python scripts/smoke_paddleocr_sample.py
status: skipped
provider: paddleocr
reason: OCR runtime provider paddleocr is not installed. Recording continues without OCR.
privacy_leak_count: 0
```

The smoke result is recorded in
`docs/evidence/paddleocr-smoke-2026-05-08.json`.

Interpretation:

- This proves the PaddleOCR smoke path is callable, local-sample based, and
  skip-safe when the optional runtime is absent.
- This is not a PaddleOCR recognition, latency, memory, or installer proof.
- Normal recording and tests remain independent of PaddleOCR, and no model files
  are bundled or downloaded.

## Qwen3 embedding smoke

On 2026-05-08, the optional Qwen3 embedding smoke command was run on this
Windows machine:

```txt
command: cd services/local-agent; uv run --python 3.13 python scripts/smoke_qwen_embedding.py
status: skipped
model_name: Qwen/Qwen3-Embedding-0.6B
endpoint: not_configured
reason: WORKTRACE_QWEN_EMBEDDING_BASE_URL is not configured.
privacy_leak_count: 0
```

The smoke result is recorded in
`docs/evidence/qwen-embedding-smoke-2026-05-08.json`.

Interpretation:

- This proves the Qwen3 embedding smoke path is callable and skip-safe when no
  local endpoint is configured.
- This is not a Qwen3 embedding quality, latency, memory, vector-index, or model
  server proof.
- Normal recording and tests remain independent of Qwen embedding runtimes, and
  no model files are bundled or downloaded.

## Qwen3-VL selected-frame smoke

On 2026-05-08, the optional Qwen3-VL selected-frame smoke command was run on
this Windows machine:

```txt
command: cd services/local-agent; uv run --python 3.13 python scripts/smoke_qwen_vl_selected_frame.py
status: skipped
model_name: Qwen/Qwen3-VL-2B-Instruct
endpoint: not_configured
reason: WORKTRACE_QWEN_VL_BASE_URL is not configured.
privacy_leak_count: 0
```

The smoke result is recorded in
`docs/evidence/qwen-vl-smoke-2026-05-08.json`.

Interpretation:

- This proves the Qwen3-VL selected-frame smoke path is callable and skip-safe
  when no local endpoint is configured.
- This is not a Qwen3-VL image-understanding quality, latency, memory, model
  server, or UI deep-analysis proof.
- Normal recording and tests remain independent of Qwen3-VL runtimes, and no
  model files are bundled or downloaded.

## faster-whisper local-path smoke

On 2026-05-08, the optional faster-whisper local-path smoke command was run on
this Windows machine:

```txt
command: cd services/local-agent; uv run --python 3.13 python scripts/smoke_faster_whisper_local_path.py
status: skipped
model_name: base
model_path: not_configured
reason: WORKTRACE_FASTER_WHISPER_MODEL_PATH is not configured.
privacy_leak_count: 0
```

The smoke result is recorded in
`docs/evidence/faster-whisper-smoke-2026-05-08.json`.

Interpretation:

- This proves the faster-whisper smoke path is callable and skip-safe when no
  explicit local model path is configured.
- This is not a faster-whisper transcription quality, latency, memory, packaged
  model, microphone capture, or installer proof.
- Normal recording and tests remain independent of faster-whisper runtimes, and
  no model files are bundled or downloaded.
