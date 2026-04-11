# FE-1: 4 Failing CI Tests

- **Phase:** fixes
- **Priority:** P1 (Critical)
- **Status:** DONE
- **Depends on:** None

## Problem

Four tests fail due to mismatches between test assertions and actual component behavior:

1. `results.test.tsx` "filters by status" (line 63) and "updates result status via dropdown" (line 181): `getByText("Dismissed")` finds multiple elements because the Radix `Select` renders the selected value inside the trigger AND inside the dropdown list simultaneously.
2. `profile.test.tsx` "loads and displays existing profile data in form fields" (line 17): uses `getByDisplayValue("Unity, C#, AR/VR")` but `TagInput` renders individual chip `<span>` elements, not a single input with a comma-joined value.
3. `profile.test.tsx` "shows error toast for invalid JSON in rubric field" (line 159): searches for placeholder `{"min_score": 5, "prefer_remote": true}` but actual placeholder in `profile.tsx:547` is `{"custom_field": "value"}`.
4. All results-page tests emit MSW errors for unhandled `GET /api/lists`, `/api/lists/:id/jobs`, `/api/results/:id/lists`. The MSW server is configured with `onUnhandledRequest: "error"`, and `ResultRow` triggers these endpoints on every render.

## Approach

1. Add MSW handlers for list endpoints in the test handler file: `GET /api/lists` returning `[]`, `GET /api/lists/:id/jobs` returning `[]`, `GET /api/results/:id/lists` returning `[]`.
2. In `results.test.tsx`, replace `getByText("Dismissed")` with `getAllByText("Dismissed")` and assert on the correct element, or use `getByRole` to target the specific trigger or option.
3. In `profile.test.tsx` line 17, replace `getByDisplayValue("Unity, C#, AR/VR")` with assertions that check each chip individually: `getByText("Unity")`, `getByText("C#")`, `getByText("AR/VR")`.
4. In `profile.test.tsx` line 159, update the placeholder string to `{"custom_field": "value"}` to match the actual component.

## Files

- `frontend/src/pages/results.test.tsx:63,181` — fix Select assertions
- `frontend/src/pages/profile.test.tsx:17` — fix TagInput assertion
- `frontend/src/pages/profile.test.tsx:159` — fix rubric placeholder string
- `frontend/src/test/handlers.ts` — add MSW handlers for list endpoints

## Implementation Notes

- Run `npm test` after each fix to confirm tests go green incrementally.
- The MSW handler additions are the highest-impact fix since they affect all results-page tests.
