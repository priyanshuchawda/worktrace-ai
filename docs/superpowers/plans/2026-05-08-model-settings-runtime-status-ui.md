# Desktop Model Settings Runtime Status UI Plan

Goal: make local AI runtime setup visible and safe in the desktop app without
starting servers, downloading model files, or exposing prompts.

Scope:

- Add a desktop Model Settings panel.
- Show the configured local Ollama endpoint and reject non-localhost URLs.
- Show Gemma E2B as the default report model and Gemma E4B as manual deep mode.
- Show a clear generate-unavailable reason when the runtime or endpoint is not
  usable.
- Keep full prompt text out of the UI.
- Keep downloads and model server startup out of scope.

Verification:

- Add React tests for model settings rendering, localhost validation, remote
  endpoint rejection, disabled report generation, and no prompt/download UI.
- Run desktop typecheck, lint, tests, and build before PR.
- Run Python/shared/Rust gates because the release proof path remains
  cross-boundary even when this issue is desktop-only.
