# CR-3 + CR-4: Cross-User Job Ownership Gap in Job Lists (Add and Remove)

- **Phase:** security
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

In `api/routes/api_lists.py:123-154`, both `add_job` (line 135) and `remove_job` (line 151) verify that the list belongs to the current user, but neither verifies that the `job_result_id` also belongs to that user. This means:

- **Add:** A user can add another user's job result UUIDs into their own list, confirming that those results exist (information leak via timing/error difference).
- **Remove:** Same gap — the delete targets a `job_result_id` without scoping to the user.

## Approach

1. Modify `JobListRepository.add_job` (in `repositories/job_list.py:104-117`) to accept a `user_id` parameter and join against `job_results` to verify ownership:
   ```sql
   INSERT INTO job_list_items (list_id, job_result_id)
   SELECT $1, $2
   WHERE EXISTS (SELECT 1 FROM job_results WHERE id = $2 AND user_id = $3)
   ON CONFLICT (list_id, job_result_id) DO NOTHING
   RETURNING list_id
   ```
2. Modify `JobListRepository.remove_job` (in `repositories/job_list.py:119-131`) similarly:
   ```sql
   DELETE FROM job_list_items
   WHERE list_id = $1 AND job_result_id = $2
     AND EXISTS (SELECT 1 FROM job_results WHERE id = $2 AND user_id = $3)
   RETURNING list_id
   ```
3. Update the route handlers in `api_lists.py` to pass `user.id` to both repository methods.

## Files

- `repositories/job_list.py:104-131` — add `user_id` parameter to `add_job` and `remove_job`, scope queries
- `api/routes/api_lists.py:135` — pass `user.id` to `repo.add_job`
- `api/routes/api_lists.py:151` — pass `user.id` to `repo.remove_job`

## Implementation Notes

- When `add_job` returns `False` (no row returned) because the job_result doesn't belong to the user, the API should return 404 "Job result not found" — do not distinguish between "doesn't exist" and "belongs to another user" to avoid enumeration.
- Add tests: create two users, user A's job result, user B's list, and verify user B cannot add user A's job result.
