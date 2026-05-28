# OCR Runtime Policy

Selective OCR is allowed only after capture, privacy, export, session deletion, sidecar packaging, and storage cleanup are stable.

Current #79 policy:

- OCR may run only on changed, high-value screenshots.
- High-value examples: terminal errors, test failure screens, browser warnings, dialogs, popups, and traceback windows.
- OCR must not run for private-mode sessions or blocked apps.
- OCR must refuse likely secret-risk screens before detailed extraction.
- Stored OCR snippets must be redacted and linked to screenshot evidence IDs.
- OCR output is evidence, not an autonomous claim. Reports must still cite source events/screenshots.
- Continuous OCR of every screenshot is forbidden.
- No OCR model files are committed to git.
- Real PaddleOCR integration is optional and must degrade to unavailable if the runtime is absent.
- Real PaddleOCR binding must be lazy and local-only, with no heavy imports in non-OCR recording paths.
- Selective OCR must cap jobs per session to avoid continuous OCR behavior.
- Runtime failures must fail safely and skip the candidate.

The default runtime state should be disabled/unavailable unless explicitly configured.

## PaddleOCR smoke status

On 2026-05-08, the repository gained a skip-safe PaddleOCR sample smoke command:

```txt
cd services/local-agent
uv run --python 3.13 python scripts/smoke_paddleocr_sample.py
```

The command uses an embedded local PNG sample and the existing lazy PaddleOCR
adapter. It does not download model files, does not bundle PaddleOCR, and does
not run during normal recording or CI.

Current local result on this Windows machine:

```txt
status: skipped
provider: paddleocr
reason: OCR runtime provider paddleocr is not installed. Recording continues without OCR.
privacy_leak_count: 0
```

This proves the real-runtime smoke path is safe to invoke and degrades cleanly
when PaddleOCR is absent. It is not a real PaddleOCR accuracy, latency, memory,
or packaging proof until a user-managed PaddleOCR install is present and the
same command returns `status: passed`.
