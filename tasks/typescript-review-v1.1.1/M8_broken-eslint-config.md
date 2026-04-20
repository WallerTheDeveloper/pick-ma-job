# M8: Fix Broken ESLint Configuration

- **Phase:** Medium
- **Priority:** P2 — Tooling / Developer Experience
- **Status:** DONE
- **Depends on:** None

## Problem

`frontend/eslint.config.js:6` imports symbols that do not exist in the installed ESLint version:

```ts
import { defineConfig, globalIgnores } from 'eslint/config'
```

`defineConfig` and `globalIgnores` are only exported from ESLint `>=9.9.0`. The currently installed version (9.39.4 or similar) does not export them, causing a fatal `TypeError` when ESLint runs. As a result, `npm run lint` has been silently broken throughout development — none of the following rules have been enforced:

- `react-hooks/exhaustive-deps` — stale closure bugs in hooks may be undetected
- `@typescript-eslint` rules — type-unsafe patterns may be undetected
- `react-refresh` rules — HMR correctness unverified

## Solution

Fix the import to use the correct ESLint flat config API for the installed version. The standard approach for ESLint 9 flat config (which does not have `defineConfig`):

```js
// eslint.config.js
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

export default [
  { ignores: ['dist'] },
  {
    files: ['**/*.{ts,tsx}'],
    ...tseslint.configs.recommended[0],
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  },
];
```

After fixing, run `npm run lint` and address any newly surfaced warnings — particularly `react-hooks/exhaustive-deps` violations.

## Files

- `frontend/eslint.config.js`
- Possibly `frontend/package.json` (verify ESLint and plugin versions)

## Acceptance Criteria

- [ ] `npm run lint` (or `npx eslint .`) runs without a `TypeError` or fatal config error
- [ ] `react-hooks/exhaustive-deps` rule is active and passing
- [ ] `@typescript-eslint` rules are active and passing
- [ ] Any new lint warnings surfaced after fixing the config are addressed
- [ ] TypeScript compiles without errors
