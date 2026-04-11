# FE-3: API Responses Cast but Never Zod-Validated

- **Phase:** fixes
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

`src/api/client.ts:74` returns `response.json() as Promise<T>` — a type-only assertion with zero runtime validation. The Zod schemas in `src/types/schemas.ts` exist but are never called at runtime. If the backend drifts from the expected shape, properties silently become `undefined`, causing hard-to-trace UI bugs.

## Approach

This is a cross-cutting change affecting all `src/api/` modules:

1. Extend the existing `api<T>` function to accept an optional Zod schema:
   ```ts
   export async function api<T>(
     path: string,
     options: RequestOptions = {},
     schema?: ZodType<T>,
   ): Promise<T> {
     // ... existing fetch logic ...
     const json = await response.json();
     return schema ? schema.parse(json) : (json as T);
   }
   ```
2. Update each API module (`auth.ts`, `results.ts`, `dashboard.ts`, `profile.ts`, `search-config.ts`, `lists.ts`) to pass the corresponding Zod schema from `src/types/schemas.ts`.
3. Ensure Zod parse errors are caught and logged with useful context (endpoint, response shape) rather than crashing silently.

## Files

- `frontend/src/api/client.ts:74` — extend `api<T>` to accept optional Zod schema
- `frontend/src/api/auth.ts` — pass auth schemas
- `frontend/src/api/results.ts` — pass results schemas
- `frontend/src/api/dashboard.ts` — pass dashboard schemas
- `frontend/src/api/profile.ts` — pass profile schemas
- `frontend/src/api/search-config.ts` — pass search config schemas
- `frontend/src/api/lists.ts` — pass list schemas
- `frontend/src/types/schemas.ts` — verify schemas match current API responses; add missing ones

## Implementation Notes

- Making the schema parameter optional allows incremental migration — callers without a schema keep current behavior.
- Add a `console.warn` in development mode when `api()` is called without a schema to track remaining unvalidated calls.
- This is the largest single task in the fixes phase. Consider doing it module-by-module.
