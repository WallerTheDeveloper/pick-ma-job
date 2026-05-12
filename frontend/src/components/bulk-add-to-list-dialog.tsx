/** BulkAddToListDialog — dialog to add multiple selected jobs to a chosen list. */

import { useState } from "react";
import { toast } from "sonner";
import { ListPlusIcon, Loader2, PlusCircleIcon } from "lucide-react";
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
import { useLists } from "@/hooks/use-lists";
import { bulkAddJobsToList } from "@/api/lists";

interface BulkAddToListDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedIds: Set<string>;
  onSuccess: () => void;
}

export function BulkAddToListDialog({
  open,
  onOpenChange,
  selectedIds,
  onSuccess,
}: BulkAddToListDialogProps) {
  const [selectedListId, setSelectedListId] = useState<string | null>(null);
  const [creatingNew, setCreatingNew] = useState(false);
  const [newListName, setNewListName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { lists, isLoading: listsLoading, createList, isCreating } = useLists();

  const count = selectedIds.size;

  function handleClose() {
    setSelectedListId(null);
    setCreatingNew(false);
    setNewListName("");
    setSubmitting(false);
    onOpenChange(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;

    let targetListId = selectedListId;
    let targetListName: string | null = null;

    if (creatingNew) {
      const name = newListName.trim();
      if (!name) return;
      try {
        const newList = await createList(name);
        targetListId = newList.id;
        targetListName = newList.name;
      } catch (err: unknown) {
        toast.error(err instanceof Error ? err.message : "Failed to create list");
        return;
      }
    } else {
      if (!targetListId) return;
      targetListName = lists.find((l) => l.id === targetListId)?.name ?? null;
    }

    setSubmitting(true);
    try {
      const result = await bulkAddJobsToList(targetListId!, [...selectedIds]);
      toast.success(`Added ${result.added} job${result.added !== 1 ? "s" : ""} to "${targetListName}"`);
      handleClose();
      onSuccess();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to add jobs to list");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose(); else onOpenChange(v); }}>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>Add {count} job{count !== 1 ? "s" : ""} to list</DialogTitle>
        </DialogHeader>

        {creatingNew ? (
          <form id="bulk-add-list-form" onSubmit={handleSubmit} className="space-y-2">
            <Input
              placeholder="New list name"
              value={newListName}
              onChange={(e) => setNewListName(e.target.value)}
              autoFocus
              disabled={submitting || isCreating}
            />
          </form>
        ) : (
          <div className="max-h-64 space-y-1 overflow-y-auto">
            {listsLoading && <p className="py-4 text-center text-sm text-muted-foreground">Loading lists…</p>}
            {!listsLoading && lists.length === 0 && (
              <p className="py-4 text-center text-sm text-muted-foreground">No lists yet. Create one below.</p>
            )}
            {!listsLoading && lists.length > 0 && (
              <div className="space-y-1">
                {lists.map((list) => (
                  <button
                    key={list.id}
                    type="button"
                    className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors ${
                      selectedListId === list.id
                        ? "bg-primary text-primary-foreground"
                        : "hover:bg-muted"
                    }`}
                    onClick={() => setSelectedListId(list.id)}
                  >
                    {list.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          {!creatingNew && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setCreatingNew(true);
                setNewListName("");
              }}
              disabled={submitting}
            >
              <PlusCircleIcon className="mr-1 h-4 w-4" />
              Create new list
            </Button>
          )}
          {creatingNew && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setCreatingNew(false);
                setNewListName("");
              }}
              disabled={submitting}
            >
              Cancel
            </Button>
          )}
          <DialogClose render={<Button variant="outline" type="button" />}>
            Cancel
          </DialogClose>
          {creatingNew ? (
            <Button
              type="submit"
              form="bulk-add-list-form"
              disabled={!newListName.trim() || submitting || isCreating}
            >
              {submitting || isCreating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating & adding…
                </>
              ) : (
                "Create & add"
              )}
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={!selectedListId || submitting}
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Adding…
                </>
              ) : (
                <>
                  <ListPlusIcon className="mr-1 h-4 w-4" />
                  Add to list
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
