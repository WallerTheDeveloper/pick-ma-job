/** Dashboard page — welcome, stats, pipeline trigger, run status. */

import { useQuery } from "@tanstack/react-query";
import { Loader2, CheckCircle2, XCircle, Clock, Play, UserCircle, Settings2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fetchDashboard } from "@/api/dashboard";
import { useRun } from "@/hooks/use-run";
import { RunStatus } from "@/components/run-status";
import type { DashboardResponse } from "@/types/schemas";

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

export function DashboardPage() {
  const { data, isLoading, error } = useQuery<DashboardResponse>({
    queryKey: ["dashboard"],
    queryFn: fetchDashboard,
  });

  const { startRun, startStatus, startError, runStatus, isRunning } = useRun();

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

  const canRun = data.has_profile && data.config_count > 0;

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
          <Button
            onClick={() => startRun()}
            disabled={!canRun || isRunning || startStatus === "pending"}
          >
            {isRunning ? (
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
          {!canRun && (
            <p className="text-sm text-muted-foreground">
              {!data.has_profile
                ? "Set up your profile first."
                : "Add at least one search config."}
            </p>
          )}
        </div>

        {startError && (
          <p className="text-sm text-destructive">
            {startError instanceof Error ? startError.message : "Failed to start run"}
          </p>
        )}

        {runStatus && <RunStatus run={runStatus} />}
      </div>

      {/* Recent runs history */}
      {data.recent_runs.length > 0 && !runStatus && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">
            Recent Runs
          </h3>
          <div className="space-y-2">
            {data.recent_runs.map((run) => (
              <Card key={run.id} className="p-3 shadow-sm">
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
