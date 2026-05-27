# T08 - Case-Insensitive Duplicate Skill Detection with Confirmation Dialog

## Priority
Medium

## Status
.Done

## Description
When adding a skill with different casing than an existing skill in the same field (e.g., typing "python" when "Python" already exists), show a confirmation dialog before adding. Currently only exact case-sensitive matches are blocked.

## Context
- `frontend/src/components/tag-input.tsx` — the `TagInput` component. The `commit()` function (line 16-21) checks `!value.includes(tag)` — case-sensitive, no feedback.
- `frontend/src/pages/profile.tsx` and `profile-helpers.ts` — the Profile page where TagInput is used for all skill fields.
- The tag fields are: `primary_skills`, `secondary_skills`, `tertiary_skills`, `not_a_good_fit`, `languages`, `exclude_keywords`.
- This task is closely related to T09 (cross-field blocking) — T08 handles same-field confirmation, T09 handles cross-field blocking.

## Acceptance Criteria
- [x] Exact case-sensitive duplicate in same field → toast "Skill already added" (existing behavior, unchanged)
- [x] Case-insensitive duplicate in same field → AlertDialog confirmation: "You've already added '{existing_skill}' in {field_name}. Are you sure you want to add '{new_skill}' to {field_name}?"
- [x] User confirms → skill added as typed (preserving user's casing)
- [x] User cancels → skill not added, input cleared
- [x] Confirmation dialog applies to ALL tag fields: primarySkills, secondarySkills, tertiarySkills, not_a_good_fit, languages, exclude_keywords
- [x] The field name in the dialog is human-readable (e.g., "Primary Skills" not "primary_skills")

## Implementation Notes

### 1. Modify `TagInput` component (`frontend/src/components/tag-input.tsx`)

Add a new optional prop:
```tsx
interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  className?: string;
  fieldName?: string;  // Human-readable field name for confirmation
  onDuplicateConfirm?: (existingSkill: string, newSkill: string, fieldName: string) => Promise<boolean>;
}
```

Update `commit()`:
```tsx
async function commit() {
  const tag = inputValue.trim();
  if (!tag) {
    setInputValue("");
    return;
  }

  // 1. Exact match — block immediately
  if (value.includes(tag)) {
    toast.error("Skill already added");
    setInputValue("");
    return;
  }

  // 2. Case-insensitive match in same field — show confirmation
  if (onDuplicateConfirm) {
    const existingMatch = value.find(v => v.toLowerCase() === tag.toLowerCase());
    if (existingMatch) {
      const confirmed = await onDuplicateConfirm(existingMatch, tag, fieldName ?? "");
      if (!confirmed) {
        setInputValue("");
        return;
      }
    }
  }

  // 3. No duplicate — add
  onChange([...value, tag]);
  setInputValue("");
}
```

Note: `commit()` must become `async` for the confirmation dialog. The `onBlur` and `onKeyDown` handlers that call `commit()` should handle this properly (the `onBlur` handler can call `commit()` without awaiting since the dialog is self-managing).

### 2. Modify Profile page (`frontend/src/pages/profile.tsx`)

In the Profile page, implement the confirmation dialog:

```tsx
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

// State for confirmation dialog
const [duplicateDialog, setDuplicateDialog] = useState<{
  existingSkill: string;
  newSkill: string;
  fieldName: string;
  resolve: (confirmed: boolean) => void;
} | null>(null);

async function handleDuplicateConfirm(
  existingSkill: string,
  newSkill: string,
  fieldName: string,
): Promise<boolean> {
  return new Promise((resolve) => {
    setDuplicateDialog({ existingSkill, newSkill, fieldName, resolve });
  });
}

function handleDuplicateResponse(confirmed: boolean) {
  if (duplicateDialog) {
    duplicateDialog.resolve(confirmed);
    setDuplicateDialog(null);
  }
}
```

Pass to each `TagInput`:
```tsx
<TagInput
  value={form.primary_skills}
  onChange={(tags) => setForm({ ...form, primary_skills: tags })}
  placeholder="Add a primary skill…"
  fieldName="Primary Skills"
  onDuplicateConfirm={handleDuplicateConfirm}
/>
```

Render the AlertDialog:
```tsx
<AlertDialog open={duplicateDialog !== null} onOpenChange={(open) => { if (!open) handleDuplicateResponse(false); }}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Duplicate Skill</AlertDialogTitle>
      <AlertDialogDescription>
        You've already added '{duplicateDialog?.existingSkill}' in {duplicateDialog?.fieldName}.
        Are you sure you want to add '{duplicateDialog?.newSkill}' to {duplicateDialog?.fieldName}?
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel onClick={() => handleDuplicateResponse(false)}>Cancel</AlertDialogCancel>
      <AlertDialogAction onClick={() => handleDuplicateResponse(true)}>Add Anyway</AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

### Field name mapping

Use human-readable names:
- `primary_skills` → "Primary Skills"
- `secondary_skills` → "Secondary Skills"
- `tertiary_skills` → "Tertiary Skills"
- `not_a_good_fit` → "Not a Good Fit"
- `languages` → "Languages"
- `exclude_keywords` → "Exclude Keywords"

## Dependencies
- T09 (Cross-Field Duplicate Skill Blocking) — these two tasks should be implemented together. The overall flow when adding a skill to any field is: (1) T09 cross-field check first, (2) exact same-field check, (3) T08 case-insensitive same-field confirmation.

## Files to Modify/Create
- `frontend/src/components/tag-input.tsx` (modify — add `fieldName` and `onDuplicateConfirm` props, update `commit()`)
- `frontend/src/pages/profile.tsx` (modify — add confirmation dialog state, pass props to TagInput instances)

## Tests
- Add "python" to Primary Skills → works normally
- Add "Python" to Primary Skills when "python" exists → toast "Skill already added"
- Add "python" to Primary Skills when "Python" exists → confirmation dialog appears
- Confirm in dialog → "python" added to Primary Skills (preserved casing)
- Cancel in dialog → nothing added, input cleared
- Works for all tag fields (secondary, tertiary, not_a_good_fit, languages, exclude_keywords)