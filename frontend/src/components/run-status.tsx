/** Pipeline run status display — shows progress and result summary. */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { RunStatusResponse } from "@/types/schemas";

interface RunStatusProps {
  run: RunStatusResponse;
}

const statusConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  pending: { label: "Pending", variant: "outline" },
  running: { label: "Running", variant: "default" },
  completed: { label: "Completed", variant: "secondary" },
  failed: { label: "Failed", variant: "destructive" },
};

export function RunStatus({ run }: RunStatusProps) {
  const config = statusConfig[run.status] ?? { label: run.status, variant: "outline" as const };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Pipeline Run</CardTitle>
          <Badge variant={config.variant}>{config.label}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {(run.status === "pending" || run.status === "running") && (
          <p className="text-muted-foreground">
            {run.status === "pending"
              ? "Waiting to start..."
              : "Scraping and evaluating jobs..."}
          </p>
        )}

        {run.status === "completed" && run.result && (
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            <span className="text-muted-foreground">Jobs found</span>
            <span className="font-medium">{run.result.jobs_found}</span>
            <span className="text-muted-foreground">Skipped (dedup)</span>
            <span className="font-medium">{run.result.jobs_skipped_dedup}</span>
            <span className="text-muted-foreground">Skipped (filter)</span>
            <span className="font-medium">{run.result.jobs_skipped_filter}</span>
            <span className="text-muted-foreground">Evaluated</span>
            <span className="font-medium">{run.result.jobs_evaluated}</span>
            <span className="text-muted-foreground">Stored</span>
            <span className="font-medium">{run.result.jobs_stored}</span>
            {run.result.errors.length > 0 && (
              <>
                <span className="text-muted-foreground">Errors</span>
                <span className="font-medium text-destructive">
                  {run.result.errors.length}
                </span>
              </>
            )}
          </div>
        )}

        {run.status === "failed" && run.error && (
          <p className="text-destructive">{run.error}</p>
        )}
      </CardContent>
    </Card>
  );
}
