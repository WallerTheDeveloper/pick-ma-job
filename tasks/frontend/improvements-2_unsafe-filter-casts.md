# FE-10: Unsafe `as` Casts on Backend Filter Data

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** TODO
- **Depends on:** fixes-3_zod-runtime-validation

## Problem

In `src/pages/search-config.tsx:146-149`, backend filter data is cast with `as string[] | undefined` without runtime validation. If the backend returns an unexpected shape (e.g., a string instead of an array), the UI silently breaks when trying to `.map()` over it.

## Approach

1. Define a Zod schema for the Apify filter shape (at minimum: `experienceLevel`, `jobType` as optional string arrays).
2. Parse the filters through the schema before rendering.
3. Provide sensible defaults (empty arrays) for missing fields.

## Files

- `frontend/src/pages/search-config.tsx:146–149` — replace `as` casts with Zod validation
- `frontend/src/types/schemas.ts` — add filter shape schema (if not covered by fixes-3)

## Implementation Notes

- This naturally pairs with fixes-3 (Zod validation). If fixes-3 is done first, the filter data may already be validated upstream.
- The filter shape varies by platform. A union schema keyed on `platform` would be ideal but a loose record type is acceptable for MVP.
