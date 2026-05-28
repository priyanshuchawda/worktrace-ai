# Issue #85 — AI Report UI + Generate Button

## Goal
Wire the desktop AI report panel through the existing typed React -> Tauri -> FastAPI boundary. The UI must not call model runtimes directly and must report honest unavailable/failure states when no local runtime is configured.

## Scope
- Add sidecar API contracts for local AI report status, generation, and cancellation.
- Add Rust sidecar bridge commands for those endpoints with localhost-only behavior and safe fallbacks.
- Add typed Tauri client functions and a desktop panel with generate, regenerate, cancel, status, model metadata, runtime duration, prompt/input hash, and evidence IDs.
- Use fakeable backend behavior in tests; no model downloads and no real Ollama/Gemma/Qwen dependency.
- Preserve deterministic export and session workflows without models.

## Out Of Scope
- Model download UI.
- Embeddings.
- OCR snippet surfacing.
- VLM/audio.
- Direct React model calls.
- Showing full prompts.

## Test Plan
1. Python API red tests:
   - Report status defaults to unavailable/not installed without runtime.
   - Generate returns safe unavailable state without runtime and does not mutate session data.
   - Injected fake report service returns a complete evidence-cited report with model metadata.
   - Invalid JSON/runtime failure maps to failed safely or retry-safe state without full prompt leakage.
   - Cancel endpoint returns cancelled state.
2. Rust bridge red tests:
   - Missing bridge returns safe unavailable report status/result.
   - Report status/generate/cancel call the expected localhost sidecar paths and redact response text.
   - Empty session IDs fail without side effects.
3. React red tests:
   - Model unavailable state disables the generate button.
   - Generate success displays report output, evidence IDs, model name, run time, and input hash.
   - Failed/invalid report state shows safe failure.
   - Cancel flow shows cancelled state.
   - Generate button is not usable while recording unless the session has stopped.

## Implementation Steps
1. Add API/service dataclasses and route response models for report status, generate, and cancel.
2. Add Rust result structs, bridge methods, Tauri commands, and command registration.
3. Extend `apps/desktop/src/lib/tauri-client.ts` with report types, fallbacks, and functions.
4. Replace the static AI-unavailable box in `ExportReviewPanel` with stateful local AI report controls.
5. Update README/model docs/claim-discipline tests to describe the UI as wired but unavailable without a configured runtime.
6. Run focused tests, then the full quality gate before PR.

## Safety Notes
- No prompt text is exposed in UI or logs.
- Evidence IDs remain mandatory for report claims.
- Model unavailable/failure states must not affect recording, timeline, deterministic export, or stored session rows/events.
- The first implementation remains manual/request-driven and must not load models while recording.
