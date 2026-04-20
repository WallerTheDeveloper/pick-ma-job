# C3: Document and Harden Dynamic SQL Column Interpolation Pattern

- **Phase:** Critical
- **Priority:** P0 — Structural Security Risk
- **Status:** DONE
- **Depends on:** None

## Problem

`repositories/job_result.py` builds SQL clauses using f-strings that interpolate column names:

```python
f"score >= ${idx}"
f"platform = ${idx}"
# ORDER BY {order}  ← from a MappingProxyType allowlist
```

The column names and `ORDER BY` values are all hardcoded literals or drawn from a compile-time allowlist — so this is **not a live SQL injection vector today**. However, the structural pattern is dangerous: a future contributor adding a user-supplied column name would silently introduce injection.

Affected locations:
- `repositories/job_result.py:228–235` (`_build_filter`)
- `repositories/job_result.py:309` (`bulk_update_status`)
- `repositories/job_result.py:358` (`bulk_delete`)
- `repositories/job_result.py:407` (`count_by_user`)

## Solution

1. **At every dynamic SQL construction site** — add a comment that makes the safety invariant explicit:
   ```python
   # SAFETY: column names below are hardcoded literals, never derived from
   # user-controlled input. If you add a column name here from an external
   # source, use a compile-time allowlist (e.g. MappingProxyType) and verify
   # the value before interpolation.
   ```

2. **`_build_filter` / `_build_keyset_condition`** — consider extracting the column-name-to-placeholder mapping into a `MappingProxyType` allowlist (matching the existing `_SORT_CLAUSES` pattern), making the safety invariant structurally enforced rather than comment-reliant.

3. Verify `_SORT_CLAUSES` allowlist is used correctly and no untrusted value bypasses it.

## Files

- `repositories/job_result.py`

## Acceptance Criteria

- [x] All dynamic SQL construction sites have a safety-invariant comment
- [x] Column names used in WHERE clauses are either literals or drawn from an explicit allowlist
- [x] No user-controlled string is ever interpolated directly into SQL text
