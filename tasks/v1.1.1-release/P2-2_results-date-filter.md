# P2-2: Add Date Filter to Results Page

- **Phase:** 2 — Feature
- **Priority:** P2 — Enhancement
- **Status:** DONE
- **Depends on:** None

## Problem

The results page has no way to filter jobs by when they were added. When many results accumulate over time, users cannot easily focus on recently scraped jobs.

## Solution

Add a preset date range filter to the results page filter bar, filtering client-side on the `created_at` field already present in result rows.

### Frontend

1. **`frontend/src/pages/results.tsx`** — add a date range dropdown filter alongside existing filters (keyword search, platform filter).

   Preset options:
   - **All time** (default — no filter)
   - **Today**
   - **Last 7 days**
   - **Last 30 days**

2. Integrate with the existing client-side filter logic: after applying keyword and platform filters, additionally filter out rows where `created_at` falls outside the selected date range.

3. Date comparison logic:
   ```ts
   const now = new Date();
   const cutoff = {
     today: startOfDay(now),           // midnight local time
     last7: subDays(now, 7),
     last30: subDays(now, 30),
   }[selectedRange];
   
   filtered = filtered.filter(r => new Date(r.created_at) >= cutoff);
   ```
   Use plain `Date` arithmetic — no external date library needed unless one is already in the project.

4. The filter state should be local (`useState`) — no URL param or persistent state required.

5. UI: use an existing shadcn/ui `Select` or `DropdownMenu` component to match the rest of the page styling.

### Backend

No backend changes required. `created_at` is already returned with result rows.

## Files

- `frontend/src/pages/results.tsx`

## Acceptance Criteria

- [x] A date range dropdown appears in the results filter bar
- [x] Selecting "Today" shows only results added since midnight local time
- [x] Selecting "Last 7 days" / "Last 30 days" shows correct subsets
- [x] Selecting "All time" shows all results (no filter)
- [x] Date filter composes correctly with keyword and platform filters (all active simultaneously)
- [x] Filter resets to "All time" on page load
