# P2-2: Pipeline Loading Animation

- **Phase:** 2 — UX Polish
- **Priority:** P1 — High
- **Status:** DONE
- **Depends on:** P2-1 (shares run-status component)

## Problem

No visual feedback while pipeline is running. User sees static text and doesn't know if anything is happening.

## Changes Required

### `frontend/src/pages/dashboard.tsx`

- "Run Pipeline" button: show a spinner icon inside the button while `isRunning` is true
- Disable button with spinner, not just "Running..." text

### `frontend/src/components/run-status.tsx`

- Replace static text "Waiting to start..." and "Scraping and evaluating jobs..." with:
  - Animated spinner + descriptive text
  - Optional: skeleton shimmer on the stats grid while waiting for completion

## Acceptance Criteria

- [x] Run Pipeline button shows spinner while running
- [x] RunStatus card has animated loading indicator during pending/running
- [x] Clear visual distinction between "loading" and "done" states
