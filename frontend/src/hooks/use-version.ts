/** Hook for fetching the app version (cached forever, no refetch). */

import { useQuery } from "@tanstack/react-query";
import { fetchVersion } from "@/api/version";

export function useVersion() {
  const query = useQuery({
    queryKey: ["version"],
    queryFn: fetchVersion,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
  });

  return query.data?.version ?? null;
}
