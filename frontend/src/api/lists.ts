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

export async function fetchJobsInList(listId: string): Promise<JobListJobsResponse> {
  return api(`/api/lists/${listId}/jobs`, {}, jobListJobsResponseSchema);
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
