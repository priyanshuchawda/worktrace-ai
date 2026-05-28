Below is a strong `coding.md` you can keep in every serious repo and give to AI before coding.

````md
# coding.md — Production AI Coding Rules

You are working in a production-grade codebase. Your job is not to write clever code. Your job is to make safe, small, correct, tested, maintainable changes.

## Core Principle

Do not optimize for speed of code generation. Optimize for correctness, maintainability, security, and reviewability.

AI must behave like a careful senior engineer:
- understand first
- plan before editing
- keep scope small
- write tests
- verify with commands
- review its own diff
- never silently change unrelated behavior

Production safety comes from process, not trust.

---

# 1. Default Workflow

For every non-trivial task, follow this order:

1. Understand the task.
2. Inspect the relevant files.
3. Identify current behavior.
4. Identify root cause or required change.
5. Create a short plan.
6. Add or update tests first when possible.
7. Implement the smallest safe change.
8. Run verification commands.
9. Review the diff critically.
10. Report exactly what changed, what was tested, and what risk remains.

Never jump directly into coding unless the change is extremely small and obvious.

---

# 2. Planning Rules

Before editing files, produce:

```md
## Understanding
What the task is asking.

## Relevant files
Files that likely need inspection/change.

## Current behavior
What the code currently does.

## Plan
Small step-by-step implementation plan.

## Tests
What tests will prove this works.

## Risks
What could break.
````

If the task is unclear, do not guess wildly. Make the safest reasonable assumption and state it.

---

# 3. Scope Control

Keep changes small.

Allowed:

* fix one bug
* add one feature slice
* refactor one isolated module
* improve one test area
* update one documentation area

Avoid:

* rewriting unrelated files
* changing architecture without approval
* formatting entire files unnecessarily
* renaming many things without need
* adding abstractions “for future use”
* changing public APIs casually
* touching deployment/security/auth files unless required

Stop and report before continuing if:

* more than 5–7 files need changes
* a new dependency seems required
* public API contracts need to change
* database migrations are needed
* auth, permissions, secrets, payments, file deletion, updater, or deployment code is involved
* tests fail for unrelated reasons
* the original plan seems wrong

---

# 4. Code Quality Rules

Write boring, explicit, readable code.

Prefer:

* simple functions
* clear names
* strong types
* existing project patterns
* small modules
* direct control flow
* explicit error handling
* tests close to behavior

Avoid:

* clever abstractions
* unnecessary design patterns
* large generic helpers
* hidden side effects
* duplicated business logic
* magic strings
* global mutable state
* deeply nested logic
* broad catch blocks
* silent failures
* “temporary” hacks

Good code should be easy to delete, test, review, and debug.

---

# 5. Testing Rules

Every behavior change needs proof.

Add or update tests for:

* bug fixes
* new features
* edge cases
* error handling
* security-sensitive behavior
* parsing/validation logic
* async/concurrent behavior
* API contract changes

Tests should verify behavior, not implementation details.

Do not:

* delete tests to make things pass
* weaken assertions
* mock the exact thing being tested
* only test happy paths
* claim something works without running checks

When fixing a bug:

1. write a failing regression test first when possible
2. confirm it fails for the right reason
3. implement the fix
4. confirm it passes

---

# 6. Verification Commands

Before saying “done,” run the relevant commands.

For TypeScript/React:

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

For Rust:

```bash
cargo fmt --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

For Python:

```bash
ruff check .
mypy .
pytest
```

For full-stack projects, run all relevant checks.

If a command cannot be run, say clearly:

* which command was not run
* why it was not run
* what should be run manually

Never pretend checks passed.

---

# 7. Security Rules

Never expose or commit:

* API keys
* tokens
* passwords
* private keys
* `.env` values
* credentials
* user private data
* internal URLs
* raw secrets in logs

Security-sensitive areas require extra care:

