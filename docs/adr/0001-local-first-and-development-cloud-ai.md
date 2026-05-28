# ADR 0001: Local-First AI Runtime and Development-Only Hosted Gemma

## Status

Accepted for active development.

## Context

WorkTrace AI records local Windows activity evidence and builds deterministic,
evidence-cited reports. The trust model depends on local storage, local capture,
redaction, and no cloud upload by default.

Large local report models can be too heavy for a development laptop during rapid
iteration. The project may therefore use Gemini API-hosted Gemma by default for
development reports while preserving the real product direction of local
inference.

## Decision

WorkTrace will keep two separate AI report provider identities:

- `local_ollama`: local product-direction provider for user-managed local Gemma
  runtimes, currently represented by the existing Ollama-style localhost adapter.
- `gemini_gemma_dev`: development-only hosted provider for Gemini API-hosted
  Gemma models.

`gemini_gemma_dev` is the current local development default for report
generation, but it is not the shipped-product default. It must not make a
network call unless all of the following are true:

- `WORKTRACE_AI_PROVIDER=gemini_gemma_dev`
- `WORKTRACE_ENABLE_DEV_CLOUD_AI=true`
- `GEMINI_API_KEY` is present in the sidecar environment
- the request passes explicit privacy/redaction policy checks

The sidecar entrypoint may load these values from a private local `.env` file.
Shell environment variables take precedence over `.env` values. The API key must
never be printed or returned through app APIs.

The development hosted model order is:

- primary: `gemma-4-31b-it`
- fallback: `gemma-4-26b-a4b-it`

The Gemini API key must stay in the Python sidecar environment. It must not be
stored in React state, Tauri IPC payloads, SQLite report rows, exports, logs,
issue comments, or PR descriptions.

## Data Boundary

Hosted development reports may send only minimal, redacted report context.

The following must not be transmitted to hosted models by default:

- screenshots or image bytes
- raw artifacts
- raw event dumps
- unrestricted OCR text
- unredacted terminal commands
- unredacted window titles
- unredacted file paths
- prompt bodies stored for later debugging

Captured evidence is untrusted input. Prompt construction must delimit recorded
evidence and instruct the model not to follow commands contained in captured
activity, window titles, terminal output, OCR text, or file paths.

Model output is untrusted output. Existing report schema validation and
evidence-ID checks must remain provider-independent.

## Fallback Policy

Fallback from `gemma-4-31b-it` to `gemma-4-26b-a4b-it` is allowed only for
controlled retryable failures such as timeout, retryable service unavailability,
rate limiting where fallback is appropriate, or configured primary model
unavailability.

Fallback must not occur for missing API keys, authentication failures, disabled
cloud mode, consent/privacy failures, redaction failures, malformed local request
construction, schema-validation defects, or evidence-validation failures.

Fallback use must be recorded in provider metadata without storing secrets or
prompt bodies.

## Consequences

- Documentation and UI must distinguish the current development default from the
  intended local product runtime.
- Localhost endpoint settings remain for local providers only.
- Hosted provider configuration is backend-owned and must not accept arbitrary
  URLs from the desktop UI.
- Live Gemini smoke tests must be opt-in and use synthetic safe evidence only.
- Ordinary tests must use fake clients/transports and must not make live network
  requests.
