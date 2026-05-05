/** Hook for fetching results with filter/sort/cursor pagination and updating status. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  bulkDeleteResults,
  bulkDeleteResultsByIds,
  bulkDismissResults,
  bulkEvaluate,
  bulkUpdateStatus,
  deleteResult,
  evaluateJob,
  fetchResults,
  updateResultStatus,
  type BulkDeleteParams,
  type BulkDismissParams,
  type BulkEvaluationParams,
  type ResultsQueryParams,
} from "@/api/results";
import type { ResultsListResponse } from "@/types/schemas";

const RESULTS_KEY = "results";

export interface ResultsFilters {
  status: string;
  minScore: string;
  platform: string;
  sort: string;
}

const defaultFilters: ResultsFilters = {
  status: "",
  minScore: "",
  platform: "",
  sort: "score_desc",
};

export function useResults(initialFilters?: Partial<ResultsFilters>) {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ResultsFilters>({
    ...defaultFilters,
    ...initialFilters,
  });

  // Cursor stack for prev/next navigation.
  // Each entry is the cursor used to fetch that page (undefined = first page).
  const [cursorStack, setCursorStack] = useState<Array<string | undefined>>([]);
  const [cursor, setCursor] = useState<string | undefined>(undefined);

  const minScore = Number(filters.minScore);
  const queryParams: ResultsQueryParams = {
    ...(filters.status && { status: filters.status }),
    ...(filters.minScore && !isNaN(minScore) && { min_score: minScore }),
    ...(filters.platform && { platform: filters.platform }),
    sort: filters.sort,
    ...(cursor !== undefined && { cursor }),
  };

  const query = useQuery<ResultsListResponse>({
    queryKey: [RESULTS_KEY, queryParams],
    queryFn: () => fetchResults(queryParams),
  });

  const nextCursorValue = query.data?.next_cursor ?? null;
  const hasNextPage = Boolean(nextCursorValue);
  const hasPrevPage = cursorStack.length > 0;

  function nextPage() {
    if (!nextCursorValue) return;
    setCursorStack((prev) => [...prev, cursor]);
    setCursor(nextCursorValue);
  }

  function prevPage() {
    if (cursorStack.length === 0) return;
    const prev = cursorStack[cursorStack.length - 1];
    setCursorStack((s) => s.slice(0, -1));
    setCursor(prev);
  }

  function updateFilter<K extends keyof ResultsFilters>(
    key: K,
    value: ResultsFilters[K],
  ) {
    setFilters((prev) => ({ ...prev, [key]: value }));
    // Reset pagination whenever any filter changes
    setCursor(undefined);
    setCursorStack([]);
  }

  function resetFilters() {
    setFilters(defaultFilters);
    setCursor(undefined);
    setCursorStack([]);
  }

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

  const bulkDeleteByIdsMutation = useMutation({
    mutationFn: (ids: string[]) => bulkDeleteResultsByIds(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [RESULTS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["lists"] });
    },
  });

  const bulkUpdateStatusMutation = useMutation({
    mutationFn: ({ ids, status }: { ids: string[]; status: string }) =>
      bulkUpdateStatus(ids, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [RESULTS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["lists"] });
    },
  });

  const evaluateJobMutation = useMutation({
    mutationFn: (resultId: string) => evaluateJob(resultId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [RESULTS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["lists"] });
    },
  });

  const bulkEvaluateMutation = useMutation({
    mutationFn: (params: BulkEvaluationParams) => bulkEvaluate(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [RESULTS_KEY] });
      queryClient.invalidateQueries({ queryKey: ["lists"] });
    },
  });

  return {
    results: query.data?.results ?? [],
    pagination: query.data?.pagination ?? null,
    isLoading: query.isLoading,
    error: query.error,
    filters,
    updateFilter,
    resetFilters,
    hasNextPage,
    hasPrevPage,
    nextPage,
    prevPage,
    updateStatus: statusMutation.mutate,
    isUpdatingStatus: statusMutation.isPending,
    bulkDismiss: bulkDismissMutation.mutateAsync,
    isBulkDismissing: bulkDismissMutation.isPending,
    deleteResult: deleteMutation.mutateAsync,
    isDeletingResult: deleteMutation.isPending,
    bulkDelete: bulkDeleteMutation.mutateAsync,
    isBulkDeleting: bulkDeleteMutation.isPending,
    bulkDeleteByIds: bulkDeleteByIdsMutation.mutateAsync,
    isBulkDeletingByIds: bulkDeleteByIdsMutation.isPending,
    bulkUpdateStatusByIds: bulkUpdateStatusMutation.mutateAsync,
    isBulkUpdatingStatus: bulkUpdateStatusMutation.isPending,
    evaluateJob: evaluateJobMutation.mutateAsync,
    isEvaluatingJob: evaluateJobMutation.isPending,
    bulkEvaluate: bulkEvaluateMutation.mutateAsync,
    isBulkEvaluating: bulkEvaluateMutation.isPending,
  };
}
