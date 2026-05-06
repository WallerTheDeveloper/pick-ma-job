# Task 05: Closed Jobs Filtering

## Goal

If a job is no longer accepting applications, it should be skipped and placed in the skipped jobs list so the user doesn't waste time applying to closed positions.

## Current Behavior

- `scrapers/base.py` `NormalizedJob` dataclass has no field for job status (open/closed)
- The Upwork scraper (`scrapers/upwork.py`) maps: `id`, `title`, `description`, `url`, `skills`, `budget`, `job_type`, `experience_level`, and extras (`client_rating`, `client_location`, `proposals`)
- The LinkedIn scraper (`scrapers/linkedin.py`) maps: `id`, `title`, `description`, `url`, `budget`, `job_type`, `experience_level`, `company_name`, `location`, and extras (`work_type`, `sector`, `applications_count`, `apply_type`, `posted_time`, `poster_name`, `company_url`)
- Neither scraper extracts or maps any `is_active`, `accepting_applications`, or `is_closed` field
- LinkedIn has an `apply_type` extra field that maps values like "Apply", "Easy Apply" — but does NOT currently detect "Expired"

## Investigation Required

Before implementing, check the Apify actor documentation for both scrapers to determine if they provide any field indicating whether a job is still accepting applications.

### Upwork Scraper

Check the Apify actor output for fields like:
- `isApplied`
- `status`
- `isOpen`
- `active`
- `is_archived`

### LinkedIn Scraper

Check the Apify actor output for fields like:
- `isApplicationExpired`
- `isClosed`
- `applyType` (check if it can return "Expired" or similar)
- `status`

**How to investigate**:
1. Check `configs/platforms/upwork.json` and `configs/platforms/linkedin.json` for the actor IDs
2. Look up the Apify actor documentation pages for those actors
3. Check the raw scraper output (add debug logging to print one full job object)
4. Review the `field_mappings` in the platform configs to see if any unmapped fields exist

## Implementation (if scraper provides the data)

### 1. Backend — Add `is_closed` to NormalizedJob

**File**: `scrapers/base.py`

Add a new field to the `NormalizedJob` frozen dataclass:

```python
@dataclass(frozen=True)
class NormalizedJob:
    id: str
    platform: str
    title: str
    description: str
    url: str
    skills: tuple[str, ...]
    budget: str | None
    job_type: str | None
    experience_level: str | None
    company_name: str | None
    location: str | None
    extras: dict[str, Any]
    is_closed: bool = False  # NEW — default to False (open)
```

### 2. Backend — Update Scrapers

**Files**: `scrapers/upwork.py`, `scrapers/linkedin.py`

Map the relevant field from each scraper's raw output to `is_closed`:

For Upwork (example):
```python
is_closed=raw_job.get("status") == "closed" or not raw_job.get("isOpen", True)
```

For LinkedIn (example):
```python
is_closed=raw_job.get("isApplicationExpired", False) or raw_job.get("applyType") == "Expired"
```

Also update the platform config `field_mappings` in:
- `configs/platforms/upwork.json`
- `configs/platforms/linkedin.json`

### 3. Backend — Pre-filter Step in Pipeline

**File**: `services/pipeline.py`

Add a closed-jobs filter step in `_run_platform()` (after keyword filter, before evaluation — same location as the language filter from Task 02):

```python
# Filter closed jobs
for job in jobs_to_evaluate:
    if job.is_closed:
        jobs_skipped_closed += 1
        closed_skipped_jobs.append(job)
        continue
    filtered_jobs.append(job)
jobs_to_evaluate = filtered_jobs
```

Store closed jobs in the skipped jobs auto-list with `skip_reason='job_closed'`.

### 4. Backend — Database Migration

**New file**: `db/migrations/014_add_is_closed.sql`

```sql
ALTER TABLE job_results
  ADD COLUMN IF NOT EXISTS is_closed BOOLEAN DEFAULT FALSE;
```

### 5. Backend — PipelineStats Update

**File**: `services/pipeline.py`

Add `jobs_skipped_closed` to `PipelineStats`:

```python
jobs_skipped_closed: int = 0
```

### 6. Backend — Repository Update

**File**: `repositories/job_result.py`

- Update `insert()` to accept `is_closed` parameter
- Update the row type

### 7. Frontend — Closed Jobs in Skipped List

**File**: `frontend/src/components/list-manager.tsx`

When viewing skipped jobs, show a "Closed" badge for jobs with `skip_reason='job_closed'`.

## Deferral Plan (if scraper does NOT provide the data)

If the investigation reveals that neither scraper provides a reliable `is_closed` or equivalent field:

1. **Do NOT implement this feature** — do not use AI to guess whether a job is still open (too unreliable, wastes API credits)
2. Add a note to this task file: "Deferred — scrapers do not provide job status data. Revisit when Apify actors add this field."
3. Consider adding a manual "Mark as Closed" button in the frontend as a stopgap

## Files to Modify

| File | Change |
|------|--------|
| `scrapers/base.py` | Add `is_closed` field to `NormalizedJob` |
| `scrapers/upwork.py` | Map scraper field to `is_closed` (if available) |
| `scrapers/linkedin.py` | Map scraper field to `is_closed` (if available) |
| `configs/platforms/upwork.json` | Add field mapping for closed status |
| `configs/platforms/linkedin.json` | Add field mapping for closed status |
| `services/pipeline.py` | Add closed-jobs pre-filter step |
| `db/migrations/014_add_is_closed.sql` | **New file** — add `is_closed` column |
| `repositories/job_result.py` | Update for new column |
| `frontend/src/components/list-manager.tsx` | Show "Closed" badge in skipped jobs |

## Acceptance Criteria

- [ ] Investigation completed: documented whether scrapers provide closed-status data
- [ ] If data available: `is_closed` field added to `NormalizedJob` and mapped from scrapers
- [ ] If data available: pipeline skips closed jobs and stores them in the skipped list
- [ ] If data NOT available: feature is deferred with documentation explaining why
- [ ] Skipped jobs list shows "Closed" badge or "Job no longer accepting applications" reason
- [ ] `PipelineStats` includes `jobs_skipped_closed` count (if implemented)
- [ ] No AI-based guessing of job status — only deterministic field mapping

## Dependencies

- **Depends on**: Task 02 (Language Filtering) — reuses the skipped jobs list mechanism and `skip_reason` column
- **Blocks**: None
