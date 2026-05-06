# Task 04: CV Diff-Style Generation

## Goal

The CV customization should return only changed fields (diff style), not the full rewritten CV. Section titles must always be included even if unchanged. This saves tokens and reduces API costs by avoiding regeneration of unchanged sections like phone numbers, addresses, and education.

## Current Behavior

- `services/cv_service.py` `_call_customize()` returns full plain text CV
- `configs/prompts/cv_customize.json` prompt instructs: "Output plain text only — no JSON, no markdown fences, no commentary"
- The output is stored as `customized_text` (TEXT) in the `cv_customizations` table
- The frontend `CustomizeCVDialog` displays the full customized text in a dialog
- Every customization regenerates the entire CV including sections that never change (contact info, education)

## Required Changes

### 1. Backend — Change CV Output Format to Structured JSON

**File**: `configs/prompts/cv_customize.json`

Modify the prompt to return a JSON object with diff-style sections:

```json
{
  "system": "... (same anti-fabrication prompt from Task 03) ...\n\nOUTPUT FORMAT:\nReturn a JSON object with this exact structure:\n{\n  \"sections\": [\n    {\n      \"title\": \"SECTION NAME\",\n      \"content\": \"The section content (original or modified)\",\n      \"changed\": true|false\n    }\n  ]\n}\n\nRules for output:\n- Include EVERY section from the original CV, even unchanged ones\n- Section titles MUST always be included (ALL CAPS)\n- Content must always be included (even if unchanged, copy the original)\n- Set \"changed\": true ONLY if you modified the content from the original\n- Set \"changed\": false if the content is identical to the original\n- Do NOT add sections that don't exist in the original CV",
  "user_template": "... (same template from Task 03) ..."
}
```

### 2. Backend — Update `_call_customize()` Return Type

**File**: `services/cv_service.py`

Change `_call_customize()` to use `generate_json` instead of `generate_text`:

```python
async def _call_customize(
    self,
    job_title: str,
    job_description: str,
    cv_text: str,
    structured: dict,
) -> dict:
    """Call Claude to customize the CV. Returns diff-style JSON:
    
    {
        "sections": [
            {"title": "SUMMARY", "content": "...", "changed": True},
            {"title": "EXPERIENCE", "content": "...", "changed": True},
            {"title": "EDUCATION", "content": "...", "changed": False},
        ]
    }
    """
```

Also add a helper to generate the full text from the diff for backward compatibility:

```python
def _diff_to_full_text(diff: dict) -> str:
    """Convert diff-style sections to full plain text CV."""
    parts = []
    for section in diff.get("sections", []):
        parts.append(section["title"])
        parts.append(section["content"])
        parts.append("")  # blank line between sections
    return "\n".join(parts).strip()
```

### 3. Backend — Database Migration

**New file**: `db/migrations/013_cv_customization_diff.sql`

Add a new JSONB column alongside the existing TEXT column for backward compatibility:

```sql
ALTER TABLE cv_customizations
  ADD COLUMN IF NOT EXISTS customized_diff JSONB;
```

Keep `customized_text` for backward compatibility and as a fallback. New code writes to both columns; reads prefer `customized_diff` when available.

### 4. Backend — Repository Update

**File**: `repositories/cv_customization.py`

Update the upsert method to store both formats:

```python
async def upsert(
    self,
    user_id: UUID,
    job_result_id: UUID,
    customized_text: str,
    customized_diff: dict | None = None,  # NEW
) -> CVCustomizationRow:
```

Update the find method to return both fields. Update the row type:

```python
@dataclass(frozen=True)
class CVCustomizationRow:
    id: UUID
    user_id: UUID
    job_result_id: UUID
    customized_text: str
    customized_diff: dict | None  # NEW — preferred when available
    created_at: datetime
    updated_at: datetime
```

### 5. Backend — Service Update

**File**: `services/cv_service.py`

Update `customize_cv()` to store both formats:

