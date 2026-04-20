# M6: Add Runtime Guard to Platform Cast in `search-config.tsx`

- **Phase:** Medium
- **Priority:** P2 — Silent Incorrect State
- **Status:** DONE
- **Depends on:** None

## Problem

`frontend/src/pages/search-config.tsx:113` casts a `string` from the backend to the `Platform` union type without any runtime check:

```ts
const platform = config.platform as Platform;
```

`config.platform` is typed as `string` from the Zod schema. The `Platform` type is `"upwork" | "linkedin"`. If the server returns an unknown platform slug (a new platform added to the backend before the frontend is updated, a typo, or a future migration), the cast silently succeeds and `platformLabels[platform]` returns `undefined` — the UI renders with a missing label and no diagnostic information.

## Solution

Add a runtime narrowing check before using the value:

```ts
const VALID_PLATFORMS: Platform[] = ["upwork", "linkedin"];

function isPlatform(value: string): value is Platform {
  return (VALID_PLATFORMS as string[]).includes(value);
}

// In configToFormState:
if (!isPlatform(config.platform)) {
  throw new Error(`Unknown platform: ${config.platform}`);
}
const platform = config.platform;
```

Alternatively, update the Zod schema to use `z.enum(["upwork", "linkedin"])` so validation happens at the API boundary:

```ts
// In types/schemas.ts
platform: z.enum(["upwork", "linkedin"]),
```

The Zod approach is preferred as it validates once at the boundary and eliminates the need for runtime checks throughout the app.

## Files

- `frontend/src/pages/search-config.tsx`
- `frontend/src/types/schemas.ts` (if using Zod enum approach)

## Acceptance Criteria

- [ ] An unknown `platform` value from the backend is caught and handled with a clear error (not silently used)
- [ ] `platformLabels[platform]` never returns `undefined` for a validated platform value
- [ ] If the Zod schema approach is used, `config.platform` is typed as `Platform` after parsing — no `as` cast needed
- [ ] TypeScript compiles without errors
