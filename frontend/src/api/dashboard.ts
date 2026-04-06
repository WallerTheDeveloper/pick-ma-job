/** Dashboard API functions. */

import { api } from "@/api/client";
import type { DashboardResponse } from "@/types/schemas";

export async function fetchDashboard(): Promise<DashboardResponse> {
  return api<DashboardResponse>("/api/dashboard");
}
