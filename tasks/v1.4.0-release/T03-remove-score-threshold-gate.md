# T03 - Remove Score Threshold Gate on Manual Evaluation

## Priority
High

## Status
.Done

## Description
Currently, clicking "Evaluate" on a job with a score below `SCORE_THRESHOLD` (default 5) returns a 422 error with message "Job score (X) is below evaluation threshold". Users should be able to manually evaluate any job regardless of its score — the threshold is a useful optimization for bulk/pipeline evaluation, but manual evaluation should always work.

## Context
- `core/evaluator.py` line 169-199: `Evaluator.evaluate_full()` checks `if existing_score < self._score_threshold` and returns `EvaluationResult.from_score(existing_score)` (all eval fields None) instead of calling Claude.
- `api/routes/api_results.py` line 400-419: `api_evaluate_result` calls `evaluator.evaluate_full()`, then checks `if eval_result.evaluation is None` and raises HTTP 422.
- `api/routes/api_results.py` line 446-585: `api_evaluate_bulk` also calls `evaluate_full()` and counts `skipped_low_score` — this bulk behavior should remain unchanged (threshold skipping is reasonable for bulk).
- The `SCORE_THRESHOLD` value comes from `configs/settings.json` via `core/settings.py`.

## Acceptance Criteria
- [x] Clicking "Evaluate" on any job, regardless of score, triggers a full Pass 2 evaluation and returns the result
- [x] The bulk evaluation endpoint still skips low-score jobs (keeps `skipped_low_score` behavior)
- [x] The `evaluate_full` method gains a `force: bool = False` parameter that bypasses the threshold check
- [x] The 422 error for low-score manual evaluation is removed
- [x] Frontend "Evaluate" button already works for all jobs with `evaluation === null && score !== null` — no client changes needed

## Implementation Notes

### Backend changes

1. **Modify `core/evaluator.py`** — `Evaluator.evaluate_full()` method (line 169):
   - Add `force: bool = False` parameter
   - Change the threshold check from:
     ```python
     if existing_score < self._score_threshold:
     ```
     to:
     ```python
     if existing_score < self._score_threshold and not force:
     ```
   - Add logging when forcing: `logger.info("Forced full evaluation for '%s' (score=%d < threshold=%d)", job.title, existing_score, self._score_threshold)`

2. **Modify `api/routes/api_results.py`** — `api_evaluate_result` endpoint (line 331):
   - Change `evaluator.evaluate_full(job, platform_context, result.score)` to `evaluator.evaluate_full(job, platform_context, result.score, force=True)`
   - Remove the 422 check at lines 415-419:
     ```python
     # REMOVE THIS BLOCK:
     if eval_result.evaluation is None:
         raise HTTPException(
             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
             detail=f"Job score ({result.score}) is below evaluation threshold",
         )
     ```
   - This block is no longer needed since `force=True` guarantees a full evaluation (unless Claude itself fails, which is caught by the existing try/except)

3. **No changes to bulk evaluation** — `api_evaluate_bulk` (line 446) should continue calling `evaluate_full(job, platform_context, result.score)` without `force=True`. The `skipped_low_score` counter and behavior remain.

### Frontend changes
- None required. The "Evaluate" button in `result-row.tsx` (line 74) already shows for `evaluation === null && score !== null`, so low-score jobs already display the button.

## Dependencies
- None

## Files to Modify/Create
- `core/evaluator.py` (modify — add `force` parameter to `evaluate_full`)
- `api/routes/api_results.py` (modify — pass `force=True`, remove 422 check)

## Tests
- Unit test: `Evaluator.evaluate_full(force=True)` with score below threshold runs Pass 2 and returns full result
- Unit test: `Evaluator.evaluate_full(force=False)` with score below threshold returns score-only result (existing behavior preserved)
- API test: `POST /api/results/{id}/evaluate` with low-score job returns 200 with full evaluation (not 422)
- API test: `POST /api/results/evaluate-bulk` still skips low-score jobs and reports `skipped_low_score`

(End of file - total 70 lines)