# H6: Fix Mutable List Fields on _EMPTY_PROFILE Singleton

- **Phase:** High
- **Priority:** P1 — Shared State Mutation Risk
- **Status:** DONE
- **Depends on:** None

## Problem

`services/profile.py:33–45` defines `_EMPTY_PROFILE` as a module-level `ProfileData` singleton. `ProfileData` is a `frozen=True` dataclass, but its fields (`primary_skills`, `secondary_skills`, etc.) are plain `list[str]`. The `frozen=True` flag only prevents field *reassignment* — it does **not** prevent in-place mutation of the list objects themselves.

Any caller that receives this shared instance and calls `.append()` on a skill list corrupts the singleton for all subsequent callers in the same process lifetime.

`empty_profile_data()` (line 89) returns this singleton rather than a fresh instance.

## Solution

1. **`services/profile.py`** — remove the `_EMPTY_PROFILE` module-level constant.

2. Change `empty_profile_data()` to construct and return a fresh `ProfileData` instance on every call:
   ```python
   def empty_profile_data() -> ProfileData:
       return ProfileData(
           role=None,
           experience=None,
           rate=None,
           primary_skills=[],
           secondary_skills=[],
           tertiary_skills=[],
           not_a_good_fit=[],
           background=[],
           notable_projects=[],
           languages=[],
           rubric={},
       )
   ```

## Files

- `services/profile.py`

## Acceptance Criteria

- [ ] `_EMPTY_PROFILE` module-level singleton is removed
- [ ] `empty_profile_data()` returns a new `ProfileData` instance on every call
- [ ] Mutating the result of one `empty_profile_data()` call does not affect any other call
