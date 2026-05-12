/** Hook for triggering pipeline runs, polling their status, and cancelling. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useRef } from "react";
import { cancelRun, startRun, getRunStatus } from "@/api/pipeline";
import type { StartRunArgs } from "@/api/pipeline";
import type { RunStatusResponse } from "@/types/schemas";

export const RUN_STATUS_KEY = "run-status";

const SESSION_STORAGE_KEY = "activeRunId";

/** Check if a run status is terminal (no more polling needed). */
function isTerminalStatus(status: string | undefined): boolean {
  return status === "completed" || status === "failed" || status === "cancelled";
}

/**
 * Polls a specific run's status until it reaches a terminal state.
 * Safe to use standalone — e.g. for rehydrating an in-progress run on page reload (T-06).
 * Stops polling when status is terminal, and never polls in the background.
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
      if (isTerminalStatus(status)) return false;
      return 2000;
    },
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    const status = query.data?.status;
    if (isTerminalStatus(status) && prevStatusRef.current !== status) {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["results"] });
    }
    prevStatusRef.current = status;
  }, [query.data?.status, queryClient]);

  return query;
}

/**
 * Starts a pipeline run and tracks its status via polling.
 * Persists the active run ID to sessionStorage so it survives page reloads and
 * navigation. Clears sessionStorage once the run reaches a terminal state.
 */
export function useRun(initialRunId?: string) {
  const queryClient = useQueryClient();

  // Seed activeRunId from sessionStorage (survives page reload) or initialRunId
  const [activeRunId, setActiveRunId] = useState<string | null>(() => {
    const stored = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (stored) return stored;
    return initialRunId ?? null;
  });

  // Rehydrate from sessionStorage on mount (in case another tab set it)
  useEffect(() => {
    const stored = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (stored && activeRunId === null) {
      setActiveRunId(stored);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync sessionStorage when activeRunId changes
  useEffect(() => {
    if (activeRunId) {
      sessionStorage.setItem(SESSION_STORAGE_KEY, activeRunId);
    }
  }, [activeRunId]);

  const startMutation = useMutation({
    mutationFn: (args?: StartRunArgs | void) => startRun(args ?? undefined),
    onSuccess: (data) => {
      setActiveRunId(data.run_id);
      sessionStorage.setItem(SESSION_STORAGE_KEY, data.run_id);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (runId: string) => cancelRun(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [RUN_STATUS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const statusQuery = useRunStatus(activeRunId);

  const runStatus: RunStatusResponse | null = statusQuery.data ?? null;
  const isRunning =
    activeRunId !== null && !isTerminalStatus(runStatus?.status);

  // Clear sessionStorage once the run reaches a terminal state
  useEffect(() => {
    if (runStatus && isTerminalStatus(runStatus.status)) {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
    }
  }, [runStatus?.status]);

  function clearRun() {
    if (activeRunId) {
      queryClient.removeQueries({ queryKey: [RUN_STATUS_KEY, activeRunId] });
    }
    setActiveRunId(null);
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
  }

  return {
    startRun: startMutation.mutate,
    startStatus: startMutation.status,
    startError: startMutation.error,
    runStatus,
    isRunning,
    activeRunId,
    setActiveRunId,
    clearRun,
    cancelRun: cancelMutation.mutate,
    isCancelling: cancelMutation.isPending,
  };
}
