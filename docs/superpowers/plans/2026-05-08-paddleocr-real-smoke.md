# PaddleOCR Real Sample Smoke Plan

Goal: prove the optional PaddleOCR path is safe to run against a local sample
screenshot when the runtime is installed, while keeping normal recording and CI
independent of PaddleOCR.

Scope:

- Add a skip-safe smoke command for the existing lazy PaddleOCR adapter.
- Use a tiny embedded local screenshot sample, not a downloaded image.
- Return public JSON with status, provider, evidence IDs, line count, and privacy
  leak count.
- Do not include image bytes, prompt text, model files, or remote runtime details
  in the public result.
- Skip cleanly when PaddleOCR is not installed.

Verification:

- Add tests first for missing-runtime skip behavior and fake-runtime pass
  behavior using the embedded screenshot sample.
- Run the smoke command locally and record whether it passed or skipped.
- Run focused OCR tests plus the full Python/shared/desktop/Rust gates before PR.
