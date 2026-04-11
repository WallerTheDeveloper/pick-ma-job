# DB-3: OFFSET Pagination Degrades on Large Datasets

- **Phase:** high
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

`find_by_user` in `repositories/job_result.py:102–147` uses `LIMIT $n OFFSET $m`. At high page numbers, PostgreSQL scans and discards all preceding rows — performance degrades linearly with page depth. For a SaaS product with potentially thousands of job results per user, this becomes a real bottleneck.

## Approach

Replace OFFSET pagination with keyset (cursor) pagination:
- For `score_desc`: `WHERE (score, id) < ($last_score, $last_id) ORDER BY score DESC, id DESC`
- For `created_at_desc`: `WHERE (created_at, id) < ($last_created_at, $last_id) ORDER BY created_at DESC, id DESC`

1. Update `find_by_user` signature to accept optional `cursor` params instead of `offset`.
2. Update `api/routes/api_results.py` to accept and return cursor values.
3. Update `api/schemas.py` to add cursor fields to the response model.
4. Update frontend `api/results.ts` and `hooks/use-results.ts` to use cursor-based pagination.

The existing composite indexes (`idx_job_results_user_score`, `idx_job_results_user_status`) already support keyset queries.

## Files

- `repositories/job_result.py:102–147` — replace OFFSET with keyset WHERE clauses
- `api/routes/api_results.py` — accept cursor params, return `next_cursor` in response
- `api/schemas.py` — add cursor fields to response model
- `frontend/src/api/results.ts` — update API client
- `frontend/src/hooks/use-results.ts` — switch to cursor-based pagination

## Implementation Notes

- Keyset pagination requires a deterministic sort order — always include `id` as a tiebreaker.
- For `score_desc`, NULL scores need special handling (`NULLS LAST` means null scores sort after non-null).
- `count_by_user` can remain as-is for total count display.
- Consider supporting both OFFSET and cursor modes temporarily during migration, then deprecate OFFSET.
