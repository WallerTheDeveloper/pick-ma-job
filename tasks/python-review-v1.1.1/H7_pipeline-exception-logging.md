# H7: Add exc_info=True to Bare Exception Handlers in Pipeline

- **Phase:** High
- **Priority:** P1 — Debuggability
- **Status:** DONE
- **Depends on:** None

## Problem

`services/pipeline.py:222–227` and `247–250` catch `except Exception` and append an error message to a list, but never log the full stack trace. When an evaluation fails in production, the error entry contains only a string like `"Evaluation failed for 'Job Title': SomeError: message"` — the stack trace that shows *where* the exception originated is lost.

## Solution

**`services/pipeline.py`** — add `exc_info=True` to all `except Exception` log calls in the pipeline loop:

```python
except Exception as exc:
    logger.error(
        "Evaluation failed for '%s': %s",
        job.title,
        exc,
        exc_info=True,   # ← adds full traceback to log
    )
    errors.append(f"Evaluation failed for '{job.title}': {type(exc).__name__}: {exc}")
```

Also include the exception type name in the error string appended to `errors` so it surfaces in the run status response.

## Files

- `services/pipeline.py`

## Acceptance Criteria

- [ ] All `except Exception` blocks in the pipeline evaluation loop log with `exc_info=True`
- [ ] The error string appended to `errors` includes the exception class name
- [ ] Full stack traces appear in application logs when an evaluation fails
- [ ] No behaviour change — failed jobs are still skipped and the run continues
