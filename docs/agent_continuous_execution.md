# Agent Continuous Execution

This file records the durable workflow for future agents working on WorkTrace AI.

## Current Sequence

1. #69 - Export and report review UX
2. Screenshot metadata drawer and delete screenshots UI
3. Session browser, delete session, and open session folder
4. Local test and claim-discipline pass
5. Full sidecar packaging into installer
6. Performance and storage cleanup
7. Selective OCR runtime
8. Model download/cache manager
9. Local LLM report runtime
10. Embedding runtime
11. Optional audio transcription
12. Selected-frame VLM
13. Workflow debugger on real captured sessions
14. Final eval and benchmark report
15. Portfolio demo polish

## Execution Rules

- Work one issue at a time from latest `main`.
- Keep branch names in the form `codex/issue-<number>-short-title`.
- Use TDD: add focused failing tests, implement the smallest passing code, then refactor.
- Run the full quality gate before every PR.
- Merge only after GitHub checks pass.
- Update `docs/AGENT_STATE.md` after every major step.
- Create the next issue only after the current issue is merged and closed.

## Never Add Out Of Sequence

- OCR before the OCR issue.
- Model runtime or model downloads before model issues.
- File-content capture.
- Keylogging.
- Browser history scraping.
- Terminal spying/global shell capture.
- Cloud telemetry by default.

## Full Quality Gate

```powershell
cd services/local-agent
uv run --python 3.13 ruff format .
uv run --python 3.13 ruff check .
uv run --python 3.13 pyright
uv run --python 3.13 pytest
cd ../..
pnpm --dir packages/shared typecheck
pnpm --dir packages/shared test
pnpm --dir apps/desktop typecheck
pnpm --dir apps/desktop lint
pnpm --dir apps/desktop test
pnpm --dir apps/desktop build
cd apps/desktop/src-tauri
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```
