# DB-12: exists() Is a Redundant Round-Trip

- **Phase:** improvements
- **Priority:** P4 (Low)
- **Status:** DONE
- **Depends on:** None

## Problem

`JobResultRepository.exists()` in `repositories/job_result.py:81–93` performs a separate SELECT before inserting. `insert()` already handles duplicates via `ON CONFLICT DO NOTHING` and returns `None` when a duplicate is skipped. Any caller using `exists()` + `insert()` in sequence does an unnecessary extra network round-trip.

## Approach

1. Search for all call sites of `exists()` across the codebase.
2. If no caller uses it independently of `insert()`, remove the method entirely.
3. If callers exist that need a standalone existence check without inserting, document why the round-trip is intentional and keep the method.

## Files

- `repositories/job_result.py:81–93` — remove `exists()` if unused standalone
- `services/pipeline.py` — likely caller; verify and update if needed

## Implementation Notes

- Search for `\.exists(` in the codebase to find all call sites.
- The `insert()` method already returns `None` for duplicates, which serves the same purpose for the scrape pipeline's dedup logic.
- Removing dead code reduces maintenance burden and eliminates confusion about the correct dedup path.
