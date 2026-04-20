# M3: Gate `console.error` Behind Dev Mode in API Client

- **Phase:** Medium
- **Priority:** P2 — Production Hygiene
- **Status:** DONE
- **Depends on:** None

## Problem

`frontend/src/api/client.ts:88` logs a `console.error` unconditionally in all environments:

```ts
console.error("Response validation failed:", error, "Raw response:", json);
```

This fires in production builds whenever a Zod schema validation fails on an API response. It leaks internal schema structure, raw API response payloads, and Zod error details to the browser console — visible to any user who opens DevTools.

For comparison, the `console.warn` at line 53 is already correctly gated behind `import.meta.env.DEV`.

## Solution

Apply the same `DEV` guard to the `console.error`:

```ts
if (import.meta.env.DEV) {
  console.error("Response validation failed:", error, "Raw response:", json);
}
```

In production, schema validation failures should still throw (so the error surfaces via the app's error handling / toast system), but raw response data should not be logged to the console.

## Files

- `frontend/src/api/client.ts`

## Acceptance Criteria

- [ ] The `console.error` at line 88 is wrapped in `import.meta.env.DEV`
- [ ] Schema validation failures still throw in production (the error is not swallowed)
- [ ] In development mode, the error and raw response are still logged for debugging
- [ ] TypeScript compiles without errors