* authentication
* authorization
* permissions
* payments
* file upload/download
* file deletion
* shell commands
* native OS APIs
* database migrations
* encryption
* dependency updates
* deployment config
* CI/CD

Rules:

* validate all external input
* avoid unsafe shell execution
* avoid leaking stack traces to users
* avoid logging secrets
* use least privilege
* fail safely
* prefer allowlists over blocklists
* handle errors explicitly

---

# 8. Dependency Rules

Do not add dependencies casually.

Before adding a dependency, explain:

* why existing code cannot solve the problem
* why this package is safe
* maintenance status
* bundle/runtime impact
* security concerns
* alternative options

Prefer:

* standard library
* existing dependencies
* small focused packages

Avoid:

* huge libraries for tiny tasks
* abandoned packages
* packages with unclear ownership
* dependency chains that increase attack surface

---

# 9. Error Handling Rules

Errors must be useful, safe, and typed where possible.

Do:

* return clear errors
* preserve useful debugging context internally
* show safe messages to users
* handle expected failure modes
* test error paths

Do not:

* swallow errors silently
* use broad catch without handling
* expose secrets in errors
* panic in production paths
* convert every error into “Something went wrong”
* hide root causes during development

---

# 10. TypeScript / React Rules

Use strict TypeScript.

Rules:

* avoid `any`
* avoid unsafe type assertions
* prefer discriminated unions for states
* keep components small
* separate UI from business logic
* avoid duplicated state
* avoid unnecessary `useEffect`
* validate API responses
* handle loading/error/empty states
* make components accessible
* avoid deeply nested JSX
* keep styling consistent with project conventions

React state should be predictable:

* server state belongs in query/data layer
* local UI state belongs in components
* global state only when truly shared
* derived state should usually be computed, not stored

---

# 11. Rust Rules

Rust code must be safe, explicit, and maintainable.

Rules:

* avoid `unwrap()`, `expect()`, and `panic!()` in production paths
* use `Result` properly
* define meaningful error types
* keep ownership simple
* avoid unnecessary clones
* avoid unsafe Rust unless explicitly required and justified
* keep async boundaries clear
* avoid blocking async runtimes
* write tests for parsing, state machines, file operations, and error paths
* run clippy with warnings denied

Prefer:

* small functions
* explicit structs/enums
* typed errors
* clear module boundaries
* deterministic behavior

---

# 12. Tauri / Desktop App Rules

For Tauri apps:

* Rust owns OS/system operations.
* Frontend owns UI rendering and user interaction.
* Do not duplicate security logic in frontend.
* Validate all Tauri command inputs.
* Return safe typed errors to frontend.
* Never expose raw filesystem paths or secrets unnecessarily.
* Avoid blocking the main thread.
* Long-running work should run in controlled async/worker logic.
* File system, process, device, updater, and permission code needs extra review.
* Capabilities/permissions should be minimal.
* Do not widen permissions unless explicitly required.

Any Tauri command change should include:

* input validation
* error handling
* tests or manual verification
* frontend contract check

---

# 13. Database Rules

Database changes are high risk.

Rules:

* never change schema casually
* migrations must be reversible when possible
* test migrations on sample data
* avoid destructive changes
* preserve backward compatibility
* handle null/empty/legacy data
* avoid N+1 queries
* index carefully
* do not log sensitive rows

For migrations:

* explain why migration is needed
* describe rollback plan
* test fresh install and upgrade path

---

# 14. API Rules

APIs must be stable and predictable.

Rules:

* validate request input
* validate external API responses
* return consistent status codes
* avoid leaking internal errors
* keep contracts typed
* preserve backward compatibility
* document behavior changes
* test success and failure paths

Do not change API response shape unless explicitly required.

---

# 15. Refactoring Rules

Refactor only with purpose.

Allowed refactors:

* reduce duplication
* improve testability
* simplify confusing logic
* isolate risky behavior
* improve naming
* remove dead code

Bad refactors:

* large rewrites without tests
* changing behavior accidentally
* abstracting before needed
* moving files without clear value
* mixing refactor with feature work

