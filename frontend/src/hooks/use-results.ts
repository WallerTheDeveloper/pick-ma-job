/** Hook for fetching results with filter/sort/pagination and updating status. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  bulkDeleteResults,
  bulkDismissResults,
  deleteResult,
  fetchResults,
  updateResultStatus,
  type BulkDeleteParams,
  type BulkDismissParams,
  type ResultsQueryParams,
} from "@/api/results";
import type { ResultsListResponse } from "@/types/schemas";

const RESULTS_KEY = "results";

export interface ResultsFilters {
  status: string;
  minScore: string;
  platform: string;
  sort: string;
  page: number;
}

const defaultFilters: ResultsFilters = {
  status: "",
  minScore: "",
  platform: "",
  sort: "score_desc",
  page: 1,
};

export function useResults(initialFilters?: Partial<ResultsFilters>) {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ResultsFilters>({
    ...defaultFilters,
    ...initialFilters,
  });

  const queryParams: ResultsQueryParams = {
    ...(filters.status && { status: filters.status }),
    ...(filters.minScore && { min_score: Number(filters.minScore) }),
    ...(filters.platform && { platform: filters.platform }),
    sort: filters.sort,
    page: filters.page,
  };

  const query = useQuery<ResultsListResponse>({
    queryKey: [RESULTS_KEY, queryParams],
    queryFn: () => fetchResults(queryParams),
  });

  const statusMutation = useMutation({
    mutationFn: ({ resultId, status }: { resultId: string; status: string }) =>
      updateResultStatus(resultId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [RESULTS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["lists"] });
    },
  });

  const bulkDismissMutation = useMutation({
    mutationFn: (params: BulkDismissParams) => bulkDismissResults(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [RESULTS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["lists"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (resultId: string) => deleteResult(resultId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [RESULTS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["lists"] });
    },
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: (params: BulkDeleteParams) => bulkDeleteResults(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [RESULTS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["lists"] });
    },
  });

  function updateFilter<K extends keyof ResultsFilters>(
    key: K,
    value: ResultsFilters[K],
  ) {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      // Reset to page 1 when changing filters (not when changing page)
      ...(key !== "page" && { page: 1 }),
    }));
  }

  function resetFilters() {
    setFilters(defaultFilters);
  }

  return {
    results: query.data?.results ?? [],
    pagination: query.data?.pagination ?? null,
    isLoading: query.isLoading,
    error: query.error,
    filters,
    updateFilter,
    resetFilters,
    updateStatus: statusMutation.mutate,
    isUpdatingStatus: statusMutation.isPending,
    bulkDismiss: bulkDismissMutation.mutateAsync,
    isBulkDismissing: bulkDismissMutation.isPending,
    deleteResult: deleteMutation.mutateAsync,
    isDeletingResult: deleteMutation.isPending,
    bulkDelete: bulkDeleteMutation.mutateAsync,
    isBulkDeleting: bulkDeleteMutation.isPending,
  };
}
