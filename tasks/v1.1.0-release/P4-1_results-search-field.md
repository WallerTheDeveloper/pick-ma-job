# P4-1: Results Search Field

- **Phase:** 4 — Results UX
- **Priority:** P2 — Enhancement
- **Status:** DONE
- **Depends on:** None

## Problem

The results page has filter controls (score, status, platform) but no way to search by text. Users who remember a job title or keyword have to scroll through the full list to find it.

## Scope

Frontend-only, client-side filtering. Server-side `?q=` search can be added later if result volume warrants it.

### Frontend

1. **`frontend/src/pages/results.tsx`** — add a text `<Input>` bound to a `searchTerm` state.
   - Filter the rendered job rows by case-insensitive match on: `title`, `evaluation.summary`, and `url` (as a fallback identifier).
   - Use `useDeferredValue` or a 150 ms debounce to avoid filtering on every keystroke.
   - The search field sits alongside existing filter controls (score, status, platform).
   - Clearing the field restores the full filtered list.

## Files

- `frontend/src/pages/results.tsx`

## Acceptance Criteria

- [ ] Search input is visible on the results page
- [ ] Typing filters job rows in real time (debounced)
- [ ] Match is case-insensitive and covers title and summary fields
- [ ] Clearing the input restores the full list
- [ ] Existing score/status/platform filters still work in combination with the search field
- [ ] No API calls are made as the user types
