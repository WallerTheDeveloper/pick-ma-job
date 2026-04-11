# P4-1: Job Lists (Named Collections)

- **Phase:** 4 — Features
- **Priority:** P3 — Enhancement
- **Status:** DONE
- **Depends on:** None

## Problem

Users want to organize job results into named collections (e.g., "Top Picks", "Saved for Later", "Interview Stage"). Currently there is no way to group or categorize jobs beyond the `status` field (new/applied/dismissed).

## Scope

### Database

New tables:

```sql
job_lists (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT now()
)

job_list_items (
  list_id       UUID NOT NULL REFERENCES job_lists(id) ON DELETE CASCADE,
  job_result_id UUID NOT NULL REFERENCES job_results(id) ON DELETE CASCADE,
  added_at      TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (list_id, job_result_id)
)
```

### API Endpoints

```
GET    /api/lists                     — list all user's job lists
POST   /api/lists                     — create a new list { name }
DELETE /api/lists/{list_id}           — delete a list (and its items)
PATCH  /api/lists/{list_id}           — rename a list { name }

GET    /api/lists/{list_id}/jobs      — get jobs in a list
POST   /api/lists/{list_id}/jobs      — add a job { job_result_id }
DELETE /api/lists/{list_id}/jobs/{job_result_id}  — remove a job from a list
```

### Frontend

- **List manager** — sidebar or modal to create/rename/delete lists
- **"Add to list" action** — dropdown on each job row (in results table) to pick a list
- **List view** — filter results by list (e.g., click list name to see only those jobs)

## Files

- `repositories/` — new `job_list.py` repository
- `services/` — new `list_service.py` or inline in API routes (simple enough)
- `api/routes/` — new `api_lists.py`
- `api/schemas.py` — new `JobList` and `JobListItem` Pydantic schemas
- `main.py` — register new router
- `frontend/src/api/` — new `lists.ts` API client
- `frontend/src/hooks/` — new `use-lists.ts` TanStack Query hooks
- `frontend/src/pages/results.tsx` — "Add to list" action per row
- `frontend/src/components/` — `ListManager` component, `AddToListMenu` component

## Acceptance Criteria

- [x] User can create a named list
- [x] User can rename and delete a list
- [x] User can add any job result to one or more lists
- [x] User can remove a job from a list
- [x] User can view all jobs in a specific list
- [x] Deleting a list does not delete the underlying job results
- [x] All list operations are scoped to the authenticated user (no cross-user access)
- [x] Existing `status` field (new/applied/dismissed) is unaffected
