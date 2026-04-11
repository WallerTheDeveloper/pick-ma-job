# FE-20: Redundant `as string` Cast on Already-String Value

- **Phase:** polish
- **Priority:** P4 (Low)
- **Status:** TODO
- **Depends on:** None

## Problem

In `src/pages/results.tsx:113`, `onValueChange={(val) => updateFilter("status", val as string)}` casts `val` to `string`, but `val` from Radix Select's `onValueChange` is already typed as `string`.

## Approach

Remove the cast: `onValueChange={(val) => updateFilter("status", val)}`.

## Files

- `frontend/src/pages/results.tsx:113` — remove `as string` cast

## Implementation Notes

- Trivial cleanup. No behavioral change.
