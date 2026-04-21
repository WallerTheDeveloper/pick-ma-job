# Task 8 — Collapse PlatformResult / PipelineRunResult into PipelineStats Monoid

**Size:** S  
**Status:** todo  
**Priority:** MEDIUM

## Goal

Replace the two near-identical result dataclasses with a single `PipelineStats` that supports `+` (monoid), eliminating the manual reducer block and making it trivial to add new counters.

## Problem

`PlatformResult` and `PipelineRunResult` share the same ~8 counter fields. Adding a new counter (e.g. `jobs_failed`) requires updating both dataclasses, the per-platform accumulation, and the final reducer in `run_pipeline`.

## Changes

**`services/pipeline.py`**
```python
@dataclass(frozen=True)
class PipelineStats:
    jobs_found: int = 0
    jobs_skipped_duplicate: int = 0
    jobs_skipped_blacklisted: int = 0
    jobs_skipped_keyword: int = 0
    jobs_evaluated: int = 0
    jobs_failed: int = 0
    jobs_alerted: int = 0

    def __add__(self, other: "PipelineStats") -> "PipelineStats":
        return PipelineStats(
            jobs_found=self.jobs_found + other.jobs_found,
            # ... all fields
        )

    @classmethod
    def zero(cls) -> "PipelineStats":
        return cls()
```

- Remove `PlatformResult` and `PipelineRunResult`
- `_run_platform` returns `PipelineStats`
- `run_pipeline` aggregates: `total = sum(platform_stats, PipelineStats.zero())`
- Update `api/schemas.py` `RunStatusResponse` to reflect the unified field names if changed

## Success Criteria

- `PlatformResult` and `PipelineRunResult` no longer exist in the codebase
- Adding a new counter field to `PipelineStats` requires changing only one dataclass
- `run_pipeline` aggregation is `sum(results, PipelineStats.zero())` with no manual field summing
