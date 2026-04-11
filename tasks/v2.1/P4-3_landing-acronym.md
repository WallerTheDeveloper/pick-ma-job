# P4-3: Explain "Pick MA Job" Acronym on Landing Page

- **Phase:** 4 — Features
- **Priority:** P3 — Low
- **Status:** DONE
- **Depends on:** None

## Problem

The product name "Pick MA Job" is unclear to new visitors. The acronym "MA" (Most Appropriate) is not explained anywhere on the landing page, causing confusion about what the product does.

## Files

- `frontend/src/pages/landing.tsx` — landing page component

## Fix

Add a brief clarification near the hero/headline area. Options:

1. **Subtitle under the logo/title:** `"Pick MA Job — Pick the Most Appropriate Job for you"`
2. **Inline parenthetical:** `"Pick MA (Most Appropriate) Job"`
3. **Tagline:** Keep the short name as the brand, add a full tagline below it

Choose whichever fits the current layout. The goal is that a first-time visitor immediately understands the name without guessing.

## Acceptance Criteria

- [x] Landing page clearly communicates that "MA" stands for "Most Appropriate"
- [x] The explanation is visible without scrolling (above the fold)
- [x] The addition is concise — one line or a short phrase, not a paragraph
