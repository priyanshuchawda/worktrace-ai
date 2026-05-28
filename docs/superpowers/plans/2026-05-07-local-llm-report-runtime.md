# Local LLM Report Runtime

**Goal:** Add a safe first local report-runtime adapter that can call a localhost model service through an injectable transport while preserving existing evidence-cited JSON validation and no-download/no-recording-load policies.

**Architecture:** Keep `reporting.py` as the report contract and validation layer. Add a small adapter module for an Ollama-style localhost `/api/generate` endpoint. The adapter must reject non-localhost URLs, use fake transports in tests, avoid model package imports, and expose safe failures that existing report generation wraps as `ReportGenerationError`.

## Step 1: Red Tests

Add tests for non-localhost rejection, prompt POST payload, conservative generation budgets, prompt-size refusal before transport, mode/context cap validation, safe transport failure, integration with `generate_evidence_cited_report`, and no heavy model imports.

Run: `cd services/local-agent; uv run --python 3.13 pytest tests/test_local_report_runtime.py -q`

Expected: FAIL because no local report runtime adapter exists.

## Step 2: Implement Adapter

Add typed config, a JSON transport protocol, a stdlib urllib transport for production use, conservative generation options, prompt budget validation, and an `OllamaReportModel` implementing the existing `LocalReportModel` protocol. Do not add dependencies, downloads, or runtime startup logic.

## Step 3: Docs

Update README and local model docs to say a localhost adapter exists, but no model is bundled/downloaded and no real runtime smoke has been run unless it actually is.

## Step 4: Verification

Run focused Python tests, then the full gate from `docs/agent_continuous_execution.md`. Run `git diff --check` before commit.
