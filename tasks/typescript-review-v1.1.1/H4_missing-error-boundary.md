# H4: Add Error Boundary Around Authenticated Routes

- **Phase:** High
- **Priority:** P1 — Production Reliability
- **Status:** DONE
- **Depends on:** None

## Problem

`frontend/src/App.tsx` has no `<ErrorBoundary>` wrapping the authenticated route tree. Any unhandled render-time exception — a Zod parse error bubbling up, a null-dereference on unexpected API data, a component accessing undefined state — will crash the entire React tree and show a blank white screen in production.

Given the app uses multiple async data sources (TanStack Query, polling, lazy-loaded pages), this is a real exposure path that will manifest as an unrecoverable blank screen for end users.

## Solution

1. Install or implement an error boundary component. React 19 supports `react-error-boundary` (the de-facto standard):
   ```bash
   npm install react-error-boundary
   ```

2. Wrap the authenticated route subtree in `App.tsx`:
   ```tsx
   import { ErrorBoundary } from "react-error-boundary";

   function AppErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
     return (
       <div className="flex min-h-screen items-center justify-center p-8 text-center">
         <div>
           <h2 className="text-lg font-semibold">Something went wrong</h2>
           <p className="mt-2 text-sm text-muted-foreground">{error?.message}</p>
           <button onClick={resetErrorBoundary} className="mt-4 ...">
             Try again
           </button>
         </div>
       </div>
     );
   }

   // In JSX:
   <ErrorBoundary FallbackComponent={AppErrorFallback}>
     {/* authenticated routes */}
   </ErrorBoundary>
   ```

3. Consider a second, tighter error boundary around individual pages so a single page crash does not affect the whole app.

## Files

- `frontend/src/App.tsx`
- `frontend/src/components/app-error-fallback.tsx` (new component)
- `frontend/package.json` (add `react-error-boundary`)

## Acceptance Criteria

- [ ] `react-error-boundary` (or an equivalent custom boundary) is installed and used
- [ ] A render-time exception in any authenticated page shows a user-friendly error UI instead of a blank screen
- [ ] The error fallback includes a "Try again" / reset action
- [ ] The error boundary does not wrap the login/landing pages (unauthenticated routes handle their own errors)
