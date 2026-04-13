/** Search config API functions — list, create, update, delete. */

import { api } from "@/api/client";
import {
  searchConfigsListResponseSchema,
  searchConfigCreateResponseSchema,
} from "@/types/schemas";
import type {
  SearchConfigCreateRequest,
  SearchConfigCreateResponse,
  SearchConfigUpdateRequest,
  SearchConfigsListResponse,
} from "@/types/schemas";

export async function fetchSearchConfigs(): Promise<SearchConfigsListResponse> {
  return api("/api/search-configs", {}, searchConfigsListResponseSchema);
}

export async function createSearchConfig(
  data: SearchConfigCreateRequest,
): Promise<SearchConfigCreateResponse> {
  return api(
    "/api/search-configs",
    { method: "POST", body: data },
    searchConfigCreateResponseSchema,
  );
}

export async function updateSearchConfig(
  id: string,
  data: SearchConfigUpdateRequest,
): Promise<SearchConfigCreateResponse> {
  return api(
    `/api/search-configs/${id}`,
    { method: "PUT", body: data },
    searchConfigCreateResponseSchema,
  );
}

export async function deleteSearchConfig(id: string): Promise<void> {
  await api<void>(`/api/search-configs/${id}`, {
    method: "DELETE",
  });
}
