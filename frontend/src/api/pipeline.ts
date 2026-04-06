/** Pipeline API functions — trigger runs and poll status. */

import { api } from "@/api/client";
import type { RunStartResponse, RunStatusResponse } from "@/types/schemas";

export async function startRun(platform?: string): Promise<RunStartResponse> {
  const params = platform ? `?platform=${encodeURIComponent(platform)}` : "";
  return api<RunStartResponse>(`/api/run${params}`, { method: "POST" });
}

export async function getRunStatus(runId: string): Promise<RunStatusResponse> {
  return api<RunStatusResponse>(`/api/run/${runId}/status`);
}
