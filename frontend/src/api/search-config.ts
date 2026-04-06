/** Search config API functions — list, create, delete. */

import { api } from "@/api/client";
import type {
  SearchConfigCreateRequest,
  SearchConfigCreateResponse,
  SearchConfigsListResponse,
} from "@/types/schemas";

export async function fetchSearchConfigs(): Promise<SearchConfigsListResponse> {
  return api<SearchConfigsListResponse>("/api/search-configs");
}

export async function createSearchConfig(
  data: SearchConfigCreateRequest,
): Promise<SearchConfigCreateResponse> {
  return api<SearchConfigCreateResponse>("/api/search-configs", {
    method: "POST",
    body: data,
  });
}

export async function deleteSearchConfig(id: string): Promise<void> {
  await api<{ ok: boolean }>(`/api/search-configs/${id}`, {
    method: "DELETE",
  });
}
