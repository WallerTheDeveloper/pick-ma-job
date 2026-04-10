/** Hook for managing job lists — create, rename, delete, and add/remove jobs. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addJobToList,
  createList,
  deleteList,
  fetchJobsInList,
  fetchLists,
  removeJobFromList,
  renameList,
} from "@/api/lists";
import type { JobListJobsResponse, JobListsResponse } from "@/types/schemas";

const LISTS_KEY = "lists";

export function useLists() {
  const queryClient = useQueryClient();

  const query = useQuery<JobListsResponse>({
    queryKey: [LISTS_KEY],
    queryFn: fetchLists,
  });

  const createMutation = useMutation({
    mutationFn: (name: string) => createList(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [LISTS_KEY] }),
  });

  const renameMutation = useMutation({
    mutationFn: ({ listId, name }: { listId: string; name: string }) =>
      renameList(listId, name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [LISTS_KEY] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (listId: string) => deleteList(listId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [LISTS_KEY] }),
  });

  const addJobMutation = useMutation({
    mutationFn: ({ listId, jobResultId }: { listId: string; jobResultId: string }) =>
      addJobToList(listId, jobResultId),
    onSuccess: (_, { listId }) => {
      queryClient.invalidateQueries({ queryKey: [LISTS_KEY, "jobs", listId] });
    },
  });

  const removeJobMutation = useMutation({
    mutationFn: ({ listId, jobResultId }: { listId: string; jobResultId: string }) =>
      removeJobFromList(listId, jobResultId),
    onSuccess: (_, { listId }) => {
      queryClient.invalidateQueries({ queryKey: [LISTS_KEY, "jobs", listId] });
    },
  });

  return {
    lists: query.data?.lists ?? [],
    isLoading: query.isLoading,
    error: query.error,
    createList: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    renameList: renameMutation.mutateAsync,
    isRenaming: renameMutation.isPending,
    deleteList: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    addJob: addJobMutation.mutateAsync,
    removeJob: removeJobMutation.mutateAsync,
  };
}

export function useListJobs(listId: string | null) {
  return useQuery<JobListJobsResponse>({
    queryKey: [LISTS_KEY, "jobs", listId],
    queryFn: () => fetchJobsInList(listId!),
    enabled: listId !== null,
  });
}
