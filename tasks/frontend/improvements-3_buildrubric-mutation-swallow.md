# FE-11: buildRubric Silently Swallows JSON Parse Errors and Mutates in Place

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** TODO
- **Depends on:** None

## Problem

In `src/pages/profile.tsx:68-76`, `buildRubric` uses `Object.assign(rubric, extra)` which mutates the `rubric` object in place, and wraps the JSON parse in a silent `catch {}` that swallows errors. This violates immutability principles and hides user input errors.

## Approach

1. Replace `Object.assign(rubric, extra)` with an immutable spread: `return { ...rubric, ...extra }`.
2. Remove the silent catch. Instead, let the JSON parse error propagate so the caller can show a toast or validation message.
3. Ensure the call site in `handleSubmit` has proper error handling before removing the catch.

## Files

- `frontend/src/pages/profile.tsx:68–76` — fix buildRubric function

## Implementation Notes

- Ensure the caller of `buildRubric` has proper error handling before removing the catch.
- Consider validating the parsed JSON against a Zod schema for the rubric shape.
