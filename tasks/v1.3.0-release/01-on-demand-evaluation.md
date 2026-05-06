# Task 01: On-Demand Evaluation

## Goal

The pipeline should scrape and store jobs automatically but only compute the relevancy score (Pass 1). The full evaluation (Pass 2) should only happen when the user explicitly clicks "Evaluate" on a job. This saves API costs by deferring expensive evaluations until the user confirms interest.

## Current Behavior

- `services/pipeline.py` `_evaluate_and_store()` runs both Pass 1 (score) and Pass 2 (full eval) in sequence for every job
- `core/evaluator.py` `evaluate()` is a two-pass system:
  - Pass 1 (`_call_score`): lightweight prompt → single integer 1–10, `max_tokens=16`
  - Pass 2 (`_assemble_system_prompt` + `generate_json_with_metadata`): full JSON evaluation, `max_tokens=2048` — only runs if Pass 1 score >= `SCORE_THRESHOLD` (5)
- All jobs are stored in `job_results` table with full `evaluation` JSONB (or NULL for low-score jobs)
- Frontend `result-row.tsx` displays inline evaluation data: summary, evaluation text, flags, scratchpad when expanded
- `PipelineStats` tracks `jobs_evaluated` (Pass 2 completed) and `jobs_skipped_low_score` (Pass 1 score below threshold)

## Required Changes

### 1. Backend — Pipeline: Score Only, No Full Eval

**File**: `services/pipeline.py`

Modify `_evaluate_and_store()` to only run Pass 1 (score). Store jobs with `score` populated but `evaluation=NULL`. The full evaluation is no longer run during pipeline execution.

- Call `evaluator._call_score(job)` directly instead of `evaluator.evaluate(job, ...)`
- The pipeline stores `score=result.relevancy_score, evaluation=None` for ALL jobs regardless of score
- Remove the branching logic that checks `result.evaluation is None` vs not — it's always None now
- Keep the dedup, blacklist, and keyword pre-filter steps unchanged

### 2. Backend — Expose `evaluate_full()` Method

**File**: `core/evaluator.py`

Expose a public method `evaluate_full()` that runs Pass 2 only (given a job and its existing score). This is the method called by the new API endpoints:

```python
async def evaluate_full(
    self,
    job: NormalizedJob,
    platform_context: dict,
    existing_score: int,
) -> EvaluationResult:
    """Run Pass 2 (full evaluation) for a job that already has a score from Pass 1.
    
    Only runs if existing_score >= self._score_threshold.
    Returns EvaluationResult.from_score(existing_score) if below threshold.
    """
```

Keep the existing `evaluate()` method but mark it as deprecated or internal — it's no longer used by the pipeline.

### 3. Backend — New API Endpoints

**File**: `api/routes/api_results.py`

Add two new endpoints:

#### `POST /api/results/{result_id}/evaluate`

Evaluates a single job by its result ID. Request: no body needed (result_id is in URL path).

Behavior:
1. Fetch the `job_result` by ID, verify it belongs to the authenticated user
2. Verify `evaluation IS NULL` (not already evaluated)
3. Load the user's profile and platform context
4. Reconstruct a `NormalizedJob` from the stored job data (title, description, URL, etc.)
5. Call `evaluator.evaluate_full(job, platform_context, existing_score)`
6. Update the `job_result` row with the evaluation JSON
7. Return the updated `JobResultResponse`

#### `POST /api/results/evaluate-bulk`

Evaluates multiple jobs. Request body:

```json
{
  "result_ids": ["uuid1", "uuid2", ...],  // specific IDs to evaluate
  "filter": {                              // OR filter-based (mutually exclusive with result_ids)
    "platform": "upwork",                  // optional
    "min_score": 5,                        // optional
    "status": "new"                        // optional
  }
}
```

Behavior:
1. Resolve the set of job result IDs to evaluate (either from `result_ids` or by querying with `filter`)
2. Filter to only unevaluated jobs (`evaluation IS NULL`)
3. Process with concurrency limit (reuse `settings.evaluation_concurrency`)
4. Return a streaming/SSE response with progress updates, or return a summary response with counts

Recommendation: Return a summary response (not SSE) for simplicity:

```json
{
  "total": 25,
  "evaluated": 20,
  "skipped_low_score": 3,
  "failed": 2,
  "updated_ids": ["uuid1", "uuid2", ...]
}
```

### 4. Backend — New API Schemas

**File**: `api/schemas.py`

Add:

```python
class BulkEvaluationRequest(BaseModel):
    result_ids: list[UUID] | None = None
    filter: dict | None = None  # platform, min_score, status filters

class EvaluationResponse(BaseModel):
    result: JobResultResponse

class BulkEvaluationResponse(BaseModel):
    total: int
    evaluated: int
    skipped_low_score: int
    failed: int
    updated_ids: list[UUID]
```

### 5. Backend — Repository Update

