# T07 - Add Company Name Badge to Result Row

## Priority
Low

## Status
.Done

## Description
Show the company name as a small badge on each result row, next to the existing platform badge. This provides quick visual identification of the employer/company without expanding the row.

## Context
- `frontend/src/components/result-row.tsx` (line 139-141) shows platform badge and other badges (language, closed).
- `NormalizedJob` in `scrapers/base.py` has a `company_name` field (attributed via `@property effective_company_name`).
- The pipeline stores job data in `job_results` table. Currently `company_name` may not be a first-class column — it might be stored in the `extras` JSONB field.
- `api/schemas.py` `JobResultResponse` (line 83-96) does not currently include `company_name`.
- `repositories/job_result.py` `JobResultRow` (line 26-39) does not include `company_name`.

## Acceptance Criteria
- [ ] `company_name` column exists in `job_results` table (via DB migration)
- [ ] `JobResultResponse` in `api/schemas.py` includes `company_name: str | None = None`
- [ ] All places in `api/routes/api_results.py` that construct `JobResultResponse` include `company_name`
- [ ] `JobResultRow` in `repositories/job_result.py` includes `company_name`
- [ ] Frontend `jobResultSchema` in `types/schemas.ts` includes `company_name`
- [ ] Result row displays company name Badge when `result.company_name` is truthy
- [ ] Badge uses `variant="outline"` and `className="text-xs"` consistent with the platform badge

## Implementation Notes

### Backend

1. **Create DB migration `db/migrations/017_company_name.sql`**:
   ```sql
   ALTER TABLE job_results ADD COLUMN IF NOT EXISTS company_name TEXT;
   ```
   Also update the pipeline insert in `repositories/job_result.py` to include `company_name` in the INSERT query. Check `NormalizedJob.company_name` and `NormalizedJob.effective_company_name` to see how the field is populated.

2. **Update `repositories/job_result.py`**:
   - Add `company_name: str | None = None` to `JobResultRow` dataclass
   - Update `_row_to_job_result()` to read `row.get("company_name")`
   - Update all INSERT queries to include `company_name` (the `insert()` method, and any other places that create job result rows)
   - Update SELECT queries if needed (the `*` pattern should pick up the new column automatically)

3. **Update `api/schemas.py`** — add `company_name: str | None = None` to `JobResultResponse`

4. **Update `api/routes/api_results.py`** — add `company_name=r.company_name` to all `JobResultResponse(...)` constructor calls (lines 139-151, 184-196, 429-443, and any other places)

5. **Update `services/pipeline.py`** — ensure the `insert()` call in `_evaluate_and_store()` passes `company_name=job.effective_company_name` (the `NormalizedJob` already provides this)

### Frontend

1. **Update `frontend/src/types/schemas.ts`** — add `company_name: z.string().nullable().optional()` to `jobResultSchema`

2. **Update `frontend/src/components/result-row.tsx`** — after the platform Badge (line 141):
   ```tsx
   {result.company_name && (
     <Badge variant="outline" className="text-xs">
       {result.company_name}
     </Badge>
   )}
   ```

## Dependencies
- None

## Files to Modify/Create
- `db/migrations/017_company_name.sql` (new)
- `repositories/job_result.py` (modify — add `company_name` to row, insert, and queries)
- `api/schemas.py` (modify — add `company_name` to `JobResultResponse`)
- `api/routes/api_results.py` (modify — include `company_name` in all response constructions)
- `services/pipeline.py` (modify — pass `company_name` to insert)
- `frontend/src/types/schemas.ts` (modify — add `company_name` to schema)
- `frontend/src/components/result-row.tsx` (modify — add badge)

## Tests
- DB migration: `017_company_name.sql` applies cleanly
- API response for job results includes `company_name` field
- Result row renders company name badge when `company_name` is present
- Result row renders without error when `company_name` is null/undefined