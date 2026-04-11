# DB-9: Duplicate Filter-Building Logic Between find_by_user and count_by_user

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

`find_by_user` (lines 102–147) and `count_by_user` (lines 276–308) in `repositories/job_result.py` independently rebuild identical `conditions`/`params` arrays. A new filter column must be added in two places and can silently diverge, causing mismatched counts vs. actual results returned.

## Approach

Extract a private helper method `_build_filter`:

```python
def _build_filter(
    self,
    user_id: UUID,
    status: str | None = None,
    min_score: int | None = None,
    platform: str | None = None,
) -> tuple[str, list, int]:
    conditions = ["user_id = $1"]
    params: list = [user_id]
    idx = 2
    if status is not None:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1
    if min_score is not None:
        conditions.append(f"score >= ${idx}")
        params.append(min_score)
        idx += 1
    if platform is not None:
        conditions.append(f"platform = ${idx}")
        params.append(platform)
        idx += 1
    return " AND ".join(conditions), params, idx
```

The helper returns the next available parameter index so `find_by_user` can append LIMIT/OFFSET or cursor params.

## Files

- `repositories/job_result.py:102–147` — refactor `find_by_user` to use `_build_filter`
- `repositories/job_result.py:276–308` — refactor `count_by_user` to use `_build_filter`

## Implementation Notes

- This is a pure refactor — no behavior change. Existing tests should pass without modification.
- Consider returning a small dataclass or named tuple instead of a raw tuple for clarity.
