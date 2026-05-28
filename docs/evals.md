# Evals

Initial Phase 0 placeholder. See `../plan.md` for the evaluation strategy.

Planned evaluation work:

- golden sessions
- `timeline_accuracy`
- `blocker_precision`
- `blocker_recall`
- `hallucinated_event_count`
- `privacy_leak_count`
- AI report evidence citation validity
- AI report unavailable-runtime fallback

MVP 4 now includes the first deterministic golden-session eval runner:

```powershell
cd services/local-agent
uv run --python 3.13 python scripts/evaluate_model.py
```

The current runner uses 20 compact local golden sessions and prints two reproducible Markdown benchmark tables:

- deterministic timeline/workflow evals
- AI report evals for deterministic report output, fake Gemma E2B output, fake Gemma E4B deep output, and model-unavailable fallback

Latency, RAM, memory, and storage columns are deterministic estimates for regression tracking only; real Windows resource-budget enforcement is handled separately.

The AI report benchmark is intentionally fake-runtime based. It does not download, start, or smoke-test real Gemma, Qwen, OCR, VLM, or audio models. It verifies that generated report claims cite known evidence IDs, invalid evidence IDs fail, privacy leak count remains zero, unavailable runtime fallback is represented, and no model is marked as called during recording.

The current portfolio-facing aggregate result is recorded in `eval-results.md`.
Re-run the command before updating public metrics.

Later real-runtime eval work must stay optional/skipping in CI and must record exact local runtime versions before making any real model quality or performance claim.
