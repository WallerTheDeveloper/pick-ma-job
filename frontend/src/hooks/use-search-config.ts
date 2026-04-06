/** Hook for listing, creating, and deleting search configs. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createSearchConfig,
  deleteSearchConfig,
  fetchSearchConfigs,
} from "@/api/search-config";
import type {
  SearchConfigCreateRequest,
  SearchConfigCreateResponse,
  SearchConfigsListResponse,
} from "@/types/schemas";

const CONFIGS_KEY = "search-configs";

export function useSearchConfigs() {
  const queryClient = useQueryClient();

  const query = useQuery<SearchConfigsListResponse>({
    queryKey: [CONFIGS_KEY],
    queryFn: fetchSearchConfigs,
  });

  const createMutation = useMutation<
    SearchConfigCreateResponse,
    Error,
    SearchConfigCreateRequest
  >({
    mutationFn: createSearchConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CONFIGS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const deleteMutation = useMutation<void, Error, string>({
    mutationFn: deleteSearchConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CONFIGS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  return {
    configs: query.data?.configs ?? [],
    isLoading: query.isLoading,
    error: query.error,
    create: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    createError: createMutation.error,
    remove: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error,
  };
}
