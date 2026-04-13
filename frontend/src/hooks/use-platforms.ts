/** Hook for fetching the list of registered platforms with config status. */

import { useQuery } from "@tanstack/react-query";
import { fetchPlatforms } from "@/api/platforms";
import type { PlatformInfo } from "@/types/schemas";

const PLATFORMS_KEY = "platforms";

export function usePlatforms() {
  const query = useQuery({
    queryKey: [PLATFORMS_KEY],
    queryFn: fetchPlatforms,
  });

  const platforms: PlatformInfo[] = query.data?.platforms ?? [];
  const configuredPlatforms = platforms.filter((p) => p.has_config);

  return {
    platforms,
    configuredPlatforms,
    isLoading: query.isLoading,
    error: query.error,
  };
}
