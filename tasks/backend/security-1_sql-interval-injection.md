# CR-1: SQL Interval Injection in magic_link.py

- **Phase:** security
- **Priority:** P1 (Critical)
- **Status:** DONE
- **Depends on:** None

## Problem

In `repositories/magic_link.py:78`, the SQL query builds an interval using string concatenation: `($2 || ' seconds')::interval`. The `within_seconds` parameter is explicitly cast to `str` on line 81 before being passed as a parameterized argument. Although the Python type hint is `int`, there is no runtime enforcement. If a non-integer value ever reaches this code path, it becomes a SQL injection vector inside the interval expression.

## Approach

1. Replace the `($2 || ' seconds')::interval` expression with `$2 * interval '1 second'`.
2. Pass `within_seconds` as an `int` directly (remove the `str()` cast on line 81).
3. This keeps the value as a parameterized integer, eliminating any injection surface.

## Files

- `repositories/magic_link.py:73-82` — rewrite the SQL query and remove `str()` cast

## Implementation Notes

- The `$2 * interval '1 second'` pattern is the idiomatic PostgreSQL approach for parameterized intervals.
- Verify the query still works by running the existing test suite for `count_recent_for_user`.
- No migration needed — this is a query-level change only.
