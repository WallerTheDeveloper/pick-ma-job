# DB-7: Invalid Sort Keys Silently Fall Back Instead of Raising

- **Phase:** high
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

In `repositories/job_result.py:133`, `_SORT_CLAUSES.get(sort, fallback)` silently falls back to `score_desc` for unknown sort values. This masks bugs in callers — a typo or invalid user input silently produces unexpected sort order instead of failing fast.

## Approach

1. Replace the `dict.get()` fallback with an explicit check:
   ```python
   if sort not in _SORT_CLAUSES:
       raise ValueError(f"Unknown sort key: {sort!r}")
   order = _SORT_CLAUSES[sort]
   ```
2. Validate the `sort` parameter at the API route level before it reaches the repository (return 422 for invalid values).
3. Consider using a `Literal` type hint: `sort: Literal["score_desc", "score_asc", "date_desc", "date_asc"]`.

## Files

- `repositories/job_result.py:133` — replace `dict.get()` fallback with explicit `ValueError`
- `api/routes/api_results.py` — validate `sort` at the route level

## Implementation Notes

- The `ValueError` at the repository level is a developer safety net — it should never reach production if the API route validates properly.
- The API route should return a 422 with a message listing valid sort options.
