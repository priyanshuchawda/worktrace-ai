Copy this as **`react_typescript.md`** and give it to any AI coding agent before it edits your React/TypeScript/Tailwind project.

````md
# React + TypeScript + Tailwind Production Rules for AI Coding Agents

You are working in a production React + TypeScript + Tailwind codebase.

Your goal is not to write fast code.
Your goal is to write correct, maintainable, tested, accessible, production-safe code with the smallest safe diff.

---

## 1. Core Principle

AI may write code, but AI must not behave like an unchecked auto-complete.

Before changing code:

1. Understand the existing project.
2. Follow existing patterns.
3. Plan the change.
4. Make a small diff.
5. Add/update tests.
6. Run verification commands.
7. Self-review the diff.
8. Report risks honestly.

Never make large uncontrolled rewrites.

---

## 2. Non-Negotiable Rules

- Do not break existing behavior.
- Do not edit unrelated files.
- Do not rewrite large files unless explicitly asked.
- Do not remove tests.
- Do not weaken types.
- Do not silence errors.
- Do not fake implementation.
- Do not add random dependencies.
- Do not change public APIs unless required.
- Do not touch auth, security, payments, env config, deployment, database, or analytics without clearly explaining why.
- Do not make code “look better” while changing behavior accidentally.
- Do not claim something is production-ready unless checks pass.

Forbidden unless explicitly justified:

```ts
any
// @ts-ignore
// @ts-expect-error
eslint-disable
dangerouslySetInnerHTML
as unknown as
````

---

## 3. Required Workflow

For every task, follow this workflow:

```txt
Read relevant files
↓
Understand existing patterns
↓
Create short plan
↓
Implement smallest safe change
↓
Add/update tests
↓
Run checks
↓
Self-review diff
↓
Fix issues
↓
Final report
```

For complex tasks, do not implement everything in one giant patch.
Break work into PR-sized steps.

---

## 4. Before Coding, Always Report

Before editing files, explain:

1. What existing patterns were found
2. Which files need changes
3. What the minimal plan is
4. What risks exist
5. What tests will be added or updated

Do not start coding blindly.

---

## 5. React Rules

Write React code that is simple, predictable, and easy to test.

### Components

* Prefer small focused components.
* Keep JSX readable.
* Avoid huge components.
* Extract complex logic into hooks or pure functions.
* Keep business logic out of deeply nested JSX.
* Prefer composition over prop drilling.
* Do not create global state for local UI state.
* Do not overuse context.
* Do not overuse memoization.

### State

Use explicit state models for async UI.

Prefer this:

```ts
type ViewState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "empty" }
  | { status: "success"; data: T };
```

Avoid messy combinations like:

```ts
const [loading, setLoading] = useState(false);
const [error, setError] = useState("");
const [data, setData] = useState([]);
```

because they can create impossible states.

### Effects

* Avoid unnecessary `useEffect`.
* Do not use `useEffect` for simple derived values.
* Always clean up subscriptions, timers, event listeners, and async side effects.
* Avoid infinite render loops.
* Keep dependency arrays correct.
* Do not suppress hook dependency warnings without strong reason.

### Rendering

* Use stable keys.
* Do not use array index as key when list order can change.
* Handle loading, error, empty, and success states.
* Avoid layout shift where possible.
* Avoid rendering broken partial UI.

---

## 6. TypeScript Rules

TypeScript must protect production behavior.

* Use strict types.
* Do not use `any`.
* Avoid unsafe casts.
* Prefer clear domain types.
* Prefer discriminated unions for state.
* Validate external data.
* Keep types close to the domain.
* Do not create over-complicated generic types.
* Do not silence TypeScript errors.
* Do not weaken types just to make code pass.

### External Data

Never trust API responses, URL params, localStorage, cookies, or user input.

Validate or narrow them before use.

Good:

```ts
const parsed = UserSchema.safeParse(response);

if (!parsed.success) {
  return { status: "error", message: "Invalid response" };
}

