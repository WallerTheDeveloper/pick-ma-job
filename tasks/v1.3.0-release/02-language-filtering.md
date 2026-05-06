# Task 02: Language Filtering

## Goal

Skip jobs whose description is in a language the user doesn't speak, as specified in their profile `languages` field. Jobs that are filtered out should be stored in an auto-created "skipped jobs" list so users can review them later.

## Current Behavior

- User profile has a `languages` field (`TEXT[] NOT NULL DEFAULT '{}'`) stored in the `profiles` table
- The `languages` field is stored and returned by the API but is **NOT used anywhere** in the evaluation pipeline
- `core/evaluator.py` `_build_score_system_prompt()` includes role, experience, primary_skills, and not_a_good_fit — no languages
- `_assemble_system_prompt()` includes the full `base_profile` JSON but languages are not checked against the job description's language
- `core/prompt_adapter.py` `profile_row_to_prompt_dict()` maps the `languages` field into the prompt dict but it's never referenced in scoring or evaluation prompts
- The pipeline in `services/pipeline.py` runs: scrape → dedup → blacklist filter → keyword filter → evaluate → store. There is no language filter step.

## Required Changes

### 1. Backend — Language Detector Module

**New file**: `core/language_detector.py`

Create a lightweight language detection service:

```python
class LanguageDetector:
    def __init__(self, llm_client: LLMClient, model: str = "claude-haiku-4-5-20251001") -> None: ...
    
    async def detect(self, text: str) -> str:
        """Detect the primary language of the given text.
        
        Uses a minimal prompt to minimize cost:
        "What is the primary language of the following text? 
         Reply with ONLY the language name in English (e.g., Dutch, French, English). 
         No explanation."
        
        Returns the language name (e.g., "English", "Dutch", "French").
        Uses max_tokens=16 to keep response short.
        """
```

Key design decisions:
- Use the job **description** as the source of truth, NOT the title. Titles are often in English even when the description is in Dutch.
- Use the cheapest model (haiku) with minimal tokens
- The response is a single language name — easy to compare against the user's `languages` list
- Handle edge cases: empty description, mixed-language text (use the primary language), unparseable responses (default to English or skip the filter)

### 2. Backend — Language Filter Step in Pipeline

**File**: `services/pipeline.py`

Add a new pre-filter step in `_run_platform()` that runs **after keyword filtering but before evaluation**:

```python
# After the existing pre-filter loop (line ~289), add language filtering:
jobs_skipped_language = 0
language_skipped_jobs: list[tuple[NormalizedJob, str]] = []  # (job, detected_language)

if user_languages:  # Only filter if user has configured languages
    for job in jobs_to_evaluate:
        detected_lang = await language_detector.detect(job.description)
        if detected_lang.lower() not in user_languages_lower:
            jobs_skipped_language += 1
            language_skipped_jobs.append((job, detected_lang))
            continue
        filtered_jobs.append(job)
    jobs_to_evaluate = filtered_jobs
```

The filter is **opt-in**: if the user's `languages` list is empty or contains only `[]`, skip the language filter entirely (evaluate everything).

### 3. Backend — Skipped Jobs Auto-List

**File**: `services/pipeline.py` (and potentially `services/auto_list_service.py`)

After the language filter, create an auto-list for skipped jobs:
- List name format: `"Skipped jobs_YYYY-MM-DD_HH:MM:SS"` (same timestamp as the pipeline run)
- Store skipped jobs in `job_results` with `skip_reason='language'` and `detected_language` populated
- These jobs should appear in the sidebar Lists section
- They should NOT appear in the main results view by default (add a filter or separate tab)

### 4. Backend — Database Migration

**New file**: `db/migrations/012_add_skip_fields.sql`

```sql
ALTER TABLE job_results 
  ADD COLUMN IF NOT EXISTS skip_reason TEXT,
  ADD COLUMN IF NOT EXISTS detected_language TEXT;
```

### 5. Backend — Repository Updates

**File**: `repositories/job_result.py`

- Update `insert()` to accept optional `skip_reason` and `detected_language` parameters
- Update the row type to include these new fields
- Add a query method to find skipped jobs by reason

### 6. Backend — PipelineStats Update

**File**: `services/pipeline.py`

Add `jobs_skipped_language` to `PipelineStats`:

```python
@dataclass(frozen=True)
class PipelineStats:
    jobs_found: int = 0
    jobs_skipped_dedup: int = 0
    jobs_skipped_filter: int = 0
    jobs_skipped_blacklist: int = 0
    jobs_skipped_language: int = 0  # NEW
    jobs_skipped_low_score: int = 0
    jobs_evaluated: int = 0
    jobs_stored: int = 0
    jobs_failed: int = 0
    jobs_score_parse_failed: int = 0
    errors: tuple[str, ...] = ()
```

### 7. Frontend — Skipped Jobs Display

**File**: `frontend/src/components/list-manager.tsx` or new component

When viewing a "Skipped jobs" list in the sidebar, show additional metadata:
- The detected language badge for each job
- The skip reason ("Language not in profile")
- A button to "Force Evaluate" if the user wants to override the filter

### 8. Frontend — Profile Language Configuration

The `languages` field already exists in the profile. Verify the frontend profile form (`frontend/src/pages/profile.tsx`) allows users to configure their spoken languages. If not, add a multi-select input for languages.

## Cost Consideration

Using a separate LLM call for language detection adds API cost:
- Each detection call: ~100–500 input tokens (job description) + 1–5 output tokens
- With 50 jobs: ~50 extra API calls per pipeline run
- Cost estimate: ~$0.01–0.05 per pipeline run (at haiku pricing)

**Alternative (cheaper but less accurate)**: Include language checking in the existing score prompt. However, this means jobs still go through the full scoring pipeline before being filtered, and the score prompt becomes more complex. The pre-filter approach is cleaner and saves evaluation costs for non-matching jobs.

**Decision**: Use the separate lightweight detection call. The cost is minimal and the separation of concerns is cleaner.

## Files to Modify

| File | Change |
|------|--------|
| `core/language_detector.py` | **New file** — lightweight LLM-based language detection |
| `services/pipeline.py` | Add language filter step after keyword filter; create skipped jobs auto-list |
| `db/migrations/012_add_skip_fields.sql` | **New file** — add `skip_reason` and `detected_language` columns |
| `repositories/job_result.py` | Update `insert()` and row type for new columns |
| `core/prompt_adapter.py` | Verify `languages` field is properly mapped (already done, verify only) |
| `frontend/src/components/list-manager.tsx` | Show detected language and skip reason in skipped jobs lists |
| `frontend/src/pages/profile.tsx` | Verify language configuration UI exists |
| `frontend/src/types/schemas.ts` | Add `skip_reason` and `detected_language` to JobResult type |

## Acceptance Criteria

- [ ] Jobs with descriptions in languages not in the user's `languages` list are skipped during pipeline
- [ ] Skipped jobs are stored in an auto-created "Skipped jobs" list with detected language and reason
- [ ] Language detection uses the cheapest model with minimal tokens
- [ ] If user has no languages configured, the language filter is skipped (all jobs evaluated)
- [ ] Job title language is NOT used — only the description
- [ ] Skipped jobs appear in the sidebar Lists section with language and reason visible
- [ ] `PipelineStats` includes `jobs_skipped_language` count
- [ ] Database migration adds `skip_reason` and `detected_language` columns

## Dependencies

- **Depends on**: None (independent feature)
- **Blocks**: Task 05 (Closed Jobs Filtering) — will reuse the skipped jobs list mechanism and `skip_reason` column
