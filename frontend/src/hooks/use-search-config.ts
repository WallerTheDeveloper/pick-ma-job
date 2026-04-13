/** Hook for listing, creating, updating, and deleting search configs. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createSearchConfig,
  deleteSearchConfig,
  fetchSearchConfigs,
  updateSearchConfig,
} from "@/api/search-config";
import type {
  SearchConfigCreateRequest,
  SearchConfigCreateResponse,
  SearchConfigUpdateRequest,
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

  const updateMutation = useMutation<
    SearchConfigCreateResponse,
    Error,
    { id: string; data: SearchConfigUpdateRequest }
  >({
    mutationFn: ({ id, data }) => updateSearchConfig(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CONFIGS_KEY] });
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
    update: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error,
    remove: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error,
  };
}
