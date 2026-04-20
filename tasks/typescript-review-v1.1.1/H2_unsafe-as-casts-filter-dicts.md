# H2: Replace Unsafe `as`-Casts in Filter Dict Converters

- **Phase:** High
- **Priority:** P1 — Silent Data Corruption Risk
- **Status:** DONE
- **Depends on:** None

## Problem

Two filter-to-form converter functions cast `Record<string, unknown>` values to concrete types using `as` without any runtime validation:

**`frontend/src/components/upwork-filters-form.tsx:35–41`:**
```ts
const maxJobAge = d.maxJobAge as { value?: number } | undefined;
experienceLevel: (d.experienceLevel as string[]) ?? [],
jobType: (d.jobType as string[]) ?? [],
paymentVerified: (d.paymentVerified as boolean) ?? true,
```

**`frontend/src/components/search-config/linkedin-form.tsx:84–94`:**
```ts
// dictToLinkedInFilters — same unsafe cast pattern
```

If the backend ever returns a malformed shape (e.g., `experienceLevel` as a string instead of an array), the cast silently succeeds and downstream code (`.includes()`, `.filter()`, etc.) throws at runtime with no diagnostic information. Zod schemas already exist for other parts of the API surface — these converters should be consistent.

## Solution

Add runtime guards before each cast. The minimal approach is `Array.isArray` checks:

```ts
experienceLevel: Array.isArray(d.experienceLevel) ? d.experienceLevel as string[] : [],
jobType: Array.isArray(d.jobType) ? d.jobType as string[] : [],
paymentVerified: typeof d.paymentVerified === "boolean" ? d.paymentVerified : true,
```

The preferred approach is a Zod schema for each filter shape:

```ts
const upworkFiltersSchema = z.object({
  experienceLevel: z.array(z.string()).default([]),
  jobType: z.array(z.string()).default([]),
  paymentVerified: z.boolean().default(true),
  maxJobAge: z.object({ value: z.number().optional() }).optional(),
});

export function dictToUpworkFilters(d: Record<string, unknown>): UpworkFilterState {
  const parsed = upworkFiltersSchema.parse(d);
  return { ...parsed };
}
```

## Files

- `frontend/src/components/upwork-filters-form.tsx`
- `frontend/src/components/search-config/linkedin-form.tsx`

## Acceptance Criteria

- [ ] `dictToUpworkFilters` validates each field with a runtime check or Zod parse before using it
- [ ] `dictToLinkedInFilters` applies the same treatment
- [ ] A malformed backend response (wrong type for any field) falls back to a safe default rather than throwing or silently producing corrupt state
- [ ] TypeScript compiles without errors
