/** Dashboard page — welcome, stats, pipeline trigger, run status. */

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fetchDashboard } from "@/api/dashboard";
import { useRun } from "@/hooks/use-run";
import { RunStatus } from "@/components/run-status";
import type { DashboardResponse } from "@/types/schemas";

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
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Profile
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">
              {data.has_profile ? "Configured" : "Not set up"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Search Configs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{data.config_count}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
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
            {isRunning ? "Running..." : "Run Pipeline"}
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
              <Card key={run.id} className="p-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    {new Date(run.started_at).toLocaleString()}
                  </span>
                  <span
                    className={
                      run.status === "completed"
                        ? "text-green-600"
                        : run.status === "failed"
                          ? "text-destructive"
                          : "text-muted-foreground"
                    }
                  >
                    {run.status}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
