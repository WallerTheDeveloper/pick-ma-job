/** Hook for fetching and saving the user's profile. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchProfile, saveProfile } from "@/api/profile";
import type {
  ProfileGetResponse,
  ProfileSaveRequest,
  ProfileSaveResponse,
} from "@/types/schemas";

const PROFILE_KEY = "profile";

export function useProfile() {
  const queryClient = useQueryClient();

  const query = useQuery<ProfileGetResponse>({
    queryKey: [PROFILE_KEY],
    queryFn: fetchProfile,
  });

  const saveMutation = useMutation<ProfileSaveResponse, Error, ProfileSaveRequest>({
    mutationFn: saveProfile,
    onSuccess: (data) => {
      queryClient.setQueryData<ProfileGetResponse>([PROFILE_KEY], {
        profile: data.profile,
      });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  return {
    profile: query.data?.profile ?? null,
    isLoading: query.isLoading,
    error: query.error,
    save: saveMutation.mutateAsync,
    isSaving: saveMutation.isPending,
    saveError: saveMutation.error,
  };
}
