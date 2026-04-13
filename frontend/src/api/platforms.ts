/** Platforms API functions — list registered scrapers with config status. */

import { api } from "@/api/client";
import { platformsListResponseSchema } from "@/types/schemas";
import type { PlatformsListResponse } from "@/types/schemas";

export async function fetchPlatforms(): Promise<PlatformsListResponse> {
  return api("/api/platforms", {}, platformsListResponseSchema);
}
