# H5: Add Zod Schema Validation to `requestMagicLink`

- **Phase:** High
- **Priority:** P1 — Type Safety at API Boundary
- **Status:** DONE
- **Depends on:** None

## Problem

`frontend/src/api/auth.ts:12` calls `api()` without passing a Zod schema as the third argument:

```ts
export async function requestMagicLink(email: string): Promise<OkResponse> {
  return api("/auth/magic-link", {
    method: "POST",
    body: { email },
  });
}
```

The `api()` base client falls through to `return json as T` — a bare cast with zero runtime validation. The `okResponseSchema` is imported in the same file but only used by `logout`. If the backend returns an unexpected shape (e.g., a new field, a renamed field, or a malformed success response), the caller receives silently wrong data with no type error.

The `magicLinkErrorResponseSchema` is defined in `types/schemas.ts` but is never used by any consumer.

## Solution

Pass `okResponseSchema` as the third argument to `api()`, matching the pattern used in `logout`:

```ts
export async function requestMagicLink(email: string): Promise<OkResponse> {
  return api("/auth/magic-link", { method: "POST", body: { email } }, okResponseSchema);
}
```

Also verify that `magicLinkErrorResponseSchema` is either used or removed if redundant.

## Files

- `frontend/src/api/auth.ts`
- `frontend/src/types/schemas.ts` (check `magicLinkErrorResponseSchema` usage)

## Acceptance Criteria

- [ ] `requestMagicLink` passes `okResponseSchema` (or an appropriate schema) as the third argument to `api()`
- [ ] The response is validated at runtime; a malformed backend response throws a typed error rather than silently casting
- [ ] `magicLinkErrorResponseSchema` is either used in an error handler or removed to avoid dead code
- [ ] TypeScript compiles without errors
