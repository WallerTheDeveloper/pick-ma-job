# FE-5: getCsrfToken Truncates Cookie Values Containing `=`

- **Phase:** fixes
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

`src/api/client.ts:8` uses `match?.split("=")[1]` to extract the CSRF token from the cookie string. If the token value contains `=` characters (common in base64-encoded tokens), everything after the first `=` is silently dropped, sending a truncated token that fails validation on the backend.

## Approach

Replace the split logic to preserve the full value:

```ts
function getCsrfToken(): string | undefined {
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${CSRF_COOKIE}=`));
  return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : undefined;
}
```

## Files

- `frontend/src/api/client.ts:5–9` — fix cookie value extraction

## Implementation Notes

- `decodeURIComponent` handles URL-encoded cookie values correctly.
- This is the same bug pattern as the backend task `cleanup-2_csrf-cookie-decode.md`. Both should be fixed together.
