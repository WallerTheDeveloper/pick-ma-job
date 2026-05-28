/** Hooks for CV upload, retrieval, deletion, and customization. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCV, uploadCV, deleteCV, customizeCV } from "@/api/cv";
import type { CVGetResponse, CVUploadResponse, CVCustomizeResponse } from "@/types/schemas";

const CV_KEY = "cv";

export function useCV() {
  return useQuery<CVGetResponse>({
    queryKey: [CV_KEY],
    queryFn: fetchCV,
  });
}

export function useUploadCV() {
  const queryClient = useQueryClient();
  return useMutation<CVUploadResponse, Error, File>({
    mutationFn: uploadCV,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CV_KEY] });
    },
  });
}

export function useDeleteCV() {
  const queryClient = useQueryClient();
  return useMutation<unknown, Error, void>({
    mutationFn: () => deleteCV(),
    onSuccess: () => {
      queryClient.setQueryData([CV_KEY], { cv: null });
    },
  });
}

export function useCustomizeCV() {
  return useMutation<CVCustomizeResponse, Error, { jobResultId: string; forceRegenerate?: boolean; adjustmentNotes?: string; humanize?: boolean }>({
    mutationFn: ({ jobResultId, forceRegenerate = false, adjustmentNotes, humanize = true }) =>
      customizeCV(jobResultId, forceRegenerate, adjustmentNotes, humanize),
  });
}
