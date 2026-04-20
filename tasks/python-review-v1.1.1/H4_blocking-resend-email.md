# H4: Fix Blocking Synchronous resend.Emails.send Inside Async Method

- **Phase:** High
- **Priority:** P1 — Event Loop Blocking
- **Status:** DONE
- **Depends on:** None

## Problem

`services/auth.py:116` calls `resend.Emails.send(...)` — the Resend SDK's **synchronous** HTTP client — directly inside an `async def` method. This blocks the asyncio event loop for the entire duration of the HTTP request, freezing all other coroutines (including other users' requests) until the email send completes or times out.

Under any meaningful concurrent load, magic link requests stall the entire application.

## Solution

Wrap the synchronous call with `asyncio.to_thread` to run it in a thread pool without blocking the event loop:

```python
import asyncio

await asyncio.to_thread(resend.Emails.send, {
    "from": self._email_from,
    "to": [email],
    "subject": "Your magic link",
    "html": f'<a href="{magic_url}">Sign in</a>',
})
```

If the Resend SDK ever ships an async client, migrate to that instead.

## Files

- `services/auth.py`

## Acceptance Criteria

- [ ] `resend.Emails.send` is called via `asyncio.to_thread` (or equivalent non-blocking wrapper)
- [ ] The event loop is not blocked during email delivery
- [ ] Email sending errors are still propagated and logged correctly
- [ ] Magic link flow works end-to-end after the change
