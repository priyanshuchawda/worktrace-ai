# Embedding Model Notes

Embedding models support retrieval, command similarity, workflow grouping, and session search.

Current status:

- Default embedding model manifest: `Qwen/Qwen3-Embedding-0.6B`.
- Runtime adapter is localhost-only and fakeable; no heavy embedding imports are required for availability checks.
- Embedding runtime is not loaded during recording.
- Automatic model downloads are disabled.
- Manual cache spec exists for `model.safetensors` only (metadata + checksum policy).
- A skip-safe smoke command exists:
  `uv run --python 3.13 python scripts/smoke_qwen_embedding.py`.
  It requires `WORKTRACE_QWEN_EMBEDDING_BASE_URL` to point to an explicit
  localhost runtime.

Embeddings are not a source of truth. Any final claim must still cite raw event, screenshot, OCR, or timeline evidence IDs.

## Qwen3 embedding smoke status

On 2026-05-08, the smoke command was run without a configured local endpoint:

```txt
status: skipped
model_name: Qwen/Qwen3-Embedding-0.6B
endpoint: not_configured
reason: WORKTRACE_QWEN_EMBEDDING_BASE_URL is not configured.
privacy_leak_count: 0
```

This proves the smoke path is safe to invoke and does not load or download a
model unless a user-managed localhost endpoint is explicitly configured. It is
not a real embedding quality, latency, memory, or vector-index proof until the
same command returns `status: passed` against a local runtime.

## Vector storage decision

- First implementation: keep embedding vectors in SQLite tables for small/local indexes.
- Future scale path: add a local file index only if measured index growth or query latency requires it.
- Cloud vector DB is out of scope.
