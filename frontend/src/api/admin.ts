/** Admin API functions — fetch user stats (admin-only). */

import { api } from "@/api/client";
import { adminUsersResponseSchema } from "@/types/schemas";
import type { AdminUsersResponse } from "@/types/schemas";

export async function fetchAdminUsers(): Promise<AdminUsersResponse> {
  return api("/api/admin/users", {}, adminUsersResponseSchema);
}
