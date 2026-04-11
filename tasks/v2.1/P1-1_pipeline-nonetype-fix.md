# P1-1: Fix Pipeline NoneType Error for New Users

- **Phase:** 1 — Critical Bugs
- **Priority:** P0 — Blocking (all non-developer users affected)
- **Status:** DONE
- **Depends on:** None

## Problem

Pipeline fails immediately for any user other than the developer account (`golo7ov.danil@gmail.com`). Clicking "Run Pipeline" returns:

```json
{
  "status": "failed",
  "error": "object of type 'NoneType' has no len()"
}
```

## Root Cause Investigation

The error is almost certainly `profile` being `None` for users who haven't filled out their profile yet, while `services/pipeline.py` calls `len()` on a profile field (e.g., `profile.skills`).

Check in order:

1. **`services/pipeline.py`** — Find every call to `len()` and confirm it handles `None`
2. **`repositories/profile.py`** — Does `get_by_user_id` return `None` when no profile row exists?
3. **`api/deps.py`** — Does the `get_current_user` dependency load the profile, or is profile loaded separately inside the pipeline?
4. **Confirm the trigger** — Add a test user with no profile row, trigger a run, verify the traceback matches

## Files

- `services/pipeline.py` — where the `len()` call likely lives
- `repositories/profile.py` — `get_by_user_id` return value when no row
- `api/routes/api_pipeline.py` — entry point for `POST /api/run`
- `api/deps.py` — dependency injection chain

## Fix

Guard against a missing profile before the pipeline starts. Preferred approach: check at the top of the pipeline execution and raise a clear, user-facing error.

```python
# Example guard in pipeline.py or api_pipeline.py
profile = await profile_repo.get_by_user_id(user_id)
if profile is None:
    raise ValueError("Profile not set up. Please complete your profile before running the pipeline.")
```

Surface the error message in the frontend results/status display.

## Acceptance Criteria

- [x] A user with no profile row gets a clear error: "Please complete your profile before running the pipeline"
- [x] A user with a profile row runs the pipeline successfully
- [x] No `NoneType` exceptions reach the background task handler unhandled
- [x] Error is logged server-side with the user_id for debugging
