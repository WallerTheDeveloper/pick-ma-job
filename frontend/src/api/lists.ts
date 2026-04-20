/** Job Lists API functions — create, manage, and view named job collections. */

import { api } from "@/api/client";
import {
  jobListSchema,
  jobListsResponseSchema,
  jobListJobsResponseSchema,
  okResponseSchema,
} from "@/types/schemas";
import type { JobList, JobListJobsResponse, JobListsResponse, OkResponse } from "@/types/schemas";

export async function fetchLists(): Promise<JobListsResponse> {
  return api("/api/lists", {}, jobListsResponseSchema);
}

export async function createList(name: string): Promise<JobList> {
  return api("/api/lists", { method: "POST", body: { name } }, jobListSchema);
}

export async function renameList(listId: string, name: string): Promise<JobList> {
  return api(`/api/lists/${listId}`, { method: "PATCH", body: { name } }, jobListSchema);
}

export async function deleteList(listId: string): Promise<OkResponse> {
  return api(`/api/lists/${listId}`, { method: "DELETE" }, okResponseSchema);
}

export interface ListJobsParams {
  status?: string;
  min_score?: number;
  platform?: string;
  sort?: string;
}

export async function fetchJobsInList(listId: string, params?: ListJobsParams): Promise<JobListJobsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.min_score != null) searchParams.set("min_score", String(params.min_score));
  if (params?.platform) searchParams.set("platform", params.platform);
  if (params?.sort) searchParams.set("sort", params.sort);
  const query = searchParams.toString();
  return api(`/api/lists/${listId}/jobs${query ? `?${query}` : ""}`, {}, jobListJobsResponseSchema);
}

export async function addJobToList(listId: string, jobResultId: string): Promise<OkResponse> {
  return api(
    `/api/lists/${listId}/jobs`,
    { method: "POST", body: { job_result_id: jobResultId } },
    okResponseSchema,
  );
}

export async function removeJobFromList(
  listId: string,
  jobResultId: string,
): Promise<OkResponse> {
  return api(
    `/api/lists/${listId}/jobs/${jobResultId}`,
    { method: "DELETE" },
    okResponseSchema,
  );
}
