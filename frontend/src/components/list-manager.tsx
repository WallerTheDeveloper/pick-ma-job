/** ListManager — sidebar panel for creating, renaming, and deleting job lists. */

import { useState } from "react";
import { PencilIcon, PlusIcon, Trash2Icon, CheckIcon, XIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { useLists } from "@/hooks/use-lists";
import type { JobList } from "@/types/schemas";

interface ListManagerProps {
  selectedListId: string | null;
  onSelectList: (listId: string | null) => void;
}

export function ListManager({ selectedListId, onSelectList }: ListManagerProps) {
  const { lists, isLoading, createList, renameList, deleteList } = useLists();
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<JobList | null>(null);

  async function handleCreate() {
    const name = newName.trim();
    if (!name) return;
    try {
      await createList(name);
      setNewName("");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to create list");
    }
  }

  function startEditing(list: JobList) {
    setEditingId(list.id);
    setEditName(list.name);
  }

  async function commitRename() {
    if (!editingId) return;
    const name = editName.trim();
    if (name) {
      try {
        await renameList({ listId: editingId, name });
      } catch (err: unknown) {
        toast.error(err instanceof Error ? err.message : "Failed to rename list");
        return;
      }
    }
    setEditingId(null);
  }

  function cancelEditing() {
    setEditingId(null);
  }

  async function handleDelete(list: JobList) {
    if (selectedListId === list.id) {
      onSelectList(null);
    }
    await deleteList(list.id);
    setDeleteTarget(null);
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        Lists
      </h3>

      {/* All results */}
      <button
        type="button"
        onClick={() => onSelectList(null)}
        className={`w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent ${
          selectedListId === null ? "bg-accent font-medium" : ""
        }`}
      >
        All results
      </button>

      {/* List items */}
      {isLoading ? (
        <p className="px-2 text-xs text-muted-foreground">Loading…</p>
      ) : (
        lists.map((list) => (
          <div key={list.id} className="group flex items-center gap-1">
            {editingId === list.id ? (
              <div className="flex flex-1 items-center gap-1">
                <Input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void commitRename();
                    if (e.key === "Escape") cancelEditing();
                  }}
                  className="h-7 flex-1 text-sm"
                  autoFocus
                />
                <Button size="icon-sm" variant="ghost" onClick={commitRename}>
                  <CheckIcon className="size-3" />
                </Button>
                <Button size="icon-sm" variant="ghost" onClick={cancelEditing}>
                  <XIcon className="size-3" />
                </Button>
              </div>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => onSelectList(list.id)}
                  className={`flex-1 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent truncate ${
                    selectedListId === list.id ? "bg-accent font-medium" : ""
                  }`}
                >
                  {list.name}
                </button>
                <div className="flex shrink-0 items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    onClick={() => startEditing(list)}
                  >
                    <PencilIcon className="size-3" />
                  </Button>
                  <Dialog
                    open={deleteTarget?.id === list.id}
                    onOpenChange={(open) => !open && setDeleteTarget(null)}
                  >
                    <DialogTrigger
                      render={
                        <Button
                          size="icon-sm"
                          variant="ghost"
                          onClick={() => setDeleteTarget(list)}
                        />
                      }
                    >
                      <Trash2Icon className="size-3" />
                    </DialogTrigger>
                    <DialogContent showCloseButton={false}>
                      <DialogHeader>
                        <DialogTitle>Delete list "{list.name}"?</DialogTitle>
                        <DialogDescription>
                          This removes the list and all its items. Your job results are not deleted.
                        </DialogDescription>
                      </DialogHeader>
                      <DialogFooter>
                        <DialogClose render={<Button variant="outline">Cancel</Button>} />
                        <Button
                          variant="destructive"
                          onClick={() => void handleDelete(list)}
                        >
                          Delete
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>
              </>
            )}
          </div>
        ))
      )}

      {/* Create new list */}
      <div className="flex items-center gap-1 pt-1">
        <Input
          placeholder="New list name…"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void handleCreate();
          }}
          className="h-7 flex-1 text-sm"
        />
        <Button
          size="icon-sm"
          variant="ghost"
          onClick={handleCreate}
          disabled={!newName.trim()}
        >
          <PlusIcon className="size-3" />
        </Button>
      </div>
    </div>
  );
}
