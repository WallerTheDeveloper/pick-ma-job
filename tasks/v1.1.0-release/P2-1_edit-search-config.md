# P2-1: Edit Existing Search Configs

- **Phase:** 2 — Search Config Editing
- **Priority:** P1 — Core Feature
- **Status:** DONE
- **Depends on:** None

## Problem

Users can create a search config but cannot edit it after the fact. The only workaround is to delete and recreate, which is disruptive. A standard edit flow is required.

## Scope

### Backend

1. **`repositories/search_config.py`** — add `update(config_id, user_id, query, filters) -> SearchConfigRow | None` using `UPDATE ... WHERE id=$1 AND user_id=$2 RETURNING *`. Returns `None` if not found or not owned.
2. **`services/search_config.py`** — add `update(user_id, config_id, data)` with the same validation as `create`. Platform is immutable on update — reject any attempt to change it.
3. **`api/schemas.py`** — add `SearchConfigUpdateRequest(query: str, filters: dict)`.
4. **`api/routes/api_search_config.py`** — add `PUT /api/search-configs/{config_id}`, CSRF-protected. Return 404 if config not found or not owned by current user, 422 on validation error.

### Frontend

5. **`frontend/src/api/search-config.ts`** — add `updateSearchConfig(id, body)` calling `PUT /api/search-configs/{id}`.
6. **`frontend/src/hooks/use-search-config.ts`** — add `useUpdateSearchConfig` mutation with query invalidation on success.
7. **`frontend/src/pages/search-config.tsx`** — add "Edit" button per config row. Clicking it opens the existing create form pre-populated with current values (`editingId` state). On submit → `PUT`. Reset form state when switching between edit/create modes.

## Files

- `repositories/search_config.py`
- `services/search_config.py`
- `api/schemas.py`
- `api/routes/api_search_config.py`
- `frontend/src/api/search-config.ts`
- `frontend/src/hooks/use-search-config.ts`
- `frontend/src/pages/search-config.tsx`

## Acceptance Criteria

- [ ] `PUT /api/search-configs/{id}` updates query and filters for the owning user
- [ ] Returns 404 if config belongs to another user
- [ ] Platform cannot be changed via edit (422 or field disabled in UI)
- [ ] Edit form is pre-populated with current config values
- [ ] Submitting the edit form updates the config and refreshes the list
- [ ] Switching from edit mode to create mode resets the form cleanly
- [ ] Existing create flow is unaffected
