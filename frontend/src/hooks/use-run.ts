/** Hook for triggering pipeline runs and polling their status. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { startRun, getRunStatus } from "@/api/pipeline";
import type { RunStatusResponse } from "@/types/schemas";

const RUN_STATUS_KEY = "run-status";

export function useRun() {
  const queryClient = useQueryClient();
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const startMutation = useMutation({
    mutationFn: (platform?: string | void) => startRun(platform ?? undefined),
    onSuccess: (data) => {
      setActiveRunId(data.run_id);
    },
  });

  const statusQuery = useQuery({
    queryKey: [RUN_STATUS_KEY, activeRunId],
    queryFn: () => getRunStatus(activeRunId!),
    enabled: activeRunId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") {
        return false;
      }
      return 2000;
    },
  });

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
