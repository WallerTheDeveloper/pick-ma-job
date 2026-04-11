# FE-19: profile.tsx and search-config.tsx Exceed 400-Line Guideline

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** improvements-1_index-key-profile-lists, improvements-3_buildrubric-mutation-swallow

## Problem

`src/pages/profile.tsx` (567 lines) and `src/pages/search-config.tsx` (558 lines) both exceed the 400-line guideline. Each file mixes form-state helpers, data conversion functions, sub-components, and the main page component in a single module.

## Approach

### profile.tsx
1. Extract form helper functions (`buildRubric`, `parseProfile`, profile-to-form converters) into `src/pages/profile/profile-form-helpers.ts`.
2. Extract sub-sections (rubric editor, background entries list, notable projects list, skills/tag section) into separate components under `src/pages/profile/` or `src/components/profile/`.
3. Keep the main `ProfilePage` component as the orchestrator in `src/pages/profile/index.tsx`.

### search-config.tsx
1. Extract the config card (individual search config display + edit form) into `src/components/search-config-card.tsx`.
2. Extract the "new config" form into `src/components/new-search-config-form.tsx`.
3. Extract filter rendering helpers into a utility file.
4. Keep the main page as the orchestrator.

## Files

- `frontend/src/pages/profile.tsx` — split into multiple files
- `frontend/src/pages/search-config.tsx` — split into multiple files

## Implementation Notes

- This is a refactoring task with no behavior changes. All existing tests must continue to pass.
- Do this after improvements-1 (stable keys) and improvements-3 (buildRubric fix) since those tasks modify the same files.
- Consider converting the page directories to use barrel exports (`index.tsx`) for clean imports.
