# CR-2: ORDER BY SQL Injection Pattern in job_result.py

- **Phase:** security
- **Priority:** P1 (Critical)
- **Status:** DONE
- **Depends on:** None

## Problem

In `repositories/job_result.py:133-143`, the ORDER BY clause is built from a raw string dict lookup (`ORDER BY {order}`). The `_SORT_CLAUSES` dict on lines 95-100 acts as an allowlist, but if the `sort` parameter does not match any key, the `.get()` fallback still returns a valid clause — the issue is that `_SORT_CLAUSES` is a mutable class attribute that could be modified externally, and there is no runtime assertion that the resolved value is actually in the known safe set.

## Approach

1. Move `_SORT_CLAUSES` to a module-level constant annotated with `Final` (see also hardening-4).
2. Add a runtime assertion before the f-string interpolation: `assert sort in _SORT_CLAUSES, f"Unknown sort: {sort}"`.
3. Alternatively, raise a `ValueError` instead of assert, since asserts can be stripped with `-O`.

## Files

- `repositories/job_result.py:95-100` — move to module-level `Final` constant
- `repositories/job_result.py:133` — add runtime validation before use in query

## Implementation Notes

- This task overlaps with hardening-4 for the `Final` annotation. If both are done, coordinate to avoid duplicate changes — ideally implement both in the same PR.
- The `.get()` fallback on line 133 means an unknown `sort` value silently falls back to `score_desc`. After adding the assertion, unknown values will raise immediately — which is the correct behavior.
- Consider validating `sort` at the API layer as well (Pydantic `Literal` type on the query param).
