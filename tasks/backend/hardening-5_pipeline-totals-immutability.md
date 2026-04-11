# CR-12: totals Dict Mutated Across Async _run_platform Calls

- **Phase:** hardening
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

In `services/pipeline.py:112-129`, `totals` and `errors` are created as mutable dicts/lists and passed by reference into `_run_platform`, which mutates them in-place. This violates the project's immutability convention and is a latent data race if `_run_platform` calls are ever parallelized (e.g., `asyncio.gather`).

## Approach

1. Define a `@dataclass(frozen=True)` result type (e.g., `PlatformResult`) with fields for each counter and an errors list.
2. Have `_run_platform` return a `PlatformResult` instead of mutating shared dicts.
3. In the calling function, accumulate results immutably:
   ```python
   results = [await self._run_platform(...) for config_row in search_configs]
   totals = reduce_platform_results(results)
   ```
4. This also makes the code safe for future parallelization with `asyncio.gather`.

## Files

- `services/pipeline.py:112-129` — replace mutable totals/errors with returned result objects
- `services/pipeline.py` (`_run_platform` method) — update to return a `PlatformResult` dataclass instead of mutating params

## Implementation Notes

- The `PlatformResult` dataclass should be `frozen=True` per project convention.
- A simple `reduce_platform_results` helper can sum all counters and concatenate error lists.
- This is a refactor — behavior should not change. Verify with existing tests.
- Currently the loop is sequential, so the race condition is latent, not active. But the immutability violation is real regardless.
