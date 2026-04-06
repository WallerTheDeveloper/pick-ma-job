/** Auth API functions. */

import { api } from "@/api/client";
import type { AuthMeResponse, OkResponse } from "@/types/schemas";

export async function fetchCurrentUser(): Promise<AuthMeResponse> {
  return api<AuthMeResponse>("/auth/me");
}

export async function requestMagicLink(email: string): Promise<OkResponse> {
  return api<OkResponse>("/auth/magic-link", {
    method: "POST",
    body: { email },
  });
}

export async function logout(): Promise<OkResponse> {
  return api<OkResponse>("/auth/logout", {
    method: "POST",
  });
}
