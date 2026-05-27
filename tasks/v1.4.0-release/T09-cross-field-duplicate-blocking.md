# T09 - Cross-Field Duplicate Skill Blocking with Toast

## Priority
Medium

## Status
.Done

## Description
When a user tries to add a skill that already exists (case-insensitive) in a different profile field, block the addition and show a toast indicating where it already exists. For example, adding "Unity" to Primary Skills when "unity" is already in Secondary Skills should be blocked with a toast "Skill 'unity' is already in Secondary Skills".

## Context
- The Profile page has six tag fields: `primary_skills`, `secondary_skills`, `tertiary_skills`, `not_a_good_fit`, `languages`, `exclude_keywords`.
- Currently, skills can be added independently across fields — "Unity" in Primary and "unity" in Secondary both exist without any warning.
- `frontend/src/pages/profile.tsx` manages the form state for all these fields.
- `frontend/src/components/tag-input.tsx` handles individual tag input per field.
- This task works in conjunction with T08 (same-field case-insensitive confirmation). The overall flow: T09 cross-field check runs first, then T08 same-field check.

## Acceptance Criteria
- [ ] Adding a skill that case-insensitively matches a skill in another field → blocked, toast: "Skill '{skill}' is already in {field_name}"
- [ ] Blocking applies to ALL tag fields cross-referencing ALL other tag fields
- [ ] Field names in toasts are human-readable: "Primary Skills", "Secondary Skills", "Tertiary Skills", "Not a Good Fit", "Languages", "Exclude Keywords"
- [ ] The blocked skill is NOT added to any field
- [ ] Cross-field check runs BEFORE the same-field confirmation dialog from T08

## Implementation Notes

### Create a utility function

Create or add to `frontend/src/pages/profile-helpers.ts`:

```typescript
interface FormState {
  primary_skills: string[];
  secondary_skills: string[];
  tertiary_skills: string[];
  not_a_good_fit: string[];
  languages: string[];
  exclude_keywords: string[];
}

const FIELD_LABELS: Record<keyof FormState, string> = {
  primary_skills: "Primary Skills",
  secondary_skills: "Secondary Skills",
  tertiary_skills: "Tertiary Skills",
  not_a_good_fit: "Not a Good Fit",
  languages: "Languages",
  exclude_keywords: "Exclude Keywords",
};

const FORM_FIELDS: (keyof FormState)[] = [
  "primary_skills",
  "secondary_skills",
  "tertiary_skills",
  "not_a_good_fit",
  "languages",
  "exclude_keywords",
];

export function findSkillInOtherFields(
  skill: string,
  currentField: keyof FormState,
  form: FormState,
): { field: keyof FormState; fieldName: string } | null {
  const skillLower = skill.toLowerCase();
  for (const field of FORM_FIELDS) {
    if (field === currentField) continue;
    const fieldValue = form[field];
    if (fieldValue.some(s => s.toLowerCase() === skillLower)) {
      return { field, fieldName: FIELD_LABELS[field] };
    }
  }
  return null;
}

export { FIELD_LABELS, FORM_FIELDS };
```

### Modify Profile page (`frontend/src/pages/profile.tsx`)

For each `TagInput`'s `onChange` handler, add cross-field checking. Example for `primary_skills`:

```typescript
import { findSkillInOtherFields } from "@/pages/profile-helpers";
import { toast } from "sonner";

// In the TagInput onChange wrapper:
function handlePrimarySkillsChange(tags: string[]) {
  // Check if the NEW tag (last element) already exists in another field
  const newTags = tags.filter(t => !form.primary_skills.includes(t));
  for (const newTag of newTags) {
    const found = findSkillInOtherFields(newTag, "primary_skills", form);
    if (found) {
      toast.error(`Skill '${newTag}' is already in ${found.fieldName}`);
      return; // Block the addition
    }
  }
  setForm({ ...form, primary_skills: tags });
}
```

However, since `TagInput` calls `onChange` with the full new array, detecting the "new" tag requires comparing with previous state. A cleaner approach:

**Alternative approach — wrap TagInput's onChange:**

Instead of modifying onChange, pass a validation callback to `TagInput` that runs before the tag is added. This is cleaner because it works with the `commit()` flow in TagInput.

Add a new prop to `TagInput`:
```tsx
interface TagInputProps {
  // ... existing props
  onBeforeAdd?: (tag: string) => boolean | Promise<boolean>;  // Return false to block
}
```

In `commit()`:
```tsx
async function commit() {
  const tag = inputValue.trim();
  if (!tag) { setInputValue(""); return; }

  // Exact match check
  if (value.includes(tag)) {
    toast.error("Skill already added");
    setInputValue("");
    return;
  }

  // Cross-field + same-field case-insensitive check via callback
  if (onBeforeAdd) {
    const allowed = await onBeforeAdd(tag);
    if (!allowed) {
      setInputValue("");
      return;
    }
  }

  // Case-insensitive same-field check (T08)
  if (onDuplicateConfirm) {
    // ... T08 logic
  }

  onChange([...value, tag]);
  setInputValue("");
}
```

Then in the Profile page, provide the `onBeforeAdd` callback for each field:

```tsx
<TagInput
  value={form.primary_skills}
  onChange={(tags) => setForm({ ...form, primary_skills: tags })}
  placeholder="Add a primary skill…"
  fieldName="Primary Skills"
  onBeforeAdd={(tag) => {
    const found = findSkillInOtherFields(tag, "primary_skills", form);
    if (found) {
      toast.error(`Skill '${tag}' is already in ${found.fieldName}`);
      return false;
    }
    return true;
  }}
  onDuplicateConfirm={handleDuplicateConfirm}
/>
```

### Combined flow with T08

The overall flow when adding a skill "opencode" to "Primary Skills":
1. **Cross-field check (T09)**: `onBeforeAdd` checks all other fields. If "opencode"/"OpenCode" exists in Secondary Skills → toast error "Skill 'opencode' is already in Secondary Skills" and BLOCK (return false).
2. **Exact same-field check**: `value.includes(tag)` — "opencode" exact match → toast "Skill already added" and BLOCK.
3. **Case-insensitive same-field check (T08)**: `onDuplicateConfirm` — "OpenCode" exists with different casing → confirmation dialog. If confirmed → add. If cancelled → don't add.

## Dependencies
- T08 (same-field confirmation) — should be implemented together with T09 for a cohesive UX. The `onBeforeAdd` and `onDuplicateConfirm` props work together in the `commit()` flow.

## Files to Modify/Create
- `frontend/src/pages/profile-helpers.ts` (modify — add `findSkillInOtherFields`, field labels)
- `frontend/src/components/tag-input.tsx` (modify — add `onBeforeAdd` prop, integrate into `commit()`)
- `frontend/src/pages/profile.tsx` (modify — pass `onBeforeAdd` to all TagInput instances with cross-field check)

## Tests
- Add "Unity" to Secondary Skills, then try adding "unity" to Primary Skills → blocked with toast "Skill 'unity' is already in Secondary Skills"
- Add "Python" to Primary Skills, then add "python" to Primary Skills → toast "Skill already added" (exact match, T08-level-1)
- Add "Python" to Primary Skills, then add "python" to Secondary Skills → blocked with "Skill 'python' is already in Primary Skills"
- Cross-field blocking works between ALL field pairs
- Adding a unique skill that doesn't exist anywhere → works normally