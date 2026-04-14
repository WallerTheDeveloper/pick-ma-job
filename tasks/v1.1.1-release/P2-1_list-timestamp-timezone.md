# P2-1: Fix Job List Timestamp Not Matching User's Local Time

- **Phase:** 2 — Bug Fix
- **Priority:** P2 — Enhancement / Bug
- **Status:** DONE
- **Depends on:** None

## Problem

When a new job list is created (manually or auto-created after a pipeline run), the displayed timestamp does not match the user's actual local time. The list `created_at` is stored in UTC in the database but is displayed without being converted to the browser's local timezone.

## Solution

### Backend

The API should already return `created_at` as an ISO 8601 UTC string (e.g., `"2026-04-14T10:30:00Z"`). No backend changes expected — verify this is the case.

1. **`api/schemas.py`** — confirm `JobListResponse` (or equivalent schema) serializes `created_at` as a UTC ISO string with timezone info (`datetime` with `tzinfo`).
2. **`repositories/job_list.py`** — confirm `created_at` is returned as a timezone-aware `datetime` object (not naive).

### Frontend

3. **Find where list timestamps are rendered** (likely `frontend/src/pages/` lists page or a list card component).
4. Replace raw date string display with a locale-aware formatter:
   ```ts
   new Date(createdAt).toLocaleString()
   // or with explicit options:
   new Date(createdAt).toLocaleString(undefined, {
     dateStyle: 'medium',
     timeStyle: 'short',
   })
   ```
5. Apply the same fix to any other place in the frontend that displays `created_at` for lists (e.g., list detail page, pipeline run result toast linking to the list).

## Files

- `api/schemas.py`
- `repositories/job_list.py`
- Frontend list display component(s) — identify during implementation

## Acceptance Criteria

- [x] Created list timestamp matches the user's local clock time
- [x] Timestamp correctly reflects DST and timezone offset
- [x] Fix applies to all places in the UI where list `created_at` is shown
- [x] No change to how timestamps are stored in the database (UTC stays canonical)
