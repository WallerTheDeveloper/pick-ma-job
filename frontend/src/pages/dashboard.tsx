/** Dashboard page — welcome, stats, pipeline trigger, run status. */

import { useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { Loader2, CheckCircle2, XCircle, Clock, Play, UserCircle, Settings2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { fetchDashboard } from "@/api/dashboard";
import { useRun } from "@/hooks/use-run";
import { RunStatus } from "@/components/run-status";
import { RunPipelineDialog } from "@/components/run-pipeline-dialog";
import type { DashboardResponse, PipelineRunInfo, RunStatusResponse } from "@/types/schemas";

function RunStatusIcon({ status }: { status: string }) {
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

/** Convert a PipelineRunInfo (from dashboard snapshot) into a RunStatusResponse
 *  so RunStatus can render immediately before the first poll arrives. */
function toRunStatusResponse(run: PipelineRunInfo): RunStatusResponse {
  return {
    run_id: run.id,
    status: run.status,
    started_at: run.started_at,
    completed_at: run.completed_at,
    result: run.result ?? null,
    error: run.error,
  };
}

export function DashboardPage() {
  const { data, isLoading, error } = useQuery<DashboardResponse>({
    queryKey: ["dashboard"],
    queryFn: fetchDashboard,
  });

  // useRun now rehydrates from sessionStorage internally, so no seedRunId needed.
  const { startRun, startStatus, startError, runStatus, isRunning, activeRunId } = useRun();
  const [dialogOpen, setDialogOpen] = useState(false);

  // Track which past run the user clicked to inspect.
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  // The run ID to display: user-selected past run takes priority,
  // otherwise fall back to the active run from useRun.
  const displayedRunId = selectedRunId ?? activeRunId ?? undefined;

  // Find the matching PipelineRunInfo from dashboard data for the snapshot fallback.
  const matchedDashboardRun = data?.recent_runs.find((r) => r.id === displayedRunId);

  // When viewing the active run, prefer the polled status with a dashboard snapshot
  // fallback for the brief window between page load and the first poll response.
  // When viewing a selected past run, use the dashboard snapshot data directly
  // (no polling needed for completed runs).
  const displayedRun: RunStatusResponse | null =
    displayedRunId === activeRunId
      ? (runStatus ?? (matchedDashboardRun ? toRunStatusResponse(matchedDashboardRun) : null))
      : (matchedDashboardRun ? toRunStatusResponse(matchedDashboardRun) : null);

  // Treat seeded-but-not-yet-polled state as running so the button is
  // immediately disabled.
  const effectiveIsRunning = isRunning || (!!activeRunId && runStatus === null);

  if (isLoading) {
    return <p className="text-muted-foreground">Loading dashboard...</p>;
  }

  if (error) {
    return (
      <p className="text-destructive">
        Failed to load dashboard: {error instanceof Error ? error.message : "Unknown error"}
      </p>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <p className="mt-1 text-muted-foreground">
          Welcome back, {data.user.email}
        </p>
      </div>

      {/* Quick stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="shadow-sm transition-shadow hover:shadow-md">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <UserCircle className="h-4 w-4" />
              Profile
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">
              {data.has_profile ? "Configured" : "Not set up"}
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm transition-shadow hover:shadow-md">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Settings2 className="h-4 w-4" />
              Search Configs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{data.config_count}</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm transition-shadow hover:shadow-md">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Clock className="h-4 w-4" />
              Recent Runs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{data.recent_runs.length}</p>
          </CardContent>
        </Card>
      </div>

      {/* Run pipeline */}
      <div className="space-y-4">
        <div className="flex items-center gap-4">
          {!data.has_profile ? (
            <p className="text-sm text-muted-foreground">
              Set up your profile first.
            </p>
          ) : data.config_count === 0 ? (
            <Link to="/search-config" className={buttonVariants({ variant: "outline" })}>
              Configure a search
            </Link>
          ) : (
            <Button
              onClick={() => setDialogOpen(true)}
              disabled={effectiveIsRunning || startStatus === "pending"}
            >
              {effectiveIsRunning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Run Pipeline
                </>
              )}
            </Button>
          )}
        </div>

        {startError && (
          <p className="text-sm text-destructive">
            {startError instanceof Error ? startError.message : "Failed to start run"}
          </p>
        )}

        {displayedRun && <RunStatus run={displayedRun} />}
      </div>

      <RunPipelineDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onRun={(platforms) => startRun({ platforms })}
        isRunning={effectiveIsRunning}
      />

      {/* Recent runs history — always visible */}
      {data.recent_runs.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">
            Recent Runs
          </h3>
          <div className="space-y-2">
            {data.recent_runs.map((run) => (
              <Card
                key={run.id}
                className="p-3 shadow-sm cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => setSelectedRunId(run.id)}
              >
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    {new Date(run.started_at).toLocaleString()}
                  </span>
                  <RunStatusIcon status={run.status} />
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}