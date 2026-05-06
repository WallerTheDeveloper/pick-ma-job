# Task 06: Generic (Non-Developer) Profile Support

## Goal

All prompts, configs, and filters must work for ANY job seeker, not just developers. Users can be HR specialists, nurses, marketers, accountants, or any other profession. The platform should be profession-agnostic.

## Current Problems

The codebase is littered with developer-specific language:

### `configs/prompts/base_profile.json`
- Top-level key is `"developer"` with `role`, `experience_years`, `level`, `rate`
- `evaluation_factors` says "Match the **developer's** stated level"
- `evaluation_factors` says "Prioritize roles that use the **developer's** primary skills"
- `evaluation_factors` says "Flag budgets that fall outside the **developer's** stated range"
- `scoring_rubric` says "appropriate level and **budget**" — budget is freelancer-centric
- `system_instructions` says "job-fit evaluator... assess against the **developer profile**"

### `core/prompt_adapter.py`
- `profile_row_to_prompt_dict()` outputs `"developer"` as the top-level key
- Docstring references "developer profile"

### `core/evaluator.py`
- `_build_score_system_prompt()` line 199: "Rate the relevance of the job posting to the **developer profile**"
- `_build_score_system_prompt()` line 202: "Developer: {role}"
- `_assemble_system_prompt()` line 239: "## **Developer** Profile"

### `configs/settings.json`
- `exclude_title_keywords` are all IT-specific: "unreal", "godot", "react native", "flutter", "devops", "data science", "machine learning", "data engineer", "android developer", "ios developer"
- These are global defaults — not per-user configurable

### `configs/prompts/upwork_context.json`
- Uses "client" terminology (freelancer-specific) — this is OK for Upwork context but shouldn't appear in base prompts

## Required Changes

### 1. Rename "developer" to "candidate" in Base Profile

**File**: `configs/prompts/base_profile.json`

Rename the top-level key and all references:

```json
{
  "candidate": {
    "role": "Example Role",
    "experience_years": 3,
    "level": "mid-level",
    "rate": {
      "hourly_eur": "20-40",
      "annual_eur": 60000
    }
  },
  ...
  "system_instructions": "You are a job-fit evaluator. Assess the provided job posting against the candidate profile above. ..."
}
```

Update all evaluation_factors text:
- "Match the **developer's** stated level" → "Match the **candidate's** stated level"
- "Prioritize roles that use the **developer's** primary skills" → "Prioritize roles that use the **candidate's** primary skills"
- "Flag budgets that fall outside the **developer's** stated range" → "Flag compensation that falls outside the **candidate's** stated range"

Update scoring_rubric:
- "appropriate level and budget" → "appropriate level and compensation"

### 2. Update `prompt_adapter.py`

**File**: `core/prompt_adapter.py`

Change `profile_row_to_prompt_dict()`:
- Output `"candidate"` as the top-level key instead of `"developer"`
- Update docstring to reference "candidate profile" instead of "developer profile"
- Update field names internally if any reference "developer"

### 3. Update `evaluator.py`

**File**: `core/evaluator.py`

Change all developer-specific references:

`_build_score_system_prompt()`:
```python
# Before
"You are a job-fit screener. Rate the relevance of the job posting to the developer profile below..."
f"Developer: {role} ({experience})"

# After
"You are a job-fit screener. Rate the relevance of the job posting to the candidate profile below..."
f"Candidate: {role} ({experience})"
```

`_assemble_system_prompt()`:
```python
# Before
f"## Developer Profile\n{json.dumps(self._base_profile, indent=2)}"

# After
f"## Candidate Profile\n{json.dumps(self._base_profile, indent=2)}"
```

### 4. Make `exclude_title_keywords` User-Configurable

**File**: `db/migrations/015_add_exclude_keywords.sql`

```sql
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS exclude_keywords TEXT[] DEFAULT '{}';
```

**File**: `api/schemas.py`

Add to profile schemas:
```python
class ProfileSaveRequest(BaseModel):
    # ... existing fields ...
    exclude_keywords: list[str] = []

class ProfileResponse(BaseModel):
    # ... existing fields ...
    exclude_keywords: list[str] = []
```

**File**: `repositories/profile.py`

Update the profile row type and save method to handle `exclude_keywords`.

**File**: `frontend/src/pages/profile.tsx`

Add a tag input field for exclude keywords:
- Reuse the existing `TagInput` component (already used for skills)
- Label: "Exclude job titles containing these keywords"
- Help text: "Jobs with these words in the title will be skipped during pipeline runs. Leave empty to use system defaults."

**File**: `services/pipeline.py`

