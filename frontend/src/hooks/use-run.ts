/** Hook for triggering pipeline runs and polling their status. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useRef } from "react";
import { startRun, getRunStatus } from "@/api/pipeline";
import type { StartRunArgs } from "@/api/pipeline";
import type { RunStatusResponse } from "@/types/schemas";

export const RUN_STATUS_KEY = "run-status";

/**
 * Polls a specific run's status until it reaches a terminal state.
 * Safe to use standalone — e.g. for rehydrating an in-progress run on page reload (T-13).
 * Stops polling when status is `completed` or `failed`, and never polls in the background.
 * Invalidates `["results"]` and `["dashboard"]` queries on terminal transition.
 */
export function useRunStatus(runId: string | null) {
  const queryClient = useQueryClient();
  const prevStatusRef = useRef<string | undefined>(undefined);

  const query = useQuery({
    queryKey: [RUN_STATUS_KEY, runId],
    queryFn: () => getRunStatus(runId!),
    enabled: runId !== null,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 2000;
    },
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    const status = query.data?.status;
    if (
      (status === "completed" || status === "failed") &&
      prevStatusRef.current !== status
    ) {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["results"] });
    }
    prevStatusRef.current = status;
  }, [query.data?.status, queryClient]);

  return query;
}

export function useRun() {
  const queryClient = useQueryClient();
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const startMutation = useMutation({
    mutationFn: (args?: StartRunArgs | void) => startRun(args ?? undefined),
    onSuccess: (data) => {
      setActiveRunId(data.run_id);
    },
  });

  const statusQuery = useRunStatus(activeRunId);

  const runStatus: RunStatusResponse | null = statusQuery.data ?? null;
  const isRunning =
    activeRunId !== null &&
    runStatus?.status !== "completed" &&
    runStatus?.status !== "failed";

  function clearRun() {
    if (activeRunId) {
      queryClient.removeQueries({ queryKey: [RUN_STATUS_KEY, activeRunId] });
    }
    setActiveRunId(null);
  }

  return {
    startRun: startMutation.mutate,
    startStatus: startMutation.status,
    startError: startMutation.error,
    runStatus,
    isRunning,
    activeRunId,
    clearRun,
  };
}
