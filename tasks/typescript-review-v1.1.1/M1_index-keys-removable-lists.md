# M1: Replace Array Index Keys on Removable / Updating Lists

- **Phase:** Medium
- **Priority:** P2 — React Correctness
- **Status:** DONE
- **Depends on:** None

## Problem

Two components use `key={i}` (array index) for lists whose items can be removed or updated:

**`frontend/src/components/tag-input.tsx:52`:**
```ts
{value.map((tag, i) => (
  <span key={i} ...>
```
Tags can be removed from any position. When a tag is removed from the middle, all subsequent keys shift by one — React incorrectly reuses DOM nodes, causing focus state, transition animations, and ARIA announcements to misbehave.

**`frontend/src/components/run-status.tsx:83`:**
```ts
{run.result.errors.map((err, i) => (
  <p key={i} ...>{err}</p>
))}
```
If the error list updates between polling intervals, index-based keys cause incorrect diffs.

## Solution

**`tag-input.tsx`:** Use `key={tag}` — tags are already deduplicated on add (`!value.includes(tag)`), so tag values are unique:
```ts
{value.map((tag) => (
  <span key={tag} ...>
```

**`run-status.tsx`:** Use a composite key combining index and a slice of the error string:
```ts
{run.result.errors.map((err, i) => (
  <p key={`${i}-${err.slice(0, 30)}`} ...>{err}</p>
))}
```

## Files

- `frontend/src/components/tag-input.tsx`
- `frontend/src/components/run-status.tsx`

## Acceptance Criteria

- [ ] `tag-input.tsx` uses `key={tag}` instead of `key={i}`
- [ ] `run-status.tsx` uses a stable composite key instead of `key={i}`
- [ ] Removing a tag from the middle of a list does not cause visible focus/animation glitches
- [ ] TypeScript compiles without errors