return { status: "success", data: parsed.data };
```

Bad:

```ts
const user = response as User;
```

---

## 7. Tailwind Rules

Tailwind code must follow the project design system.

* Use existing spacing, colors, typography, and component patterns.
* Do not invent random styles.
* Preserve responsive behavior.
* Preserve dark mode if the app supports it.
* Add proper hover, focus, active, disabled, and loading states.
* Avoid unreadable class soup.
* Extract repeated class patterns into reusable components or variants when useful.
* Use `clsx`, `cn`, `tailwind-merge`, or `class-variance-authority` if already used in the project.
* Do not add new styling libraries unless explicitly approved.

Bad:

```tsx
<div className="p-3 mt-7 text-[13px] bg-[#f8f8f8] rounded-[13px]">
```

Better:

```tsx
<Card className="mt-6 p-4 text-sm">
```

Follow existing project style.

---

## 8. Accessibility Rules

Every UI change must be accessible.

* Use semantic HTML.
* Buttons must be `<button>`.
* Navigation links must be `<a>` or framework link components.
* Inputs must have labels.
* Error messages must be connected to fields.
* Focus states must be visible.
* UI must be keyboard usable.
* Modals, dropdowns, and menus must handle focus correctly.
* Do not use ARIA where semantic HTML is enough.
* Do not remove accessibility attributes.
* Do not rely only on color to communicate state.

For forms:

* Show validation errors clearly.
* Disable submit while submitting.
* Prevent duplicate submissions.
* Preserve user input after recoverable errors.

---

## 9. Security Rules

Frontend security still matters.

* Never expose secrets in client code.
* Never hardcode API keys.
* Never trust client-side validation alone.
* Never inject raw HTML unless sanitized and justified.
* Validate URLs before opening or redirecting.
* Avoid unsafe `target="_blank"` usage.

Use:

```tsx
<a target="_blank" rel="noreferrer">
```

Do not log sensitive data:

* tokens
* cookies
* passwords
* auth headers
* private user data
* API keys
* raw error objects that may contain secrets

---

## 10. Data Fetching Rules

Follow existing project patterns.

If the project uses server components, server actions, loaders, React Query, SWR, or custom hooks, follow that pattern.

Rules:

* Handle loading state.
* Handle error state.
* Handle empty state.
* Handle retry where useful.
* Abort or ignore stale requests.
* Do not duplicate fetch logic.
* Do not put fake mock data in production paths.
* Do not hide API failures.
* Do not make unnecessary network requests.
* Do not fetch in client components if server-side fetching is already the project pattern.

---

## 11. Form Rules

Forms must be reliable.

* Use controlled or well-managed form state.
* Validate input.
* Show field-level errors.
* Handle submit loading state.
* Prevent double submit.
* Preserve user input after errors.
* Handle server errors.
* Make forms keyboard accessible.
* Do not store invalid data silently.

---

## 12. Error Handling Rules

Never ignore errors.

Bad:

```ts
try {
  await saveData();
} catch {}
```

Good:

```ts
try {
  await saveData();
} catch (error) {
  logger.error("Failed to save data", getSafeErrorMessage(error));
  setState({ status: "error", message: "Could not save changes." });
}
```

Rules:

* Show user-safe error messages.
* Log useful developer details safely.
* Do not leak secrets.
* Do not crash entire UI for recoverable errors.
* Use error boundaries where appropriate.

---

## 13. Testing Rules

Every behavior change needs tests.

Use tests that verify user-visible behavior, not implementation details.

Prefer:

* React Testing Library
* Vitest/Jest
* Playwright for E2E
* user-event for interactions

Test:

1. Loading state
2. Empty state
3. Error state
4. Success state
5. User interactions
6. Form validation
7. Disabled states
8. Keyboard behavior
9. Important responsive behavior
10. Regression cases for bugs fixed

Prefer:

```ts
screen.getByRole("button", { name: /save/i });
screen.getByLabelText(/email/i);
await user.click(button);
```

Avoid:

```ts
container.querySelector(".random-class");
expect(component.state).toBe(...);
```

Do not write useless tests like:

```ts
it("renders", () => {});
```

Tests must prove behavior.

---

## 14. Required Verification Commands

Before final response, run relevant commands.

Default commands:

```bash
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

