/** Auth API functions. */

import { api } from "@/api/client";
import { authMeResponseSchema, okResponseSchema } from "@/types/schemas";
import type { AuthMeResponse, OkResponse } from "@/types/schemas";

export async function fetchCurrentUser(): Promise<AuthMeResponse> {
  return api("/auth/me", {}, authMeResponseSchema);
}

export async function requestMagicLink(email: string): Promise<OkResponse> {
  return api("/auth/magic-link", {
    method: "POST",
    body: { email },
  });
}

export async function logout(): Promise<OkResponse> {
  return api("/auth/logout", { method: "POST" }, okResponseSchema);
}
