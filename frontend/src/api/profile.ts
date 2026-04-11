/** Profile API functions — fetch and save the user's profile. */

import { api } from "@/api/client";
import { profileGetResponseSchema, profileSaveResponseSchema } from "@/types/schemas";
import type {
  ProfileGetResponse,
  ProfileSaveRequest,
  ProfileSaveResponse,
} from "@/types/schemas";

export async function fetchProfile(): Promise<ProfileGetResponse> {
  return api("/api/profile", {}, profileGetResponseSchema);
}

export async function saveProfile(
  data: ProfileSaveRequest,
): Promise<ProfileSaveResponse> {
  return api(
    "/api/profile",
    { method: "POST", body: data },
    profileSaveResponseSchema,
  );
}
