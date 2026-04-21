# Task 10 — Fix Pass-1 Parse Failure Silent Fallback

**Size:** S  
**Status:** todo  
**Priority:** MEDIUM

## Goal

When Pass 1 output is unparseable, the current fallback returns `SCORE_THRESHOLD` (5), which passes the `>= 5` check and silently triggers Pass 2. A bug in the scoring prompt becomes an invisible 2× cost regression.

## Problem

In `core/evaluator.py → _parse_score`:
```python
except (ValueError, KeyError):
    return SCORE_THRESHOLD  # silently passes the gate
```

## Changes

**`core/evaluator.py`**
- Change fallback to return `SCORE_THRESHOLD - 1` (i.e. below the gate, default → 4):
  ```python
  except (ValueError, KeyError):
      logger.warning("pass1_parse_failed", extra={"raw": raw_text[:200]})
      return self._score_threshold - 1
  ```
- Add a `parse_failures` counter to `EvaluationResult` (or emit as a log metric) so the rate is observable

**`services/pipeline.py`**
- Count jobs where `result.pass1_parse_failed is True` into `PipelineStats.jobs_failed` or a new `jobs_score_parse_failed` counter

## Success Criteria

- A mocked Pass 1 response that returns unparseable text results in the job being skipped (not evaluated in Pass 2)
- A log warning is emitted for every parse failure with the raw truncated response
- `jobs_score_parse_failed` (or `jobs_failed`) counter increments in the run result
