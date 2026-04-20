# M2: Remove Extra Render Cycle in Profile Form Initialization

- **Phase:** Medium
- **Priority:** P2 — React Best Practice
- **Status:** DONE
- **Depends on:** None

## Problem

`frontend/src/pages/profile.tsx:45–50` uses a `useEffect` with an `initialized` flag to set the form state after the query resolves:

```ts
useEffect(() => {
  if (!initialized && !isLoading) {
    setForm(profile ? profileToForm(profile) : emptyForm());
    setInitialized(true);
  }
}, [profile, isLoading, initialized]);
```

This causes an extra render cycle: the component first renders with `emptyForm()` state, then after the effect fires (after the query resolves), it re-renders with the real profile data. The `initialized` flag is a common anti-pattern that adds complexity without benefit.

## Solution

Simplify by deriving the form's initial state directly. Use `useEffect` without the `initialized` guard — just depend on `profile` and reset only when profile transitions from `null` to a value:

```ts
const [form, setForm] = useState<ProfileForm>(emptyForm);

useEffect(() => {
  if (profile && !isLoading) {
    setForm(profileToForm(profile));
  }
}, [profile, isLoading]);
```

This removes the `initialized` state variable entirely. The form resets whenever `profile` changes (e.g., after a successful save and re-fetch), which is the correct behavior.

## Files

- `frontend/src/pages/profile.tsx`

## Acceptance Criteria

- [ ] The `initialized` state variable is removed
- [ ] The form initializes from `profile` data when the query resolves
- [ ] The form resets correctly when `profile` changes (e.g., after save)
- [ ] No extra render cycle with empty form state before the real profile loads
- [ ] TypeScript compiles without errors
