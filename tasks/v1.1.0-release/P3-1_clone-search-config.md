# P3-1: Clone Existing Config When Creating New One

- **Phase:** 3 — Config Clone
- **Priority:** P2 — Enhancement
- **Status:** Done
- **Depends on:** P2-1 (edit form refactor)

## Problem

When creating a new search config, users must fill in all fields from scratch even if they want a config nearly identical to an existing one. A "start from existing" option would save time and reduce errors.

## Scope

Frontend-only — no backend changes. Cloning is implemented by prefilling the create form and then submitting a standard `POST`.

### Frontend

1. **`frontend/src/pages/search-config.tsx`** — in the create form, add a "Start from existing" `<Select>` dropdown populated from `useSearchConfigs`.
   - On selection: populate `query` and `filters` fields with the source config's values. Default the `platform` field to the source's platform (user may change it).
   - The dropdown only appears when the form is in create mode (not edit mode).
   - Selecting an option does not submit — it only prefills. User still clicks "Create".
   - Selecting "None / start fresh" clears any prefilled values.

## Files

- `frontend/src/pages/search-config.tsx`

## Acceptance Criteria

- [x] "Start from existing" dropdown is visible in create mode
- [x] Selecting a config prefills query, filters, and platform in the form
- [x] User can modify any prefilled field before submitting
- [x] Submitting creates a new config (does not overwrite the source)
- [x] Dropdown is hidden when the form is in edit mode
- [x] Selecting "None" or clearing the dropdown resets the form to empty defaults