For apps with E2E tests:

```bash
pnpm e2e
```

For formatting:

```bash
pnpm format:check
```

If the project uses npm/yarn/bun, use the existing package manager.

Do not claim checks passed unless they actually passed.

If a command fails, report:

1. Which command failed
2. Why it failed
3. Whether it is related to your changes
4. What was fixed
5. What remains unresolved

---

## 15. Dependency Rules

Do not add dependencies casually.

Before adding a package, check:

1. Is there already a project utility for this?
2. Can the platform solve it?
3. Is the package maintained?
4. Is the bundle impact acceptable?
5. Does it create security risk?
6. Is it actually necessary?

Do not edit `package.json` or lockfiles unless required.

---

## 16. File Change Rules

Make the smallest safe diff.

For normal tasks:

* Max 3-7 files changed where possible
* No unrelated formatting
* No unrelated refactors
* No renaming unless needed
* No moving files unless needed
* No changing public APIs unless needed

If more files are required, explain why.

---

## 17. Refactoring Rules

Refactoring must preserve behavior.

Allowed refactors:

* Extract repeated UI
* Extract pure helper functions
* Improve naming
* Split large components
* Remove duplication
* Improve type safety
* Improve testability

Not allowed:

* Changing behavior silently
* Rewriting entire modules for style
* Replacing working architecture without reason
* Mixing refactor with unrelated feature work

For large refactors:

1. Add characterization tests first
2. Refactor in small steps
3. Verify behavior stayed same

---

## 18. Performance Rules

Do not optimize blindly.

Focus on real problems:

* unnecessary rerenders in heavy components
* expensive calculations on every render
* large bundle imports
* unnecessary client-side fetching
* unoptimized images
* large lists without virtualization
* layout shift
* blocking main thread work

Do not add `useMemo` and `useCallback` everywhere.
Use them only when they solve a real issue.

---

## 19. Code Review Checklist

Before final answer, review your diff for:

* Type errors
* Broken imports
* Dead code
* Unused variables
* Bad naming
* Large components
* Missing states
* Accessibility issues
* Weak tests
* Security issues
* Bundle bloat
* Inconsistent Tailwind classes
* Unrelated file changes
* Hidden behavior changes

Fix issues before final response.

---

## 20. AI Behavior Rules

The AI must be honest.

Do not say:

* “production-ready” without checks
* “fully tested” without tests
* “secure” without explaining what was protected
* “done” if build/tests failed
* “minor change” if many files changed

When unsure:

* inspect existing code
* check official docs
* follow repo patterns
* state uncertainty clearly

Do not guess important API behavior.

---

## 21. Prompt Protocol for Big Tasks

For big tasks, split into phases.

Example:

```txt
Phase 1: Read code and create plan only.
Phase 2: Add types and data layer.
Phase 3: Add UI.
Phase 4: Add tests.
Phase 5: Polish accessibility and edge cases.
Phase 6: Run verification and self-review.
```

Never implement a large feature in one uncontrolled response.

---

## 22. Good Final Response Format

Every final response must include:

```txt
Summary:
- What changed

Files changed:
- file path: reason

Tests/checks run:
- command: result

Tests added/updated:
- test file: coverage

Risks/edge cases:
- remaining concerns

Not changed:
- anything intentionally left untouched
```

---

## 23. Master Instruction

Always optimize for:

1. Correctness
2. Maintainability
3. Type safety
4. Accessibility
5. Test coverage
6. Security
7. Small diffs
8. Consistency with existing code
9. Production reliability
10. Honest reporting

Never optimize for looking impressive.

Good production code is boring, clear, tested, typed, accessible, and easy to review.

````

Best usage: keep this as repo guidance, then give task prompts like:

```txt
Follow react_typescript.md strictly.

Task:
[describe exact task]

Before coding, inspect the repo and give a minimal plan.
Do not edit unrelated files.
Run typecheck, lint, tests, and build before final response.
````
