/** Profile API functions — fetch and save the user's profile. */

import { api } from "@/api/client";
import type {
  ProfileGetResponse,
  ProfileSaveRequest,
  ProfileSaveResponse,
} from "@/types/schemas";

export async function fetchProfile(): Promise<ProfileGetResponse> {
  return api<ProfileGetResponse>("/api/profile");
}

export async function saveProfile(
  data: ProfileSaveRequest,
): Promise<ProfileSaveResponse> {
  return api<ProfileSaveResponse>("/api/profile", {
    method: "POST",
    body: data,
  });
}
