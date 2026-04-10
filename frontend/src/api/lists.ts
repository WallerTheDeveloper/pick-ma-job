/** Job Lists API functions — create, manage, and view named job collections. */

import { api } from "@/api/client";
import type { JobList, JobListJobsResponse, JobListsResponse, OkResponse } from "@/types/schemas";

export async function fetchLists(): Promise<JobListsResponse> {
  return api<JobListsResponse>("/api/lists");
}

export async function createList(name: string): Promise<JobList> {
  return api<JobList>("/api/lists", { method: "POST", body: { name } });
}

export async function renameList(listId: string, name: string): Promise<JobList> {
  return api<JobList>(`/api/lists/${listId}`, { method: "PATCH", body: { name } });
}

export async function deleteList(listId: string): Promise<OkResponse> {
  return api<OkResponse>(`/api/lists/${listId}`, { method: "DELETE" });
}

export async function fetchJobsInList(listId: string): Promise<JobListJobsResponse> {
  return api<JobListJobsResponse>(`/api/lists/${listId}/jobs`);
}

export async function addJobToList(listId: string, jobResultId: string): Promise<OkResponse> {
  return api<OkResponse>(`/api/lists/${listId}/jobs`, {
    method: "POST",
    body: { job_result_id: jobResultId },
  });
}

export async function removeJobFromList(
  listId: string,
  jobResultId: string,
): Promise<OkResponse> {
  return api<OkResponse>(`/api/lists/${listId}/jobs/${jobResultId}`, { method: "DELETE" });
}
