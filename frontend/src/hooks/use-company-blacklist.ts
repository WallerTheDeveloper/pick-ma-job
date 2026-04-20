import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addBlacklist, listBlacklist, removeBlacklist } from "@/api/company-blacklist";
import type { CompanyBlacklistEntry, CompanyBlacklistListResponse } from "@/types/company-blacklist";

const BLACKLIST_KEY = ["company-blacklist"] as const;

export function useCompanyBlacklist() {
  return useQuery<CompanyBlacklistListResponse>({
    queryKey: BLACKLIST_KEY,
    queryFn: listBlacklist,
  });
}

export function useAddBlacklistEntry() {
  const queryClient = useQueryClient();
  return useMutation<CompanyBlacklistEntry, Error, string>({
    mutationFn: (name: string) => addBlacklist(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: BLACKLIST_KEY }),
  });
}

export function useRemoveBlacklistEntry() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id: string) => removeBlacklist(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: BLACKLIST_KEY }),
  });
}
