# DB-4: Missing Index on job_list_items(job_result_id)

- **Phase:** high
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

The `job_list_items` table has a composite PK of `(list_id, job_result_id)`. The FK `job_result_id -> job_results(id)` has no supporting index. When a job result is deleted, the `ON DELETE CASCADE` triggers a sequential scan on `job_list_items` to find matching rows. The `get_list_ids_for_job` query also filters `WHERE job_result_id = $1` without an index.

## Approach

1. Create a new migration file `db/migrations/003_job_list_items_index.sql`.
2. Add the index:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_job_list_items_job_result_id ON job_list_items(job_result_id);
   ```
3. Add the same index to `db/schema.sql` after the `job_list_items` table definition for new installs.

## Files

- `db/schema.sql:130` — add index after table definition
- `db/migrations/003_job_list_items_index.sql` — new migration file

## Implementation Notes

- `CREATE INDEX IF NOT EXISTS` is safe to run on a live database with no downtime risk (PostgreSQL builds it non-blocking if `CONCURRENTLY` is added).
- The index will be used by both the FK cascade on deletion and the `get_list_ids_for_job` lookup.
