# Task 11 — Add CompanyBlacklistCard to Profile page

**Size:** S  
**Status:** done

## Goal

Render `<CompanyBlacklistCard />` on `frontend/src/pages/profile.tsx` below the existing profile form.

## Change

In `profile.tsx`, import and place `<CompanyBlacklistCard />` after the existing profile `<Card>` block, separated by a spacing div (e.g. `<div className="mt-6" />`  or equivalent Tailwind spacing).

## Notes

- The blacklist card manages its own state via TanStack Query — it does not interact with the profile save/submit flow.
- No prop passing needed; the card is self-contained.

## Success Criteria

- Profile page renders the blacklist card below the profile form.
- Saving the profile form does not affect the blacklist card and vice versa.
- No layout breakage on mobile or desktop viewport.
