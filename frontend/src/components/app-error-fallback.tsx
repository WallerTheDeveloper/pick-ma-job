/** AppErrorFallback — full-page error UI rendered by the top-level ErrorBoundary. */

import type { FallbackProps } from "react-error-boundary";
import { Button } from "@/components/ui/button";

export function AppErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  const message = error instanceof Error ? error.message : "An unexpected error occurred.";

  return (
    <div className="flex min-h-screen items-center justify-center p-8 text-center">
      <div className="max-w-md space-y-4">
        <h2 className="text-lg font-semibold">Something went wrong</h2>
        <p className="text-sm text-muted-foreground">{message}</p>
        <Button onClick={resetErrorBoundary}>Try again</Button>
      </div>
    </div>
  );
}
