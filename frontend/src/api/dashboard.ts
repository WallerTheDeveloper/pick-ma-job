/** Dashboard API functions. */

import { api } from "@/api/client";
import { dashboardResponseSchema } from "@/types/schemas";
import type { DashboardResponse } from "@/types/schemas";

export async function fetchDashboard(): Promise<DashboardResponse> {
  return api("/api/dashboard", {}, dashboardResponseSchema);
}
