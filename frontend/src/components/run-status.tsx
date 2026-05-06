/** Pipeline run status display — shows progress and result summary. */

import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RunStatusResponse } from "@/types/schemas";

interface RunStatusProps {
  run: RunStatusResponse;
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "pending":
      return <Clock className="h-4 w-4 text-muted-foreground" />;
    case "running":
      return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    case "completed":
      return <CheckCircle2 className="h-4 w-4 text-green-600" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-destructive" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

export function RunStatus({ run }: RunStatusProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Pipeline Run</CardTitle>
          <div className="flex items-center gap-1.5">
            <StatusIcon status={run.status} />
            <span className="text-sm text-muted-foreground">
              {run.status.charAt(0).toUpperCase() + run.status.slice(1)}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {(run.status === "pending" || run.status === "running") && (
          <>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin shrink-0" />
              <span>
                {run.status === "pending"
                  ? "Waiting to start..."
                  : "Scraping and evaluating jobs..."}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 pt-1 animate-pulse">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-4 rounded bg-muted" />
              ))}
            </div>
          </>
        )}

        {run.status === "completed" && run.result && (
          <>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              <span className="text-muted-foreground">Jobs found</span>
              <span className="font-medium">{run.result.jobs_found}</span>
              <span className="text-muted-foreground">Skipped (dedup)</span>
              <span className="font-medium">{run.result.jobs_skipped_dedup}</span>
              <span className="text-muted-foreground">Skipped (filter)</span>
              <span className="font-medium">{run.result.jobs_skipped_filter}</span>
              <span className="text-muted-foreground">Stored</span>
              <span className="font-medium">{run.result.jobs_stored}</span>
              {run.result.rate_limit_hits > 0 && (
                <>
                  <span className="text-muted-foreground">Rate limit hits</span>
                  <span className="font-medium text-amber-600">
                    {run.result.rate_limit_hits}
                  </span>
                </>
              )}
              {(run.result.total_input_tokens > 0 || run.result.total_output_tokens > 0) && (
                <>
                  <span className="text-muted-foreground">Token usage</span>
                  <span className="font-medium">
                    {(run.result.total_input_tokens / 1000).toFixed(1)}k in / {(run.result.total_output_tokens / 1000).toFixed(1)}k out
                  </span>
                </>
              )}
              {run.result.errors.length > 0 && (
                <>
                  <span className="text-muted-foreground">Errors</span>
                  <span className="font-medium text-destructive">
                    {run.result.errors.length}
                  </span>
                </>
              )}
            </div>
            {run.result.errors.length > 0 && (
              <div className="mt-2 space-y-1">
                {run.result.errors.map((err, i) => (
                  <p key={`${i}-${err.slice(0, 30)}`} className="text-xs text-destructive break-words">
                    {err}
                  </p>
                ))}
              </div>
            )}
          </>
        )}

        {run.status === "failed" && run.error && (
          <p className="text-destructive">{run.error}</p>
        )}
      </CardContent>
    </Card>
  );
}
