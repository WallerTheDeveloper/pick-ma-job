/** Pipeline API functions — trigger runs, poll status, and cancel. */

import { api } from "@/api/client";
import { okResponseSchema, runStartResponseSchema, runStatusResponseSchema } from "@/types/schemas";
import type { RunStartResponse, RunStatusResponse } from "@/types/schemas";

export interface StartRunArgs {
  platforms?: string[];
}

export async function startRun(args?: StartRunArgs): Promise<RunStartResponse> {
  const body = args?.platforms !== undefined ? { platforms: args.platforms } : {};
  return api("/api/run", { method: "POST", body }, runStartResponseSchema);
}

export async function getRunStatus(runId: string): Promise<RunStatusResponse> {
  return api(`/api/run/${runId}/status`, {}, runStatusResponseSchema);
}

export async function cancelRun(runId: string): Promise<{ ok: boolean }> {
  return api(`/api/run/${runId}/cancel`, { method: "POST" }, okResponseSchema);
}
