import { api } from "@/api/client";
import {
  CompanyBlacklistListResponseSchema,
  CompanyBlacklistEntrySchema,
  type CompanyBlacklistEntry,
  type CompanyBlacklistListResponse,
} from "@/types/company-blacklist";

const BASE = "/api/company-blacklist";

export async function listBlacklist(): Promise<CompanyBlacklistListResponse> {
  return api(BASE, {}, CompanyBlacklistListResponseSchema);
}

export async function addBlacklist(name: string): Promise<CompanyBlacklistEntry> {
  const res = await api<{ entry: CompanyBlacklistEntry }>(BASE, { method: "POST", body: { name } });
  return CompanyBlacklistEntrySchema.parse(res.entry);
}

export async function removeBlacklist(id: string): Promise<void> {
  await api(`${BASE}/${id}`, { method: "DELETE" });
}
