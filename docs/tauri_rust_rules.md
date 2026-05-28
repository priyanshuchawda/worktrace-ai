# tauri_rust_rules.md

Production rules for AI agents working on a **Tauri v2 + Rust + React + TypeScript** desktop app.

Use this file as the repo-level instruction file for Cursor, Codex, Claude Code, Copilot, or any AI coding agent.

---

# 0. Core Principle

The goal is not to make AI “write more code”.

The goal is to make AI produce **small, safe, testable, production-quality changes** that follow existing project architecture.

AI must behave like a careful senior engineer, not a fast code generator.

Golden rule:

```txt
Explore first. Plan second. Code third. Test always. Review before merge.
```

Production can never be guaranteed to “never break”, but this repo must make it very hard for bad changes to silently enter production.

---

# 1. Default AI Operating Mode

For every task, the AI must follow this exact workflow:

## 1.1 Explore

Before writing code:

- Read the relevant files.
- Understand existing architecture.
- Identify current patterns.
- Find similar existing implementations.
- Check naming conventions.
- Check how errors are handled.
- Check how tests are written.
- Check whether the task touches security-sensitive areas.

Do not code before this.

## 1.2 Plan

Before implementation, return a short plan with:

- Problem summary.
- Files likely to change.
- Existing patterns found.
- Smallest safe implementation.
- Test plan.
- Security/data-loss/regression risks.
- Anything that should not be changed.

## 1.3 Implement

During implementation:

- Make the smallest safe diff.
- Do not change unrelated files.
- Do not invent new architecture unless necessary.
- Do not add dependencies unless justified.
- Do not remove tests.
- Do not silence warnings.
- Do not hide errors.
- Do not weaken security settings.
- Add or update tests for changed behavior.

## 1.4 Verify

After implementation, run or clearly list the relevant commands:

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace

pnpm typecheck
pnpm lint
pnpm test
pnpm build
pnpm test:e2e
```

If a command cannot be run, explain why.

## 1.5 Report

Final response must include:

- Changed files.
- What changed.
- Tests run.
- Tests not run.
- Remaining risks.
- Manual QA steps.

---

# 2. Non-Negotiable Rules

These rules override all feature requests unless the user explicitly approves an exception.

## 2.1 Forbidden Without Explicit Approval

Do not do these without explicit approval:

- Delete files.
- Rewrite large parts of the app.
- Add new dependencies.
- Change lockfiles without dependency changes.
- Change Tauri capabilities/permissions.
- Add shell/process execution.
- Add broad filesystem access.
- Add network calls.
- Change updater/signing/release config.
- Weaken CSP.
- Store secrets in source code.
- Modify authentication/security logic.
- Modify database migrations destructively.
- Change public APIs silently.
- Mix refactor + feature + styling in one PR.
- Add fake “production-ready” claims without tests.

## 2.2 Required Behavior

Always:

- Follow existing style.
- Keep changes small.
- Use typed interfaces.
- Validate untrusted input.
- Add regression tests for bugs.
- Prefer clear code over clever code.
- Preserve user data.
- Make failure modes visible.
- Document important security decisions.
- Ask for approval before risky changes.

---

# 3. Tauri Architecture Rules

Tauri apps have two worlds:

```txt
React/TypeScript frontend = untrusted UI
Rust backend/native layer = trusted system boundary
```

The frontend may request actions.

Rust must validate and decide.

## 3.1 Frontend Responsibilities

React/TypeScript should handle:

- UI rendering.
- User interactions.
- Forms.
- Local UI state.
- Calling typed Tauri client functions.
- Displaying typed errors.
- Accessibility.
- Client-side validation for user experience only.

Frontend must not be the final authority for:

- File safety.
- Path safety.
- Permission decisions.
- Shell execution.
- Process spawning.
- Database integrity.
- Security-sensitive decisions.
- Secrets.
- Local system policy.

## 3.2 Rust Responsibilities

Rust should handle:

- Filesystem access.
- Path validation.
- Process execution.
- Native OS APIs.
- Tauri commands.
- Database writes.
- Background workers.
- Sidecar control.
- Security boundaries.
- Privacy/data retention logic.
- Durable state.
- Logging/telemetry safety.
- Error normalization.

## 3.3 IPC Boundary Rule

All communication between React and Rust must go through a typed IPC boundary.

Bad:

```ts
await invoke("delete_file", { path });
```

Good:

```ts
await tauriClient.deleteProjectFile({ relativePath });
```

Bad:

```rust
#[tauri::command]
fn delete_file(path: String) {
    std::fs::remove_file(path).unwrap();
}
```

Good:

```rust
#[tauri::command]
async fn delete_project_file(
    input: DeleteProjectFileInput,
    state: tauri::State<'_, AppState>,
) -> Result<DeleteProjectFileOutput, AppError> {
    input.validate()?;
    let safe_path = state.path_policy.resolve_project_path(&input.relative_path)?;
    state.file_service.delete_file(&safe_path).await?;
    Ok(DeleteProjectFileOutput { deleted: true })
}
```

---

# 4. Recommended Project Structure

Prefer this structure:

```txt
apps/desktop/
  src/
    app/
    components/
    features/
    hooks/
    lib/
      tauri-client.ts
      schemas.ts
      errors.ts
    types/

  src-tauri/
    src/
      main.rs
      lib.rs

      commands/
        mod.rs
        files.rs
        settings.rs
        recorder.rs
        sidecar.rs

      domain/
        mod.rs
        paths.rs
        validation.rs
        session.rs
        timeline.rs
        errors.rs

      services/
        mod.rs
        storage.rs
        process.rs
        capture.rs
        sidecar.rs

      state.rs
      telemetry.rs
      config.rs
