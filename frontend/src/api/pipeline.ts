/** Pipeline API functions — trigger runs and poll status. */

import { api } from "@/api/client";
import { runStartResponseSchema, runStatusResponseSchema } from "@/types/schemas";
import type { RunStartResponse, RunStatusResponse } from "@/types/schemas";

export async function startRun(platform?: string): Promise<RunStartResponse> {
  const params = platform ? `?platform=${encodeURIComponent(platform)}` : "";
  return api(`/api/run${params}`, { method: "POST" }, runStartResponseSchema);
}

export async function getRunStatus(runId: string): Promise<RunStatusResponse> {
  return api(`/api/run/${runId}/status`, {}, runStatusResponseSchema);
}
