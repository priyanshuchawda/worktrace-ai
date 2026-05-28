# Qwen3-VL Selected-Frame Local Runtime Smoke Plan

Goal: prove the existing localhost-only Qwen3-VL selected-frame adapter can be
exercised against a user-managed local runtime when configured, while normal
recording and tests remain independent of that runtime.

Scope:

- Add a skip-safe smoke command for `Qwen/Qwen3-VL-2B-Instruct`.
- Read the local endpoint only from explicit configuration, not a remote default.
- Keep endpoint validation in the existing runtime adapter.
- Use a tiny embedded selected screenshot sample with a source evidence ID.
- Return public JSON with status, model name, sanitized endpoint host, evidence
  IDs, title/description, and privacy leak count.
- Do not expose full prompt text, image bytes, data URLs, model files, or private
  screenshot contents in the public smoke result.
- Skip cleanly when no endpoint is configured.

Verification:

- Add tests first for unconfigured skip behavior and fake localhost-runtime pass
  behavior.
- Run the smoke command locally and record whether it passed or skipped.
- Run focused Qwen3-VL tests plus full Python/shared/desktop/Rust gates before
  PR.