```

## 4.1 Layering Rules

```txt
React components
  ↓
Typed frontend Tauri client
  ↓
Tauri command handlers
  ↓
Domain logic
  ↓
Services / storage / OS APIs
```

Rules:

- React components must not call `invoke` directly.
- Tauri command handlers should be thin.
- Business logic belongs in `domain/`.
- Side effects belong in `services/`.
- Validation should happen before side effects.
- Shared request/response shapes should be typed.
- Avoid circular dependencies.

---

# 5. Tauri Security Rules

Tauri security is critical because frontend bugs can become native system bugs.

## 5.1 Capability and Permission Rules

When touching Tauri capabilities or permissions:

- Use least privilege.
- Scope access to the smallest required window/webview.
- Scope commands narrowly.
- Do not add broad filesystem permissions.
- Do not add broad shell permissions.
- Do not expose dangerous commands to all windows.
- Explain why every added permission is necessary.
- Add tests/manual QA notes for permission behavior.

Before changing capabilities, AI must answer:

```txt
1. Which command needs access?
2. Which window/webview needs access?
3. Why is this permission minimal?
4. What abuse case is prevented?
5. What would go wrong if this permission were broader?
```

## 5.2 CSP Rules

Do not weaken Content Security Policy.

Forbidden without explicit approval:

- `unsafe-inline`
- `unsafe-eval`
- broad remote script sources
- loading unknown remote scripts
- disabling CSP protections
- adding wildcard sources

If CSP must change, explain:

- Why.
- Exact new source.
- Risk.
- Safer alternative considered.

## 5.3 Shell and Process Rules

Never accept raw shell commands from the frontend.

Bad:

```ts
await invoke("run_command", { command: userInput });
```

Good:

```ts
await invoke("start_indexer", { projectId });
```

Rust should choose the exact command internally.

Rules:

- Use allowlisted commands only.
- Validate arguments.
- Avoid shell string interpolation.
- Prefer structured command APIs.
- Capture and sanitize output.
- Add timeouts.
- Add cancellation.
- Avoid leaking secrets in logs.
- Do not run destructive commands without explicit confirmation.

## 5.4 Filesystem Rules

Frontend-provided paths are untrusted.

Rust must:

- Reject absolute paths unless explicitly allowed.
- Canonicalize paths.
- Check path is inside an allowed base directory.
- Reject path traversal.
- Avoid following unsafe symlinks when dangerous.
- Validate file extensions when needed.
- Use atomic writes for important data.
- Backup or transactionally update important files.
- Never delete recursively without explicit approval and tests.

Bad:

```rust
std::fs::read_to_string(input.path)?;
```

Good:

```rust
let path = path_policy.resolve_allowed_path(&input.relative_path)?;
let content = file_service.read_text_file(&path)?;
```

## 5.5 Secrets Rules

Never:

- Commit API keys.
- Log tokens.
- Send secrets to frontend.
- Store secrets in localStorage.
- Put secrets in screenshots/log exports.
- Include secrets in error messages.
- Add `.env` files to git.
- Print environment variables.

Use:

- OS keychain where appropriate.
- Tauri/plugin-supported secure storage if available.
- Redaction helpers.
- Secret scanning in CI where possible.

## 5.6 Updater and Signing Rules

Updater/signing/release config is security-critical.

Do not change without explicit approval.

If touched:

- Explain signing implications.
- Verify update URL.
- Verify public key handling.
- Verify release channel behavior.
- Do not disable signature verification.
- Do not allow arbitrary update URLs.

---

# 6. Rust Rules

Rust code should be safe, boring, explicit, and testable.

## 6.1 Error Handling

Use typed errors.

Preferred:

```rust
#[derive(thiserror::Error, Debug)]
pub enum AppError {
    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Permission denied")]
    PermissionDenied,