Merge user's exclude_keywords with global defaults:
```python
# In __init__ or _run_platform:
user_exclude = set(kw.lower() for kw in profile.exclude_keywords)
global_exclude = set(kw.lower() for kw in settings.exclude_title_keywords)
effective_exclude = user_exclude if user_exclude else global_exclude
# If user has custom keywords, use ONLY those (don't merge with global)
# If user has empty list, fall back to global defaults
```

This means:
- User with `exclude_keywords = ["nurse", "therapist"]` → only filters those
- User with `exclude_keywords = []` → uses system defaults from `settings.json`
- User can add their own profession-specific exclusions

### 5. Review Platform Context Prompts

**Files**: `configs/prompts/upwork_context.json`, `configs/prompts/linkedin_context.json`

Review each for developer-specific language:
- `upwork_context.json`: "client" is fine (Upwork-specific), but ensure `evaluation_notes` don't assume developer skills
- `linkedin_context.json`: same review — ensure it's profession-agnostic

Update any notes that reference developer-specific concepts (e.g., "code review", "sprint", "deployment").

### 6. Update `base_profile.json` Scoring Rubric

**File**: `configs/prompts/base_profile.json`

Make the scoring rubric profession-agnostic:

```json
{
  "scoring_rubric": {
    "9-10": "Excellent match — hits primary strengths, appropriate level and compensation, apply immediately",
    "7-8": "Good match — primarily relevant with minor gaps, likely worth applying",
    "5-6": "Moderate match — touches secondary/tertiary skills or notable mismatches, apply cautiously",
    "3-4": "Poor match — only tangential overlap or significant red flags, probably not worth it",
    "1-2": "Very poor match — outside domain entirely, do not apply"
  },
  "evaluation_factors": [
    "Skills Match: How well required skills align with primary > secondary > tertiary strengths",
    "Experience Level: Match the candidate's stated level",
    "Role Type: Prioritize roles that use the candidate's primary skills",
    "Compensation: Flag compensation that falls outside the candidate's stated range",
    "Role Scope: Both full ownership and team contribution are acceptable",
    "Employer Quality: Flag vague requirements, unrealistic expectations, unpaid trial work",
    "Competition: Niche roles with fewer applicants are a positive signal"
  ]
}
```

## Files to Modify

| File | Change |
|------|--------|
| `configs/prompts/base_profile.json` | Rename `developer` → `candidate`; update all evaluation text |
| `core/prompt_adapter.py` | Output `candidate` key; update docstring |
| `core/evaluator.py` | Change "developer" → "candidate" in all prompt text |
| `configs/settings.json` | Review defaults; keep as fallback (user can override) |
| `db/migrations/015_add_exclude_keywords.sql` | **New file** — add `exclude_keywords` column to profiles |
| `api/schemas.py` | Add `exclude_keywords` to profile request/response |
| `repositories/profile.py` | Handle new column |
| `frontend/src/pages/profile.tsx` | Add exclude keywords tag input |
| `services/pipeline.py` | Merge user exclude_keywords with global defaults |
| `configs/prompts/upwork_context.json` | Review for developer-specific language |
| `configs/prompts/linkedin_context.json` | Review for developer-specific language |

## Acceptance Criteria

- [ ] No file in the codebase references "developer" in prompt text (except comments/docstrings)
- [ ] `base_profile.json` uses `"candidate"` as the top-level key
- [ ] Score prompt says "candidate profile" not "developer profile"
- [ ] System prompt says "## Candidate Profile" not "## Developer Profile"
- [ ] Evaluation factors are profession-agnostic (no "budget", use "compensation")
- [ ] Users can configure their own `exclude_keywords` in the profile form
- [ ] Empty `exclude_keywords` falls back to system defaults from `settings.json`
- [ ] A nurse can configure exclude keywords like ["developer", "engineer", "programmer"]
- [ ] A developer can keep the existing defaults
- [ ] Platform context prompts don't assume developer skills
- [ ] All existing tests pass after the rename

## Migration Note

The `developer` → `candidate` rename in `base_profile.json` is a **breaking change** for the prompt structure. Any existing stored profiles that reference the `developer` key in custom configs will break. However, since `base_profile.json` is loaded from disk at startup (not from DB), this only affects the static config file.

The `profile_row_to_prompt_dict()` function maps DB profile data into the prompt dict — the key name change from `"developer"` to `"candidate"` is internal and doesn't affect the DB schema.

## Dependencies

- **Depends on**: None (independent feature, but should be done early since it touches many files)
- **Blocks**: None — but affects all other tasks that modify prompts
