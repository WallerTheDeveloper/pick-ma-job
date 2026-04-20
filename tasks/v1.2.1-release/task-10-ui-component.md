# Task 10 — Create CompanyBlacklistCard UI component

**Size:** M  
**Status:** done

## Goal

Build `frontend/src/components/company-blacklist-card.tsx` — a self-contained shadcn Card for managing the blacklist.

## UI Layout

```
┌─────────────────────────────────────────────┐
│ Blacklisted Companies                        │
│─────────────────────────────────────────────│
│ [_________________ input ___] [Add]          │
│ "Matched case-insensitively as substrings.   │
│  Minimum 3 characters."                      │
│─────────────────────────────────────────────│
│ ● Google                           [🗑]      │
│ ● Acme Corp                        [🗑]      │
│ (empty state: "No companies blacklisted yet")│
└─────────────────────────────────────────────┘
```

## Behaviour

- **Add:** Trim input, validate ≥ 3 chars client-side before calling mutation. Show inline error on duplicate (409) or validation failure.
- **Remove:** Immediately call `useRemoveBlacklistEntry` on trash icon click (no confirmation needed — list is easily re-addable).
- **Loading state:** Show skeleton or spinner while `useCompanyBlacklist` is loading.
- **Empty state:** "No companies blacklisted yet." text.
- **Error state:** Surface query/mutation errors inline.
- **After add:** Clear the input field on success.

## shadcn components to use

`Card`, `CardHeader`, `CardTitle`, `CardContent`, `Input`, `Button`, `Badge` (or simple text rows).

## Success Criteria

- Input shorter than 3 chars shows inline error without hitting the API.
- Duplicate shows inline error from the API 409 response.
- Trash icon removes the entry and the list updates.
- Component renders correctly with 0 entries (empty state).
- No TypeScript errors.
