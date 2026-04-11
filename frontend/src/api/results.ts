/** Results API functions — fetch and update job evaluation results. */

import { api } from "@/api/client";
import type { JobResult, ResultsListResponse } from "@/types/schemas";

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
  return api<ResultsListResponse>(`/api/results${qs ? `?${qs}` : ""}`);
}

export async function updateResultStatus(
  resultId: string,
  status: string,
): Promise<JobResult> {
  return api<JobResult>(`/api/results/${resultId}`, {
    method: "PATCH",
    body: { status },
  });
}

export async function deleteResult(resultId: string): Promise<void> {
  await api<void>(`/api/results/${resultId}`, { method: "DELETE" });
}

export interface BulkDismissParams {
  older_than_days?: number;
  status?: string;
  platform?: string;
  max_score?: number;
}

export interface BulkDismissResult {
  dismissed_count: number;
}

export async function bulkDismissResults(
  params: BulkDismissParams,
): Promise<BulkDismissResult> {
  return api<BulkDismissResult>("/api/results/bulk-dismiss", {
    method: "POST",
    body: params,
  });
}

export interface BulkDeleteParams {
  older_than_days?: number;
  status?: string;
  platform?: string;
  max_score?: number;
}

export interface BulkDeleteResult {
  deleted_count: number;
}

export async function bulkDeleteResults(
  params: BulkDeleteParams,
): Promise<BulkDeleteResult> {
  return api<BulkDeleteResult>("/api/results/bulk-delete", {
    method: "POST",
    body: params,
  });
}
