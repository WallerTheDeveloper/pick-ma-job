/** Results API functions — fetch and update job evaluation results. */

import { api } from "@/api/client";
import { resultsListResponseSchema, jobResultSchema } from "@/types/schemas";
import type { JobResult, ResultsListResponse } from "@/types/schemas";
import { z } from "zod";

export interface ResultsQueryParams {
  status?: string;
  min_score?: number;
  platform?: string;
  sort?: string;
  cursor?: string;
}

export async function fetchResults(
  params: ResultsQueryParams = {},
): Promise<ResultsListResponse> {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.min_score !== undefined)
    search.set("min_score", String(params.min_score));
  if (params.platform) search.set("platform", params.platform);
  if (params.sort) search.set("sort", params.sort);
  if (params.cursor !== undefined) search.set("cursor", params.cursor);

  const qs = search.toString();
  return api(`/api/results${qs ? `?${qs}` : ""}`, {}, resultsListResponseSchema);
}

export async function updateResultStatus(
  resultId: string,
  status: string,
): Promise<JobResult> {
  return api(`/api/results/${resultId}`, { method: "PATCH", body: { status } }, jobResultSchema);
}

export async function deleteResult(resultId: string): Promise<void> {
  await api<void>(`/api/results/${resultId}`, { method: "DELETE" });
}

interface BulkActionParams {
  older_than_days?: number;
  status?: string;
  platform?: string;
  min_score?: number;
  max_score?: number;
}

export type BulkDismissParams = BulkActionParams;

export interface BulkDismissResult {
  dismissed_count: number;
}

const bulkDismissResultSchema = z.object({ dismissed_count: z.number() });

export async function bulkDismissResults(
  params: BulkDismissParams,
): Promise<BulkDismissResult> {
  return api(
    "/api/results/bulk-dismiss",
    { method: "POST", body: params },
    bulkDismissResultSchema,
  );
}

export type BulkDeleteParams = BulkActionParams;

export interface BulkDeleteResult {
  deleted_count: number;
}

const bulkDeleteResultSchema = z.object({ deleted_count: z.number() });

export async function bulkDeleteResults(
  params: BulkDeleteParams,
): Promise<BulkDeleteResult> {
  return api(
    "/api/results/bulk-delete",
    { method: "POST", body: params },
    bulkDeleteResultSchema,
  );
}
