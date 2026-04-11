# DB-2: SQL Injection in count_recent_for_user

- **Phase:** critical
- **Priority:** P1 (Critical)
- **Status:** DONE
- **Depends on:** None

## Problem

In `repositories/magic_link.py:70–83`, `count_recent_for_user` casts `within_seconds` to `str` and uses it in `($2 || ' seconds')::interval` — string concatenation inside the SQL expression. Although the Python type hint is `int`, there is no runtime enforcement. If a non-integer value reaches this code path, it becomes a live SQL injection vector inside the interval expression.

## Approach

1. Replace `($2 || ' seconds')::interval` with `$2 * interval '1 second'` (or `make_interval(secs => $2)`).
2. Remove the `str(within_seconds)` cast — pass `within_seconds` as a native `int`.
3. asyncpg will bind it as a numeric parameter with no string interpolation.

## Files

- `repositories/magic_link.py:70–83` — rewrite the SQL query and remove `str()` cast

## Implementation Notes

- **Related task:** This is the same issue as `tasks/backend/security-1_sql-interval-injection.md`. The fix is in the same file and same lines — completing one completes the other. Do not fix twice.
- The `$2 * interval '1 second'` pattern is the idiomatic PostgreSQL approach for parameterized intervals.
- No migration needed — this is a query-level change only.
