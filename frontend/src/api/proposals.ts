/** Proposal API functions — generate and retrieve Upwork proposals. */

import { api } from "@/api/client";
import { proposalResponseSchema } from "@/types/schemas";
import type { ProposalResponse } from "@/types/schemas";

export async function generateProposal(
  resultId: string,
  forceRegenerate = false,
  adjustmentNotes?: string,
): Promise<ProposalResponse> {
  return api(
    `/api/results/${resultId}/proposal`,
    {
      method: "POST",
      body: {
        force_regenerate: forceRegenerate,
        adjustment_notes: adjustmentNotes || null,
      },
    },
    proposalResponseSchema,
  );
}

export async function getCachedProposal(
  resultId: string,
): Promise<ProposalResponse> {
  return api(`/api/results/${resultId}/proposal`, {}, proposalResponseSchema);
}