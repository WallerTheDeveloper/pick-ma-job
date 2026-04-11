# DB-6: pipeline_run update_status Has No user_id Scope

- **Phase:** high
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

`PipelineRunRepository.update_status(run_id, status, ...)` in `repositories/pipeline_run.py:60–81` updates by `run_id` alone with no `user_id` in the WHERE clause. If `run_id` is ever user-supplied or guessable, any user can overwrite any run's status, result, or error fields. Every other mutating method in the codebase scopes by `user_id` — this is an inconsistency.

## Approach

1. Add `user_id: UUID` as a required parameter to `update_status`.
2. Add `AND user_id = $n` to the WHERE clause.
3. Return a boolean or row count so callers can detect when no row was updated.
4. Update all callers (`services/pipeline.py`, `services/run_manager.py`) to pass `user_id`.

## Files

- `repositories/pipeline_run.py:60–81` — add `user_id` parameter and scope the UPDATE
- `services/pipeline.py` — pass `user_id` when calling `update_status`
- `services/run_manager.py` — pass `user_id` when calling `update_status`

## Implementation Notes

- Callers already have `user_id` available in context — threading it through is straightforward.
- Consider returning `RETURNING id` so callers can verify the update matched a row.
- This is defense-in-depth — even if `run_id` is only set internally today, the repository should enforce user isolation regardless.
