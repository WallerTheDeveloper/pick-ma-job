# H1: Guard `JSON.parse` Inside `buildRubric`

- **Phase:** High
- **Priority:** P1 — Runtime Crash Risk
- **Status:** DONE
- **Depends on:** None

## Problem

`frontend/src/pages/profile-helpers.ts:66` calls `JSON.parse(r.advanced)` inside `buildRubric` without a try/catch:

```ts
const extra = JSON.parse(r.advanced) as Record<string, unknown>;
```

The caller `validateForm` does perform a parse check before reaching `buildRubric`, so the current happy path is safe. However, `buildRubric` is an exported public function that does not defend itself — any future caller that passes unvalidated data (a test, a refactor, a new code path) will receive an uncaught runtime `SyntaxError` that crashes the page.

## Solution

Wrap the `JSON.parse` call inside `buildRubric` in a try/catch and return a meaningful fallback or throw a typed error:

```ts
let extra: Record<string, unknown>;
try {
  extra = JSON.parse(r.advanced) as Record<string, unknown>;
} catch {
  throw new Error(`Invalid JSON in rubric entry "${r.label}": ${r.advanced}`);
}
```

Alternatively, move validation into `buildRubric` so the function is self-contained and callers don't need to pre-validate.

## Files

- `frontend/src/pages/profile-helpers.ts`

## Acceptance Criteria

- [ ] `buildRubric` handles malformed JSON in `r.advanced` without an uncaught `SyntaxError`
- [ ] An invalid JSON entry produces a clear error message identifying which rubric entry is malformed
- [ ] `validateForm` still performs its own pre-validation (no regression)
- [ ] TypeScript compiles without errors
