# P3-1: Profile Page Redesign

- **Phase:** 3 — Profile Redesign
- **Priority:** P2 — Medium
- **Status:** TODO
- **Depends on:** None

## Problem

Profile page has too many plain text fields, comma-separated input is confusing, and the raw JSON rubric field is intimidating for non-technical users. Nobody will manually write JSON.

## Changes Required

### New Component — `frontend/src/components/tag-input.tsx`

- Tag/chip input component: user types text, presses Enter, sees a removable chip
- Props: `value: string[]`, `onChange: (tags: string[]) => void`, `placeholder: string`
- Each tag shows as a pill with an X button to remove
- Prevents duplicate tags

### Profile Page — Skills Section

- Replace comma-separated `<Textarea>` for primary/secondary/tertiary skills with `<TagInput>`
- Replace comma-separated "Not a Good Fit" textarea with `<TagInput>`
- Replace comma-separated "Languages" input with `<TagInput>`

### Profile Page — Background Section

- Replace "one entry per line" textarea with a dynamic list of `<Input>` fields
- Each entry gets its own row with a remove button (same pattern as Notable Projects)
- "Add entry" button at the bottom

### Profile Page — Rubric Section

Replace raw JSON textarea with structured form fields:

- **Minimum score threshold** — number input (1-10)
- **Prefer remote** — toggle/checkbox
- **Priority keywords** — `<TagInput>`
- **Avoid keywords** — `<TagInput>`
- **Advanced: raw JSON** — collapsible section for power users, hidden by default

### Profile Page — General UX

- Add helper text and examples for each field
- Add section descriptions explaining what each section is used for
- Consider a progress indicator showing profile completeness

### Backend — `api/schemas.py`

- Update rubric Pydantic model if structured fields need explicit schema validation
- Ensure backwards compatibility with existing free-form JSON rubric data

### Type Updates — `frontend/src/types/schemas.ts`

- Add structured rubric type alongside the generic `Record<string, unknown>`

## Files

- `frontend/src/components/tag-input.tsx` (new)
- `frontend/src/pages/profile.tsx`
- `frontend/src/types/schemas.ts`
- `api/schemas.py`

## Acceptance Criteria

- [ ] Skills use tag/chip input instead of comma-separated text
- [ ] Background uses dynamic list of individual inputs
- [ ] Rubric has structured form fields (no JSON knowledge needed)
- [ ] Power users can still access raw JSON via collapsible section
- [ ] Existing profile data loads correctly into the new form
- [ ] Saving works with both structured and raw JSON rubric