**File**: `repositories/job_result.py`

Add a method to update evaluation for a single job:

```python
async def update_evaluation(
    self,
    result_id: UUID,
    user_id: UUID,
    evaluation: dict,
) -> JobResultRow | None:
    """Update the evaluation JSON for a job result. Returns None if not found or not owned by user."""
```

### 6. Backend — PipelineStats Update

**File**: `services/pipeline.py`

Update `PipelineStats`:
- Remove `jobs_evaluated` field (evaluation no longer happens in-pipeline)
- Rename `jobs_skipped_low_score` to clarify it's about scoring, not evaluation skipping
- All stored jobs now have the same structure: score + NULL evaluation

### 7. Frontend — Evaluate Button in Result Row

**File**: `frontend/src/components/result-row.tsx`

Add an "Evaluate" button in the action area (right side of the row, alongside "Customize CV" and other actions):

- The button should ONLY appear when `result.evaluation === null` and `result.score !== null`
- Button label: "Evaluate" (default state), "Evaluating..." with spinner (loading state)
- When clicked, call the evaluate API endpoint
- On success, update the result in React Query cache to show the new evaluation data
- On error, show a toast notification
- The action area should be a flex row with gap for extensibility:
  ```tsx
  <div className="flex items-center gap-2">
    {showEvaluate && <Button ...>Evaluate</Button>}
    {showCustomizeCV && <Button ...>Customize CV</Button>}
    <AddToListMenu ... />
  </div>
  ```

### 8. Frontend — Inline Loading State

**File**: `frontend/src/components/result-row.tsx`

While evaluating, show a thin progress indicator at the bottom of the collapsible card:
- A small spinner or shimmer animation
- Text: "Evaluating with AI..."
- Should be responsive to any page size (use CSS, not fixed positioning)

### 9. Frontend — Bulk Evaluate Actions

**File**: `frontend/src/pages/results.tsx`

Add "Evaluate All" and "Evaluate Selected" options to the existing floating bulk action bar at the bottom of the results page:
- "Evaluate All" calls the bulk evaluate endpoint with a filter for all unevaluated jobs on the current page/filter
- "Evaluate Selected" calls bulk evaluate with the selected result IDs
- Both should show a progress toast: "Evaluating X jobs..."
- On completion, invalidate the results query to refresh the list

### 10. Frontend — API Hooks

**File**: `frontend/src/hooks/use-results.ts` (or new `use-evaluate.ts`)

Add:
```typescript
function useEvaluateJob() {
  // POST /api/results/{id}/evaluate
  // Returns mutation with loading state
}

function useBulkEvaluate() {
  // POST /api/results/evaluate-bulk
  // Returns mutation with loading state
}
```

### 11. Frontend — Type Updates

**File**: `frontend/src/types/schemas.ts`

Add types for `BulkEvaluationRequest`, `BulkEvaluationResponse`, `EvaluationResponse`.

## Files to Modify

| File | Change |
|------|--------|
| `services/pipeline.py` | Remove Pass 2 from `_evaluate_and_store()`; score only |
| `core/evaluator.py` | Add public `evaluate_full()` method for on-demand full eval |
| `api/routes/api_results.py` | Add `POST /api/results/{id}/evaluate` and `POST /api/results/evaluate-bulk` |
| `api/schemas.py` | Add `BulkEvaluationRequest`, `EvaluationResponse`, `BulkEvaluationResponse` |
| `api/deps.py` | Inject evaluator service if not already available |
| `repositories/job_result.py` | Add `update_evaluation()` method |
| `frontend/src/components/result-row.tsx` | Add Evaluate button, inline loading, action bar refactor |
| `frontend/src/pages/results.tsx` | Add bulk evaluate actions to floating bar |
| `frontend/src/hooks/use-results.ts` or new `use-evaluate.ts` | API mutation hooks |
| `frontend/src/types/schemas.ts` | New TypeScript types |

## Acceptance Criteria

- [x] Pipeline stores all jobs with score but `evaluation=NULL` — no Pass 2 during pipeline
- [x] "Evaluate" button appears on result rows that have a score but no evaluation
- [x] Clicking "Evaluate" triggers a single-job API call and shows inline loading
- [x] On success, the row expands to show the full evaluation (summary, flags, recommendation, etc.)
- [x] "Evaluate All" and "Evaluate Selected" appear in the floating bulk action bar
- [x] Bulk evaluation processes jobs with concurrency limit and reports progress
- [x] API endpoints validate user ownership of the job results
- [x] Below-threshold jobs (score < 5) return a score-only result even on explicit evaluation
- [x] Already-evaluated jobs are skipped in bulk evaluation

## Dependencies

- **None** — this task is independent and can be done first
- Tasks 02 (Language Filtering) will add another pre-filter step that runs before scoring
- Task 07 (Rate Limit Handling) affects the same `LLMClient` used for evaluation calls