    #[error("File not found")]
    NotFound,

    #[error("Storage error")]
    Storage,

    #[error("Internal error")]
    Internal,
}
```

Rules:

- Do not expose raw internal errors to frontend.
- Do not leak paths/tokens/secrets in errors.
- Avoid `unwrap()` and `expect()` in production paths.
- Use `Result<T, AppError>`.
- Convert external errors at boundaries.
- Log detailed internal errors only after redaction.
- Return user-safe messages to frontend.

## 6.2 `unwrap` / `expect` Rules

Allowed:

- Tests.
- Truly impossible states with comments.
- Startup code where crashing is acceptable and explained.

Not allowed:

- IPC command handlers.
- Filesystem operations.
- Network calls.
- Process execution.
- Database operations.
- User input parsing.
- Background workers.

## 6.3 Async Rules

When using async Rust:

- Do not block async runtime with heavy sync work.
- Use `spawn_blocking` for CPU-heavy/blocking operations.
- Add cancellation for long-running tasks.
- Add timeouts for external processes.
- Avoid holding locks across `.await`.
- Avoid global mutable state.
- Use channels for background worker communication.
- Handle shutdown gracefully.

## 6.4 State Management

For Tauri state:

- Keep `AppState` small and intentional.
- Avoid dumping everything into global state.
- Use `Arc` where needed.
- Use `Mutex/RwLock` carefully.
- Do not hold locks while awaiting.
- Document what state is durable vs runtime-only.

## 6.5 Domain Logic

Domain logic should be pure where possible.

Good domain modules:

- Validate inputs.
- Transform data.
- Decide policies.
- Build timelines.
- Classify events.
- Compute summaries.
- Contain unit tests.

Domain modules should avoid:

- Direct UI calls.
- Direct Tauri APIs.
- Random filesystem access.
- Global process state.

## 6.6 Services

Services handle side effects:

- Storage service.
- File service.
- Process service.
- Sidecar service.
- Capture service.
- Telemetry service.

Rules:

- Services should have narrow public APIs.
- Services should return typed errors.
- Services should be testable.
- Services should not expose low-level unsafe operations to commands.

---

# 7. React + TypeScript Rules

Frontend code should be typed, accessible, and maintainable.

## 7.1 TypeScript Rules

Required:

- `strict: true`
- Avoid `any`
- Prefer `unknown` over `any`
- Use discriminated unions for state machines
- Use schema validation at boundaries
- Type Tauri command inputs/outputs
- Avoid duplicated types

Recommended `tsconfig` flags:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "useUnknownInCatchVariables": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

## 7.2 Component Rules

Components should:

- Be small.
- Have clear props.
- Avoid hidden side effects.
- Avoid huge JSX files.
- Use semantic HTML.
- Support keyboard usage.
- Handle loading/error/empty states.
- Avoid business logic inside render-heavy components.

If a component becomes large, split into:

```txt
FeaturePage.tsx
FeatureToolbar.tsx
FeatureList.tsx
FeatureItem.tsx
useFeatureData.ts
feature-types.ts
```

## 7.3 State Rules

Use the simplest state that works.

Prefer:

- Local state for UI-only state.
- URL state for navigational state.
- Server/native state from typed Tauri client.
- Reducer/state machine for complex flows.

Avoid:

- Duplicated derived state.
- Unnecessary global stores.
- Storing sensitive data in browser storage.
- `useEffect` chains that simulate workflows badly.
- Silent background mutations.

## 7.4 Effects Rules

Do not use `useEffect` as a dumping ground.

Rules:

- No side effects during render.
- Do not ignore hook dependency warnings.
- Avoid derived state in effects when it can be computed.
- Cleanup subscriptions/listeners.
- Abort/cancel long-running requests where possible.
- Handle component unmount safely.

## 7.5 Tauri Client Rules

Create a single typed Tauri client layer.

Example:

```ts
// src/lib/tauri-client.ts

