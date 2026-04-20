/** AddToListMenu — dropdown to add/remove a job result from named lists. */

import { useState } from "react";
import { toast } from "sonner";
import { BookmarkPlusIcon, CheckIcon, Loader2, PlusCircleIcon } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
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
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newListName, setNewListName] = useState("");
  const { lists, isLoading: listsLoading, createList, isCreating } = useLists();
  const queryClient = useQueryClient();

  const { data: membershipData, isLoading: membershipLoading } = useQuery({
    queryKey: ["result-lists", jobResultId],
    queryFn: () => fetchResultLists(jobResultId),
    enabled: open,
    staleTime: 0,
  });

  const listIds = membershipData?.list_ids ?? [];
  const isLoading = listsLoading || membershipLoading;

  function handleOpenCreateDialog() {
    setOpen(false);
    setNewListName("");
    setCreateDialogOpen(true);
  }

  function handleCreateDialogOpenChange(next: boolean) {
    if (!next) setNewListName("");
    setCreateDialogOpen(next);
  }

  async function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault();
    const name = newListName.trim();
    if (!name) return;

    try {
      const newList = await createList(name);
      await onAdd(newList.id);
      await queryClient.invalidateQueries({ queryKey: ["result-lists", jobResultId] });
      setCreateDialogOpen(false);
      setNewListName("");
      toast.success(`Added to "${newList.name}"`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to create list");
    }
  }

  return (
    <>
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
            <DropdownMenuItem disabled>No lists yet</DropdownMenuItem>
          )}
          {!isLoading && lists.length > 0 && (
            <>
              <DropdownMenuSeparator />
              {lists.map((list) => {
                const inList = listIds.includes(list.id);
                return (
                  <DropdownMenuItem
                    key={list.id}
                    onSelect={(e) => e.preventDefault()}
                    onClick={async () => {
                      try {
                        if (inList) {
                          await onRemove(list.id);
                        } else {
                          await onAdd(list.id);
                        }
                        await queryClient.invalidateQueries({ queryKey: ["result-lists", jobResultId] });
                      } catch (err: unknown) {
                        toast.error(err instanceof Error ? err.message : "Failed to update list");
                      }
                    }}
                  >
                    <span className="flex-1 truncate">{list.name}</span>
                    {inList && <CheckIcon className="size-3 ml-2 shrink-0 text-muted-foreground" />}
                  </DropdownMenuItem>
                );
              })}
            </>
          )}
          {!isLoading && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleOpenCreateDialog}>
                <PlusCircleIcon className="size-4 mr-2 shrink-0" />
                Create new list…
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={createDialogOpen} onOpenChange={handleCreateDialogOpenChange}>
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>Create new list</DialogTitle>
          </DialogHeader>
          <form id="create-list-form" onSubmit={handleCreateSubmit} className="space-y-2">
            <Input
              placeholder="List name"
              value={newListName}
              onChange={(e) => setNewListName(e.target.value)}
              autoFocus
              disabled={isCreating}
            />
          </form>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" type="button" />}>
              Cancel
            </DialogClose>
            <Button
              type="submit"
              form="create-list-form"
              disabled={!newListName.trim() || isCreating}
            >
              {isCreating ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  Creating…
                </>
              ) : (
                "Create & add"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
