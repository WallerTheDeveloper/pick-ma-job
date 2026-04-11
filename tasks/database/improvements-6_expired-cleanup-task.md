# DB-13: No Scheduled Cleanup for Expired Sessions and Magic Links

- **Phase:** improvements
- **Priority:** P4 (Low)
- **Status:** DONE
- **Depends on:** None

## Problem

`delete_expired()` methods exist on both `SessionRepository` (line 70) and `MagicLinkRepository` (line 93) but nothing calls them. Expired rows accumulate indefinitely, bloating tables and degrading index performance on token lookups over time.

## Approach

Add a periodic cleanup task in the FastAPI lifespan function:

```python
async def _cleanup_loop(session_repo: SessionRepository, magic_link_repo: MagicLinkRepository) -> None:
    while True:
        await asyncio.sleep(3600)  # run every hour
        try:
            sessions_deleted = await session_repo.delete_expired()
            links_deleted = await magic_link_repo.delete_expired()
            logger.info("Cleanup: deleted %d sessions, %d magic links", sessions_deleted, links_deleted)
        except Exception:
            logger.exception("Cleanup task failed")
```

Launch as `asyncio.create_task` in the lifespan startup, cancel on shutdown.

## Files

- `main.py` — add cleanup task to lifespan function
- `repositories/session.py:70` — verify `delete_expired` returns row count
- `repositories/magic_link.py:93` — verify `delete_expired` returns row count

## Implementation Notes

- The cleanup task should be fire-and-forget — failures should be logged but not crash the app.
- An admin endpoint (`POST /api/admin/cleanup`) is an alternative approach and allows manual triggers.
- Both approaches can coexist: background loop for normal cleanup, admin endpoint for manual triggers.
