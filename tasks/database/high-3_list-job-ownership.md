# DB-5: add_job and remove_job Don't Verify List/Job Ownership

- **Phase:** high
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

`add_job(list_id, job_result_id)` and `remove_job(list_id, job_result_id)` in `repositories/job_list.py:104–131` insert/delete with no ownership check on either the list or the job result. A user can add another user's job results into any list. Ownership enforcement must live at the repository level, not only the service layer.

## Approach

1. Add `user_id: UUID` as a third parameter to both methods.
2. For `add_job`, use a CTE guard:
   ```sql
   WITH owned_list AS (SELECT id FROM job_lists WHERE id = $1 AND user_id = $3),
        owned_job  AS (SELECT id FROM job_results WHERE id = $2 AND user_id = $3)
   INSERT INTO job_list_items (list_id, job_result_id)
   SELECT $1, $2 FROM owned_list, owned_job
   ON CONFLICT (list_id, job_result_id) DO NOTHING
   RETURNING list_id
   ```
3. For `remove_job`, scope the DELETE:
   ```sql
   DELETE FROM job_list_items
   WHERE list_id = $1 AND job_result_id = $2
     AND list_id IN (SELECT id FROM job_lists WHERE id = $1 AND user_id = $3)
   RETURNING list_id
   ```
4. Update route handlers in `api/routes/api_lists.py` to pass `user.id`.

## Files

- `repositories/job_list.py:104–131` — add `user_id` parameter, scope queries
- `api/routes/api_lists.py:135` — pass `user.id` to `add_job`
- `api/routes/api_lists.py:151` — pass `user.id` to `remove_job`

## Implementation Notes

- **Related task:** Same issue as `tasks/backend/security-3_cross-user-job-list-ownership.md`. Both fix the same code paths — complete together.
- When ownership check fails, return 404 "Job result not found" — don't distinguish "doesn't exist" from "belongs to another user" to prevent enumeration.
- Add a cross-user test: two users, verify user B cannot add user A's job result to user B's list.
