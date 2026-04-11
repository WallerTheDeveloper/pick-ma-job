# CR-11: _SORT_CLAUSES Is a Mutable Class Attribute

- **Phase:** hardening
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

In `repositories/job_result.py:95-100`, `_SORT_CLAUSES` is defined as a mutable `dict[str, str]` class attribute on `JobResultRepository`. Any code with a reference to the class or an instance can mutate this dict, which would affect all subsequent queries. The mutable class attribute also violates the project's immutability convention.

## Approach

1. Move `_SORT_CLAUSES` to module level above the class.
2. Annotate with `Final` from `typing`: `_SORT_CLAUSES: Final[dict[str, str]] = { ... }`.
3. For true immutability, wrap in `types.MappingProxyType`: `_SORT_CLAUSES: Final = MappingProxyType({...})`.

## Files

- `repositories/job_result.py:95-100` — move to module level, annotate with `Final`, wrap in `MappingProxyType`
- `repositories/job_result.py:133` — update reference from `self._SORT_CLAUSES` to module-level `_SORT_CLAUSES`

## Implementation Notes

- This task overlaps with security-2 which also addresses this dict. Coordinate — ideally implement both in the same PR.
- `MappingProxyType` raises `TypeError` on mutation attempts at runtime, which is stronger than `Final` (type-checker hint only).
- Import: `from types import MappingProxyType` and `from typing import Final`.