```python
async def customize_cv(self, user_id: UUID, job_result_id: UUID) -> CVCustomizationRow:
    # ... existing logic ...
    diff = await self._call_customize(job_title, job_description, cv_text, structured)
    full_text = _diff_to_full_text(diff)
    
    return await self._cv_customization_repo.upsert(
        user_id=user_id,
        job_result_id=job_result_id,
        customized_text=full_text,
        customized_diff=diff,
    )
```

### 6. Backend — API Response Update

**File**: `api/schemas.py` and `api/routes/api_cv.py`

Update `CVCustomizeResponse` to include the diff format:

```python
class CVSectionDiff(BaseModel):
    title: str
    content: str
    changed: bool

class CVCustomizeResponse(BaseModel):
    customized_text: str  # full text (backward compat)
    sections: list[CVSectionDiff]  # diff format (preferred)
    warnings: list[str] | None = None  # from Task 03
```

### 7. Frontend — Diff Highlighting

**File**: `frontend/src/components/customize-cv-dialog.tsx`

Update the dialog to display sections with diff highlighting:

```tsx
{sections.map((section) => (
  <div key={section.title} className="mb-4">
    <h3 className="font-bold text-sm uppercase tracking-wider text-muted-foreground">
      {section.title}
    </h3>
    <div className={section.changed 
      ? "bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 pl-3 py-2" 
      : "pl-3 py-2 opacity-60"
    }>
      <pre className="whitespace-pre-wrap text-sm">{section.content}</pre>
    </div>
    {!section.changed && (
      <span className="text-xs text-muted-foreground ml-3">No changes</span>
    )}
  </div>
))}
```

Visual design:
- Changed sections: highlighted background (yellow tint), left border accent
- Unchanged sections: dimmed/opacity, "No changes" badge
- Section titles always visible in ALL CAPS
- Toggle to "Show all" vs "Show changes only" (optional enhancement)

### 8. Frontend — Type Updates

**File**: `frontend/src/types/schemas.ts`

```typescript
interface CVSectionDiff {
  title: string;
  content: string;
  changed: boolean;
}

interface CVCustomizeResponse {
  customized_text: string;
  sections: CVSectionDiff[];
  warnings?: string[];
}
```

## Files to Modify

| File | Change |
|------|--------|
| `configs/prompts/cv_customize.json` | Change to JSON output format with diff sections |
| `services/cv_service.py` | Parse JSON response, add `_diff_to_full_text()`, store both formats |
| `repositories/cv_customization.py` | Add `customized_diff` JSONB column handling |
| `db/migrations/013_cv_customization_diff.sql` | **New file** — add `customized_diff` column |
| `api/schemas.py` | Add `CVSectionDiff`, update `CVCustomizeResponse` |
| `api/routes/api_cv.py` | Return sections in diff format |
| `frontend/src/components/customize-cv-dialog.tsx` | Highlight changed sections, dim unchanged |
| `frontend/src/types/schemas.ts` | Add `CVSectionDiff` type, update response type |

## Acceptance Criteria

- [ ] CV customization returns a JSON object with `sections` array
- [ ] Each section has `title`, `content`, and `changed` boolean
- [ ] Section titles are ALWAYS included even if unchanged
- [ ] Unchanged sections contain the original content with `changed: false`
- [ ] `customized_diff` JSONB column is added to the database
- [ ] Both `customized_text` and `customized_diff` are stored for each customization
- [ ] API response includes both full text and sections array
- [ ] Frontend shows changed sections with yellow highlight and left border
- [ ] Frontend shows unchanged sections dimmed with "No changes" badge
- [ ] Token usage decreases compared to generating the full CV every time
- [ ] Backward compatibility: old customizations without `customized_diff` still display correctly

## Dependencies

- **Depends on**: Task 03 (CV Anti-Fabrication) — the prompt rewrite in Task 03 should be done first, then this task adds the JSON output format on top
- **Blocks**: None
