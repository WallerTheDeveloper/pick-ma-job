# FE-2: Non-null Assertion on getElementById Without Guard

- **Phase:** fixes
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

`createRoot(document.getElementById("root")!).render(...)` in `main.tsx` uses a non-null assertion. If the `#root` element is missing (e.g., misconfigured HTML), the app crashes with an unhelpful `Cannot read properties of null` error instead of a clear message.

## Approach

Replace the `!` assertion with an explicit null check that throws a descriptive error:

```ts
const root = document.getElementById("root");
if (!root) {
  throw new Error("Root element #root not found in document");
}
createRoot(root).render(...);
```

## Files

- `frontend/src/main.tsx:6` — add null guard before createRoot

## Implementation Notes

- Trivial change, no risk of regression.
