/** AddToListMenu — dropdown to add/remove a job result from named lists. */

import { useState } from "react";
import { toast } from "sonner";
import { BookmarkPlusIcon, CheckIcon } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLists } from "@/hooks/use-lists";
import { api } from "@/api/client";

interface JobResultListsResponse {
  ok: boolean;
  list_ids: string[];
}

async function fetchResultLists(jobResultId: string): Promise<JobResultListsResponse> {
  return api<JobResultListsResponse>(`/api/results/${jobResultId}/lists`);
}

interface AddToListMenuProps {
  jobResultId: string;
  onAdd: (listId: string) => Promise<void>;
  onRemove: (listId: string) => Promise<void>;
}

export function AddToListMenu({ jobResultId, onAdd, onRemove }: AddToListMenuProps) {
  const [open, setOpen] = useState(false);
  const { lists, isLoading: listsLoading } = useLists();

  const { data: membershipData, isLoading: membershipLoading } = useQuery({
    queryKey: ["result-lists", jobResultId],
    queryFn: () => fetchResultLists(jobResultId),
    enabled: open,
    staleTime: 0,
  });

  const listIds = membershipData?.list_ids ?? [];
  const isLoading = listsLoading || membershipLoading;

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger
        render={
          <Button size="icon-sm" variant="ghost" title="Add to list">
            <BookmarkPlusIcon className="size-4" />
          </Button>
        }
      />
      <DropdownMenuContent side="bottom" align="end">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Add to list</DropdownMenuLabel>
        </DropdownMenuGroup>
        {isLoading && (
          <DropdownMenuItem disabled>Loading…</DropdownMenuItem>
        )}
        {!isLoading && lists.length === 0 && (
          <DropdownMenuItem disabled>No lists yet — create one in the sidebar</DropdownMenuItem>
        )}
        {!isLoading && lists.length > 0 && (
          <>
            <DropdownMenuSeparator />
            {lists.map((list) => {
              const inList = listIds.includes(list.id);
              return (
                <DropdownMenuItem
                  key={list.id}
                  onClick={() => {
                    const promise = inList ? onRemove(list.id) : onAdd(list.id);
                    promise.catch((err: unknown) => {
                      toast.error(err instanceof Error ? err.message : "Failed to update list");
                    });
                  }}
                >
                  <span className="flex-1 truncate">{list.name}</span>
                  {inList && <CheckIcon className="size-3 ml-2 shrink-0 text-muted-foreground" />}
                </DropdownMenuItem>
              );
            })}
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
