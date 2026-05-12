/** Hooks for Upwork proposal generation and retrieval. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { generateProposal, getCachedProposal } from "@/api/proposals";
import type { ProposalResponse } from "@/types/schemas";

export function useProposal(jobResultId: string) {
  return useQuery<ProposalResponse>({
    queryKey: ["proposal", jobResultId],
    queryFn: () => getCachedProposal(jobResultId),
    enabled: false, // don't auto-fetch; only fetch when dialog opens
  });
}

export function useGenerateProposal() {
  const queryClient = useQueryClient();
  return useMutation<
    ProposalResponse,
    Error,
    { resultId: string; forceRegenerate?: boolean; adjustmentNotes?: string }
  >({
    mutationFn: ({ resultId, forceRegenerate = false, adjustmentNotes }) =>
      generateProposal(resultId, forceRegenerate, adjustmentNotes),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["proposal", variables.resultId],
      });
    },
  });
}