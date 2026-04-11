# DB-14: list_users_with_stats Has No LIMIT

- **Phase:** improvements
- **Priority:** P4 (Low)
- **Status:** DONE
- **Depends on:** None

## Problem

`UserRepository.list_users_with_stats()` in `repositories/user.py:75–97` returns all users with a LEFT JOIN and GROUP BY, with no pagination. This query becomes increasingly expensive and memory-heavy as the user base grows.

## Approach

1. Add `limit: int = 100` and `offset: int = 0` parameters to `list_users_with_stats`.
2. Append `LIMIT $1 OFFSET $2` to the query.
3. Add a `count_users() -> int` method for total count display.
4. Update the admin API route to accept and pass pagination parameters.

## Files

- `repositories/user.py:75–97` — add `limit`/`offset` parameters
- `api/routes/api_admin.py` — accept pagination query params, return total count

## Implementation Notes

- OFFSET pagination is acceptable here — the admin user list is low-traffic and unlikely to reach thousands of pages.
- The LEFT JOIN with GROUP BY is expensive at scale — consider caching or materializing job counts if this becomes a bottleneck.