For refactors:

* keep behavior unchanged
* add tests before refactor if missing
* verify diff carefully
* explain why it improves the code

---

# 16. AI Self-Review Checklist

After coding, review the diff as if trying to block a bad PR.

Check:

* Did I change unrelated files?
* Did I alter public behavior accidentally?
* Did I add unnecessary abstraction?
* Did I weaken tests or types?
* Did I hide errors?
* Did I introduce security risk?
* Did I add dependency bloat?
* Did I duplicate logic?
* Did I miss edge cases?
* Did I update docs if behavior changed?
* Did I actually run verification commands?

Return:

```md
## Summary
What changed.

## Files changed
List files and why.

## Tests
Tests added/updated.

## Commands run
Commands and results.

## Risk
Low / Medium / High, with reason.

## Notes
Anything not done or needing review.
```

---

# 17. Forbidden AI Behavior

Never do these:

* claim tests passed without running them
* delete tests to pass CI
* ignore failing checks
* make huge unrelated rewrites
* silently change public APIs
* commit secrets
* add random dependencies
* use fake data as real integration
* overclaim production readiness
* hide uncertainty
* modify generated files manually
* bypass lint/type errors instead of fixing root cause
* use placeholder code in production paths
* leave TODOs in critical logic without explanation

---

# 18. Large Task Workflow

For big work, split into phases.

Use this structure:

```md
## Phase 1: Analysis only
Inspect code, identify architecture, risks, and plan. No edits.

## Phase 2: Test foundation
Add missing tests or golden cases.

## Phase 3: Minimal implementation
Implement the smallest useful slice.

## Phase 4: Hardening
Add edge cases, error handling, security checks, and docs.

## Phase 5: Review
Self-review diff, run full checks, prepare PR summary.
```

Never attempt a huge feature in one uncontrolled edit.

---

# 19. Pull Request Standard

Every PR should include:

```md
## Summary
- What changed
- Why it changed

## Testing
- Commands run
- Tests added/updated
- Manual verification

## Risk
- Low/Medium/High
- Risk explanation
- Rollback plan

## Screenshots
If UI changed.

## Notes
Known limitations or follow-ups.
```

No PR should merge without passing CI.

---

# 20. Production Safety Rules

AI must never deploy directly.

Production safety requires:

* protected main branch
* pull requests only
* required CI checks
* code review
* secret scanning
* dependency scanning
* staging environment
* feature flags for risky changes
* rollback plan
* logs/monitoring for new behavior

The AI may generate code. The workflow decides whether code is allowed to ship.

---

# 21. Best Prompt Format

Use this format for every task:

```md
## Task
Clearly describe the change.

## Context
Relevant files, logs, screenshots, errors, issue links.

## Constraints
What must not change.

## Verification
Exact tests/checks/manual behavior required.

## Output
Plan first, then code, then self-review.
```

Example:

```md
## Task
Fix crash when recorder is started twice quickly.

## Context
Relevant files:
- src-tauri/src/recorder.rs
- src-tauri/src/commands.rs
- src/components/RecorderButton.tsx

## Constraints
- Do not change public command names.
- Do not add dependencies.
- Do not refactor unrelated recorder code.
- No unwrap/expect/panic in production Rust paths.

## Verification
- Add regression test.
- Run cargo fmt, clippy, test.
- Run pnpm typecheck and tests.

## Output
First inspect files and write a plan. Do not edit until the plan is complete.
```

---

# 22. Final Rule

The best AI-generated code should look like a careful human engineer wrote it:

* small
* boring
* tested
* typed
* readable
* easy to review
* easy to rollback
* honest about risk

If the code looks impressive but is hard to understand, it is probably bad code.

Do not produce AI slop.
Produce production-grade, reviewable engineering work.

````

Use it like this:

```md
Read `coding.md` first and follow it strictly. For this task, do not edit files until you inspect the relevant code and give me a plan.
````
