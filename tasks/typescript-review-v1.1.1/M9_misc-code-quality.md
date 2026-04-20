# M9: Miscellaneous Code Quality Fixes

- **Phase:** Medium
- **Priority:** P3 — Low-Impact Cleanup
- **Status:** DONE
- **Depends on:** M6 (platform Zod schema), M8 (ESLint fix)

## Items

### 1. Magic-number score thresholds in `ScoreBadge`
**File:** `frontend/src/components/score-badge.tsx:10–12`

Score thresholds (`>= 7`, `>= 4`) are hard-coded in the component. These same thresholds appear in the backend rubric (CLAUDE.md). Extract to named constants:

```ts
const SCORE_GOOD_THRESHOLD = 7;
const SCORE_MODERATE_THRESHOLD = 4;
```

Consider placing them in a shared `frontend/src/constants.ts` if they are referenced in multiple places.

---

### 2. `toRunStatusResponse` discards `result` from completed dashboard runs
**File:** `frontend/src/pages/dashboard.tsx:32–41`

The adapter sets `result: null` unconditionally even when a completed run has result data in `PipelineRunInfo`. This means the `RunStatus` component shows no stats for the brief window between page load and the first poll. Pass through the `result` field if it exists:

```ts
result: run.result ?? null,
```

Verify the type alignment between `PipelineRunInfo.result` and `RunResult` first.

---

### 3. Uncontrolled keyword input in `LinkedInFiltersForm`
**File:** `frontend/src/components/search-config/linkedin-form.tsx:143–151`

The keyword `<input>` is uncontrolled (no `value` prop). After adding a keyword, the handler resets it via direct DOM mutation (`input.value = ""`). This is inconsistent with `TagInput`, which uses controlled state. If the parent needs to reset keywords programmatically (e.g., on form reset), the uncontrolled input will not respond.

Convert to a controlled input with a `useState`:

```ts
const [keywordInput, setKeywordInput] = useState("");

<input
  value={keywordInput}
  onChange={(e) => setKeywordInput(e.target.value)}
  onKeyDown={(e) => {
    if (e.key === "Enter" && keywordInput.trim()) {
      addKeyword(keywordInput.trim());
      setKeywordInput("");
    }
  }}
/>
```

---

### 4. Paired cursor state in `useResults` could diverge
**File:** `frontend/src/hooks/use-results.ts:43–44`

`cursor` and `cursorStack` are separate `useState` calls reset in multiple places. Co-locating them into a single state object prevents them from diverging in future edits:

```ts
const [paginationState, setPaginationState] = useState({
  cursor: null as string | null,
  cursorStack: [] as string[],
});
```

This is a low-risk refactor; only address if the file is being touched for other reasons.

---

## Files

- `frontend/src/components/score-badge.tsx`
- `frontend/src/pages/dashboard.tsx`
- `frontend/src/components/search-config/linkedin-form.tsx`
- `frontend/src/hooks/use-results.ts`
- `frontend/src/constants.ts` (new, optional)

## Acceptance Criteria

- [ ] Score thresholds in `score-badge.tsx` are named constants, not magic numbers
- [ ] `toRunStatusResponse` passes through `result` from a completed run instead of always setting `null`
- [ ] LinkedIn keyword input is controlled (responds to programmatic reset)
- [ ] Cursor state in `useResults` is co-located (optional — only if touching the file)
- [ ] TypeScript compiles without errors
