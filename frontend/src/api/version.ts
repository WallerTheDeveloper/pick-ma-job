/** Version API functions. */

import { api } from "@/api/client";
import { versionResponseSchema } from "@/types/schemas";
import type { VersionResponse } from "@/types/schemas";

export async function fetchVersion(): Promise<VersionResponse> {
  return api("/api/version", {}, versionResponseSchema);
}
