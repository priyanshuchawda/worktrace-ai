# Qwen3 Embedding Local Runtime Smoke Plan

Goal: prove the existing localhost-only Qwen3 embedding adapter can be exercised
against a user-managed local runtime when configured, while normal recording and
tests remain independent of that runtime.

Scope:

- Add a skip-safe smoke command for `Qwen/Qwen3-Embedding-0.6B`.
- Read the local endpoint only from explicit configuration, not a remote default.
- Keep endpoint validation in the existing runtime adapter.
- Return public JSON with status, model name, sanitized endpoint host,
  embedding count, embedding dimension, and privacy leak count.
- Do not expose full input text, prompt text, model files, or embedding vectors in
  the public smoke result.
- Skip cleanly when no endpoint is configured.

Verification:

- Add tests first for unconfigured skip behavior and fake localhost-runtime pass
  behavior.
- Run the smoke command locally and record whether it passed or skipped.
- Run focused Qwen embedding tests plus full Python/shared/desktop/Rust gates
  before PR.
