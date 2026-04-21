# Task 5 — Observability: Structured Logs + run_id Context

**Size:** M  
**Status:** todo  
**Priority:** HIGH

## Goal

Add `run_id` and `user_id` to every log line emitted during a pipeline run, and emit structured (JSON) logs so runs can be traced end-to-end. Currently errors are logged but cannot be correlated to a specific run or user.

## Problem

- `PipelineService` and `Evaluator` log with plain `logging.getLogger(__name__)` — no `run_id`
- Log lines from different concurrent runs interleave with no way to group them
- No metrics for: Claude latency, token usage, per-platform job counts, dedup hit rate

## Changes

**`core/context.py`** — new file
```python
import contextvars
run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="-")
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="-")
```

**`core/logging.py`** — new file
- `ContextFilter(logging.Filter)`: adds `run_id` and `user_id` from `contextvars` to every `LogRecord`
- JSON formatter that emits `{"time": ..., "level": ..., "logger": ..., "run_id": ..., "user_id": ..., "msg": ...}`

**`main.py`**
- Configure root logger to use `ContextFilter` and JSON formatter on startup

**`services/run_manager.py`** (or `pipeline.py`)
- Set `run_id_var` and `user_id_var` at the start of each background task before calling `PipelineService.run_pipeline`

**`core/evaluator.py`**
- Log Pass 1 and Pass 2 durations:
  ```python
  logger.info("llm_call", extra={"pass": 1, "model": model, "duration_ms": ..., "tokens": ...})
  ```

## Success Criteria

- Every log line emitted during a pipeline run includes `run_id` and `user_id` fields
- Log output is valid JSON (verify with `python -c "import json; [json.loads(l) for l in open('app.log')]"`)
- Pass 1 and Pass 2 durations are logged per job
- `run_id` propagates correctly when two pipeline runs execute concurrently (each run's logs show its own ID)
