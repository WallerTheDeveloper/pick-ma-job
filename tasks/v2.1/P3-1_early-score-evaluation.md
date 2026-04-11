# P3-1: Two-Pass Early Score Evaluation (Token Optimization)

- **Phase:** 3 — Performance
- **Priority:** P2 — Medium
- **Status:** DONE
- **Depends on:** None

## Problem

Currently, Claude generates a full evaluation (scratchpad, evaluation text, recommendation, flags, summary) for every job — including irrelevant ones. Jobs scoring below 5/10 don't need full evaluations, and generating them wastes tokens and increases pipeline cost.

## Approach

Split evaluation into two passes:

**Pass 1 — Score only**
- Send a lightweight prompt asking only for `relevancy_score` (1–10 integer)
- Minimal output, minimal tokens

**Pass 2 — Full evaluation (conditional)**
- Only triggered if Pass 1 score ≥ 5
- Same as current full evaluation prompt

**If score < 5:**
- Store a minimal `job_results` row with just the score, no evaluation fields
- Mark as auto-skipped (e.g., `status = "skipped"` or leave evaluation fields null)
- Log that the job was skipped to avoid confusion

## Files

- `core/evaluator.py` — main evaluation logic; add two-prompt flow
- `configs/prompts/upwork_context.json` — may need a separate scoring-only template
- `configs/prompts/linkedin_context.json` — same
- `repositories/job_result.py` — confirm nullable evaluation fields are acceptable
- `api/schemas.py` — `JobResult` response schema may need to handle null evaluation fields

## Implementation Notes

- Pass 1 prompt should be concise: just job title + description + brief profile summary + "respond with a single integer 1-10"
- Retry logic from the current evaluator applies to Pass 1 too
- Keep both passes in the same `evaluate_job` method or split into `score_job` + `evaluate_job` — either is fine, but keep the interface clean
- The existing `EvaluationResult` dataclass can remain `frozen=True`; just make non-score fields `Optional[str]`

## Acceptance Criteria

- [x] Jobs with Pass 1 score < 5 do not receive a second Claude API call
- [x] Jobs with Pass 1 score ≥ 5 receive the full evaluation as before
- [x] Skipped jobs are stored in `job_results` with their score and null evaluation fields
- [x] Skipped jobs are visible in the UI (evaluation field is null, score is shown — filtered out by default min_score filter)
- [x] Total token usage per pipeline run decreases for datasets with many irrelevant jobs
- [x] No regression in evaluation quality for scored jobs