export async function getSessionTimeline(
  input: GetSessionTimelineInput
): Promise<GetSessionTimelineOutput> {
  const parsed = GetSessionTimelineInputSchema.parse(input);
  return invoke<GetSessionTimelineOutput>("get_session_timeline", parsed);
}
```

Rules:

- Components do not call raw `invoke`.
- Client validates input for UX.
- Rust validates again for security.
- All command names live in one place.
- Output types are explicit.
- Errors are normalized.

## 7.6 Accessibility Rules

For all UI changes:

- Use semantic buttons/inputs.
- Add labels for form controls.
- Ensure keyboard navigation works.
- Do not remove focus indicators.
- Use ARIA only when semantic HTML is not enough.
- Provide loading and error states.
- Ensure modals trap focus.
- Ensure destructive actions require clear confirmation.

---

# 8. Data and Storage Rules

Desktop apps can lose user data if careless. Treat storage as production-critical.

## 8.1 SQLite Rules

If using SQLite:

- Use WAL mode where appropriate.
- Use migrations.
- Avoid destructive migrations.
- Use transactions for multi-step writes.
- Add indexes only when justified.
- Validate migration rollback/forward behavior.
- Do not block UI with long DB operations.
- Do not store secrets unless encrypted.
- Add tests for important queries.

## 8.2 Migration Rules

Never:

- Drop columns/tables casually.
- Delete user data without backup.
- Change schema without migration.
- Mix unrelated schema changes.

Always:

- Explain migration intent.
- Add migration tests if possible.
- Preserve existing data.
- Add safe defaults.
- Document irreversible changes.

## 8.3 File Write Rules

For important files:

- Write to temp file.
- Flush if needed.
- Rename atomically.
- Avoid partial writes.
- Handle disk full errors.
- Handle permission errors.
- Avoid corrupting existing data.

---

# 9. Sidecar Rules

If the app uses a Python/FastAPI/local AI sidecar, follow these rules.

## 9.1 Sidecar Boundary

The sidecar is not automatically trusted.

Rust should:

- Start/stop sidecar safely.
- Check health.
- Use localhost only unless explicitly approved.
- Use fixed allowlisted ports or safe dynamic port allocation.
- Add timeouts.
- Sanitize requests/responses.
- Restart carefully.
- Capture logs with redaction.
- Avoid exposing sidecar publicly.

## 9.2 Sidecar API Rules

Sidecar APIs should be:

- Versioned.
- Typed.
- Validated.
- Timeout-protected.
- Error-normalized.
- Tested separately.

## 9.3 Local AI Rules

For local LLM/OCR/vision/audio models:

- Do not block UI.
- Queue heavy tasks.
- Support cancellation.
- Limit memory usage.
- Add progress events.
- Use model availability checks.
- Degrade gracefully.
- Never upload private data unless explicitly approved.
- Clearly distinguish local vs remote processing.

---

# 10. Privacy Rules

For a desktop activity recorder, privacy is core product quality.

AI must protect:

- Screenshots.
- Audio transcripts.
- Browser metadata.
- Clipboard contents.
- File paths.
- App/window titles.
- User documents.
- Secrets visible on screen.
- Logs.
- Exports.

Rules:

- Default to local-first.
- Do not add remote telemetry without explicit approval.
- Redact secrets in logs.
- Provide deletion/export controls.
- Store only what is needed.
- Make retention behavior explicit.
- Avoid collecting sensitive fields accidentally.
- Do not log raw OCR/audio text unless necessary and approved.
- Keep debug logs opt-in for sensitive data.

---

# 11. Performance Rules

Desktop apps must feel fast.

## 11.1 Frontend Performance

- Avoid unnecessary re-renders.
- Virtualize large lists.
- Do not load huge timelines all at once.
- Debounce search/input where needed.
- Keep expensive computations out of render.
- Use memoization only when useful.
- Avoid giant global state updates.
- Split heavy components.

## 11.2 Rust Performance

- Do heavy work off the UI path.
- Use streaming/progress events for long tasks.
- Avoid unbounded memory growth.
- Use bounded queues.
- Add backpressure.
- Avoid cloning huge buffers unnecessarily.
- Prefer incremental processing.
- Profile before complex optimization.

## 11.3 AI/ML Performance

- Use small models by default.
- Lazy-load heavy models.
- Keep model workers separate from UI.
- Add model warmup only if needed.
- Cache embeddings/results carefully.
- Avoid reprocessing unchanged data.
- Add batch processing where useful.
- Track memory/CPU usage.

---

# 12. Testing Rules

Tests are not optional.

## 12.1 Rust Tests

Add Rust tests for:

- Path validation.
- Permission decisions.
- Input validation.
- Domain logic.
- Error mapping.
- Migration logic.
- File safety behavior.
- Sidecar state transitions.

Commands:

```bash
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
```

## 12.2 Frontend Tests

Add frontend tests for:

- User flows.
- Component states.
- Error displays.
- Loading states.
- Accessibility basics.
- Tauri client error handling.

Commands:

```bash
pnpm test
pnpm typecheck
pnpm lint
```

## 12.3 E2E Tests

Use Playwright for:

- Main app startup.
- Critical user journeys.
- Settings flows.
- Data import/export.
- Error states.
- Permission-denied flows.

Command:

```bash
pnpm test:e2e
```

## 12.4 Regression Tests

Every bug fix should include a test that fails before the fix.

Prompt AI:

```txt
Before fixing this bug, identify the regression test that would fail today.
Add that test first if practical.
Then implement the smallest fix.
```

---

# 13. CI Rules

A PR should not merge unless these pass:

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace

pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

For major UI/native changes, also run:

```bash
pnpm test:e2e
pnpm tauri build
```

Optional but recommended:

```bash
cargo deny check
cargo audit
pnpm audit
```

---

# 14. Dependency Rules

Dependencies are production risk.

Do not add dependencies unless:

- Existing code cannot reasonably solve it.
- The library is maintained.
- The license is acceptable.
- Bundle size impact is acceptable.
- Security risk is understood.
- Alternative was considered.

When adding dependency, AI must explain:

```txt
1. Why this dependency is needed.
2. Why existing dependencies are insufficient.
3. Maintenance/security status.
4. Bundle/runtime impact.
5. Files changed.
```

---

# 15. Logging and Telemetry Rules

Logs must help debugging without leaking private data.

Rules:

- Use structured logs where possible.
- Redact secrets.
- Redact user content unless explicitly needed.
- Do not log full screenshots/OCR/audio text.
- Include operation IDs for debugging.
- Include safe error categories.
- Avoid noisy logs.
- Make debug logging opt-in.
- Do not send telemetry remotely without explicit approval.

---

# 16. Error UX Rules

The user should understand what failed and what to do.

Bad:

```txt
Something went wrong.
```

Good:

```txt
Could not save the session because the storage folder is not writable.
Choose another folder or check permissions.
```

Rules:

- User-facing errors should be actionable.
- Internal errors should be redacted.
- Do not expose stack traces to UI.
- Keep technical details in safe logs.
- Provide retry only when retry can help.
- Do not silently fall back if it hides failure.

---

# 17. AI Code Quality Rules

AI must avoid common slop patterns.

## 17.1 Forbidden Slop

Do not produce:

- Huge god files.
- Generic utility dumping grounds.
- Duplicate types.
- Unused abstractions.
- Unused components.
- Dead code.
- Fake TODO-driven implementation.
- Broad try/catch swallowing errors.
- Silent fallbacks.
- Magic strings spread everywhere.
- Business logic inside JSX.
- `any` everywhere.
- `unwrap()` everywhere.
- Overcomplicated architecture for simple tasks.
- “Production-ready” claims without proof.

## 17.2 Preferred Code Style

Prefer:

- Small modules.
- Clear names.
- Typed errors.
- Exhaustive matches.
- Explicit state transitions.
- Tests near behavior.
- Pure functions for logic.
- Narrow APIs.
- Boring predictable code.
- Comments only where they explain why, not what.

---

# 18. Refactor Rules

Refactors must be separated from features.

Allowed refactor PR:

```txt
- No behavior change.
- No UI change.
- No permission change.
- Tests pass before and after.
- Public APIs preserved unless approved.
```

Refactor process:

```txt
1. Add/confirm characterization tests.
2. Move code mechanically.
3. Rename clearly.
4. Remove duplication.
5. Run full verification.
```

Do not combine:

```txt
feature + refactor + dependency upgrade + UI redesign
```

in one change.

---

# 19. Security Review Checklist

Before merging changes, review:

```txt
Tauri:
[ ] Did permissions/capabilities change?
[ ] Is access least-privilege?
[ ] Did CSP weaken?
[ ] Did updater/signing change?
[ ] Are dangerous commands exposed?

