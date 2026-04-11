# FE-9: key={index} on User-Reorderable Profile Lists

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

In `src/pages/profile.tsx:376,432`, background entries and notable projects use `key={i}` (array index). When items are removed from the middle of the list, React reuses DOM nodes for the wrong items, corrupting controlled input state (e.g., editing item 2 after deleting item 1 shows item 3's data).

## Approach

1. Generate a stable unique ID (e.g., `crypto.randomUUID()`) when each background entry or notable project is created.
2. Store the ID alongside the form data in component state.
3. Use the stable ID as the React key instead of the array index.

## Files

- `frontend/src/pages/profile.tsx:376` — background entries key
- `frontend/src/pages/profile.tsx:432` — notable projects key

## Implementation Notes

- If the form state is a plain array of objects, add an `id` field. Existing data loaded from the backend can have IDs generated on load.
- `crypto.randomUUID()` is available in all modern browsers. No polyfill needed.
