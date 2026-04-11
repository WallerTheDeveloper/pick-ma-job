# FE-15: window.matchMedia Called Without SSR Guard

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** TODO
- **Depends on:** None

## Problem

In `src/hooks/use-theme.ts:12`, `getInitialTheme` calls `window.matchMedia` without checking if `window` is defined. While the app is currently a client-only SPA, this will break if SSR or testing environments (like jsdom without matchMedia) are introduced.

## Approach

Add a guard:

```ts
function getInitialTheme(): Theme {
  const stored = localStorage.getItem("theme");
  if (stored === "dark" || stored === "light") return stored;
  if (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    return "dark";
  }
  return "light";
}
```

## Files

- `frontend/src/hooks/use-theme.ts:12` — add `typeof window` guard

## Implementation Notes

- Also consider guarding `localStorage.getItem` for the same reason, or wrapping both in a single `typeof window !== "undefined"` check.
