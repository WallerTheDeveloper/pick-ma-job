# CR-14: getCsrfToken Doesn't decodeURIComponent

- **Phase:** cleanup
- **Priority:** P4 (Low)
- **Status:** DONE
- **Depends on:** None

## Problem

In `frontend/src/api/client.ts:5-9`, the `getCsrfToken` function reads the CSRF token from `document.cookie` by splitting on `=`, but does not call `decodeURIComponent` on the extracted value. Cookie values set by the server may be percent-encoded by the browser. In practice, CSRF tokens are hex/base64 characters that don't get encoded, but this is fragile.

## Approach

Wrap the return value with `decodeURIComponent`:

```typescript
return match ? decodeURIComponent(match.split("=")[1]) : undefined;
```

## Files

- `frontend/src/api/client.ts:9` — add `decodeURIComponent` wrapper

## Implementation Notes

- This is a defensive fix. The current CSRF token is generated via `hmac.hexdigest()` which produces only hex characters (`[0-9a-f]`), so encoding never occurs in practice.
- The fix has zero risk and makes the code correct for any future token format.