Rust:
[ ] Are inputs validated?
[ ] Are paths canonicalized?
[ ] Are shell/process args allowlisted?
[ ] Are errors typed and redacted?
[ ] Are secrets protected?
[ ] Are panics avoided?

Frontend:
[ ] Are raw invoke calls avoided?
[ ] Are types strict?
[ ] Are errors displayed safely?
[ ] Is sensitive data avoided in localStorage?
[ ] Is accessibility preserved?

Data:
[ ] Are writes atomic/transactional?
[ ] Are migrations safe?
[ ] Is deletion confirmed?
[ ] Is user data preserved?

AI/sidecar:
[ ] Is local/private data protected?
[ ] Are sidecar ports local-only?
[ ] Are model tasks cancellable?
[ ] Are logs redacted?
```

---

# 20. PR Rules

Every PR must include:

```md
## Summary

What changed and why.

## Files Changed

Main files changed.

## Tests

- [ ] cargo fmt
- [ ] cargo clippy
- [ ] cargo test
- [ ] pnpm typecheck
- [ ] pnpm lint
- [ ] pnpm test
- [ ] pnpm build
- [ ] pnpm test:e2e, if needed

## Security Notes

Mention permissions, filesystem, shell, secrets, updater, CSP.

## Data Safety

Mention migrations, deletion, storage, user data impact.

