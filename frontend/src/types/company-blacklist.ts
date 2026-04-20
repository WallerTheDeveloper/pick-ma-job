import { z } from "zod";

export const CompanyBlacklistEntrySchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  created_at: z.string().datetime(),
});

export const CompanyBlacklistListResponseSchema = z.object({
  entries: z.array(CompanyBlacklistEntrySchema),
});

export type CompanyBlacklistEntry = z.infer<typeof CompanyBlacklistEntrySchema>;
export type CompanyBlacklistListResponse = z.infer<typeof CompanyBlacklistListResponseSchema>;
