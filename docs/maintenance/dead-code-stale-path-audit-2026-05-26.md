# Dead Code and Stale Path Audit - 2026-05-26

Parent issue: #131.

## Scope

This audit looked for dead code, stale documentation, duplicate runtime concepts,
and obsolete experimental paths after the Gemini development provider, privacy
center persistence, screenshot preview/OCR snippets, and desktop refactor work.

## Fixed in this PR

- `scripts/validation/run-local-gates.ps1` had a stale `GeminiSmoke`
  placeholder even though `worktrace_agent.scripts.smoke_gemini_gemma_dev_report`
  exists. The scope now runs the real skip-safe smoke script and remains explicit.
- `docs/development/local-validation.md` still described Gemini live smoke as a
  placeholder. It now documents the opt-in smoke command and required environment
  controls.
- `README.md` still described `gemini_gemma_dev` as future, claimed screenshot
  OCR snippets were not surfaced, and said session folder open was path-only.
  These claims now match current code.

## Intentionally retained

- Skip-safe smoke scripts for PaddleOCR, Qwen embeddings, Qwen-VL, faster-whisper,
  Gemini/Gemma development mode, and Gemma E2B Ollama remain useful product proof
  and local-runtime verification seams. They are not dead code.
- `docs/superpowers/plans/**` contains historical implementation plans. These are
  stale by nature but useful as project memory; do not treat them as current
  product claims.
- Fake providers/transports and deterministic benchmark paths are retained because
  normal tests must not require live model services.

## Deferred Cleanup Candidates

- README is still too long and duplicates status across several sections. A later
  documentation pass should move detailed milestone history into `docs/`.
- Desktop model endpoint concepts are still split between React validation, Rust
  localhost bridge checks, and Python provider config. Keep this until local model
  runtime strategy work (#135), then consolidate naming and public copy.
- Optional model runtime docs are split across README, `docs/model-routing.md`,
  `docs/evals.md`, smoke evidence files, and ADR 0001. Issue #135 should become
  the model-runtime source of truth.
- Root-level `architecture.md` is absent; current architecture content lives at
  `docs/architecture.md`. Do not recreate a duplicate root document unless the
  owner wants root docs mirrored.
