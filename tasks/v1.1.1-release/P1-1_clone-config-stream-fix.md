# P1-1: Fix "Body Stream Already Read" Error on Clone Search Config

- **Phase:** 1 — Bug Fix
- **Priority:** P1 — Critical Bug
- **Status:** DONE
- **Depends on:** None

## Problem

When a user tries to create a new search config from an existing one ("start from existing"), the UI shows a toast:

> Failed to execute 'text' on 'Response': body stream already read

The backend returns a `500 Internal Server Error` for `POST /api/search-configs`. The stack trace points to `client.ts:59` → `createSearchConfig` in `search-config.ts` → `handleSubmit` in `search-config.tsx`.

The error `body stream already read` indicates the `Response` body is being consumed twice — once in an error-handling branch and again for the success payload — in the `api()` fetch wrapper in `client.ts`.

## Solution

### Frontend

1. **`frontend/src/api/client.ts`** — audit the `api()` wrapper:
   - Find any place where `response.text()` or `response.json()` is called more than once on the same `Response` object.
   - Fix by reading the body once into a variable, then branching on status code.
   - Example pattern:
     ```ts
     const text = await response.text();
     if (!response.ok) {
       throw new Error(text);
     }
     return JSON.parse(text);
     ```

2. **`frontend/src/api/search-config.ts`** — verify `createSearchConfig` passes the payload correctly and does not re-read the response.

3. **`frontend/src/pages/search-config.tsx`** — verify `handleSubmit` clone logic constructs the payload correctly (no stale reference to a previous response object).

### Backend

4. **`api/routes/api_search_config.py`** — check `POST /api/search-configs` handler for any unhandled exception that could cause a 500. Confirm the route correctly handles a `clone_from` / existing config payload shape.

## Files

- `frontend/src/api/client.ts`
- `frontend/src/api/search-config.ts`
- `frontend/src/pages/search-config.tsx`
- `api/routes/api_search_config.py`

## Acceptance Criteria

- [ ] Cloning an existing search config succeeds without a toast error
- [ ] `POST /api/search-configs` returns `200`/`201` for a valid clone payload
- [ ] No `body stream already read` error in the browser console
- [ ] Creating a brand-new config (not from existing) still works correctly