## Manual QA

Steps to verify manually.

## Risks

Remaining risks or limitations.
```

---

# 21. Best Prompts for AI Agents

## 21.1 Default Implementation Prompt

```txt
Act as a senior Tauri v2, Rust, React, and TypeScript engineer.

Task:
<task>

Follow tauri_rust_rules.md strictly.

Before coding:
1. Inspect relevant files.
2. Identify existing patterns.
3. Produce a short implementation plan.
4. List files likely to change.
5. List risks.
6. List tests to add/update.

Implementation rules:
- Smallest safe diff.
- No unrelated changes.
- No new dependencies unless justified.
- No Tauri permission/capability/CSP/updater/signing changes unless explicitly required.
- Frontend input is untrusted.
- Rust validates all IPC input.
- Use typed errors.
- Avoid unwrap/expect in production paths.
- Add tests for changed behavior.

After coding:
- Run or list verification commands.
- Summarize changed files.
- Explain risks and manual QA.
```

## 21.2 Bug Fix Prompt

```txt
Investigate this bug in the Tauri/Rust/React app.

Bug:
<bug>

Do not code first.

First return:
1. Likely cause.
2. Relevant files.
3. Failing path.
4. Regression test that should be added.
5. Smallest safe fix.

Then implement the fix with the regression test.
Do not refactor unrelated code.
```

## 21.3 Security Review Prompt

```txt
Review this diff as a senior Tauri desktop security reviewer.

