# faster-whisper Local-Path Runtime Smoke Plan

Goal: prove the existing optional faster-whisper adapter can be exercised
against an explicit local model path when configured, while normal recording and
tests remain independent of that runtime.

Scope:

- Add a skip-safe smoke command for the default faster-whisper `base` CPU int8
  metadata target.
- Read the local model path only from explicit configuration, not a model-size
  string that can trigger an automatic download.
- Keep the existing real binding rule that `faster_whisper` is imported only
  after an explicit existing local model path is present.
- Return public JSON with status, model name, sanitized model-path state,
  evidence IDs, transcript character count, language, and privacy leak count.
- Do not expose raw audio bytes, transcript text, model files, or local absolute
  paths in the public smoke result.
- Skip cleanly when no model path, optional package, or sample audio path is
  configured.

Verification:

- Add tests first for unconfigured skip behavior and fake local-path runtime pass
  behavior.
- Run the smoke command locally and record whether it passed or skipped.
- Run focused faster-whisper/audio tests plus full Python/shared/desktop/Rust
  gates before PR.