Focus on:
- Tauri permissions/capabilities
- IPC exposure
- frontend-controlled paths
- filesystem access
- shell/process execution
- CSP
- updater/signing
- secrets
- unsafe Rust
- logs leaking private data
- destructive data operations

Return:
1. Blockers
2. High risks
3. Medium risks
4. Low risks
5. Exact file concerns
6. Minimal safer fix
```

## 21.4 Code Quality Review Prompt

```txt
Review this diff for production code quality.

Look for:
- AI slop
- overengineering
- poor architecture
- weak typing
- bad error handling
- duplicate logic
- large files
- hidden side effects
- missing tests
- accessibility regressions
- performance risks

Do not rewrite everything.
Give the smallest changes that significantly improve quality.
```

## 21.5 Refactor Prompt

```txt
Refactor this area without changing behavior.

Rules:
- No feature changes.
- No UI behavior changes.
- No Tauri permission changes.
- No dependency changes.
- Preserve public APIs unless approved.
- Add/confirm tests before refactor.
- Keep diff mechanical and reviewable.

Return:
1. Current problem.
2. Refactor plan.
3. Files changed.
4. How behavior is preserved.
5. Tests run.
```

---

# 22. Manual QA Checklist

Before merging desktop app changes:

```txt
[ ] App starts successfully.
[ ] Main window loads.
[ ] No console errors.
[ ] No Rust panics.
[ ] Changed feature works.
[ ] Error state works.
[ ] Loading state works.
[ ] Keyboard navigation works.
[ ] Data persists after restart.
[ ] No unexpected permission prompt.
[ ] No sensitive data in logs.
[ ] App still builds.
```

For recorder/local AI apps:

```txt
[ ] Start session works.
[ ] Stop session works.
[ ] App handles cancellation.
[ ] App handles sidecar missing.
[ ] App handles model unavailable.
[ ] App handles low-memory/slow processing.
[ ] Timeline does not freeze UI.
[ ] Private data is not uploaded.
[ ] Logs are redacted.
```

---

# 23. Final Rule

AI may assist with implementation.

AI does not own production quality.

Production quality comes from:

```txt
clear architecture
+ strict types
+ least privilege
+ small diffs
+ tests
+ CI gates
+ separate review
+ manual QA
```

When in doubt, choose the safer, smaller, more testable change.
