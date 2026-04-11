/** Search configuration page — manage per-platform search configs. */

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { SearchConfigCard } from "@/components/search-config-card";
import {
  UpworkFiltersForm,
  emptyUpworkFilters,
  upworkFiltersToDict,
  type UpworkFilters,
} from "@/components/upwork-filters-form";
import { useSearchConfigs } from "@/hooks/use-search-config";
import type {
  Platform,
  SearchConfigCreateRequest,
} from "@/types/schemas";
import { platformValues } from "@/types/schemas";

// ── Platform labels ─────────────────────────────────────────────────────────

const platformLabels: Record<Platform, string> = {
  upwork: "Upwork",
  linkedin: "LinkedIn",
};

// ── Add config form state ───────────────────────────────────────────────────

interface AddFormState {
  platform: Platform;
  query: string;
  upworkFilters: UpworkFilters;
}

function emptyAddForm(): AddFormState {
  return {
    platform: "upwork",
    query: "",
    upworkFilters: emptyUpworkFilters(),
  };
}

function formToRequest(form: AddFormState): SearchConfigCreateRequest {
  const filters =
    form.platform === "upwork" ? upworkFiltersToDict(form.upworkFilters) : {};

  return {
    platform: form.platform,
    query: form.query.trim() || null,
    filters,
  };
}

function validateForm(form: AddFormState): string | null {
  if (!form.query.trim()) return "Search query is required.";
  return null;
}

// ── Main page ───────────────────────────────────────────────────────────────

export function SearchConfigPage() {
  const {
    configs,
    isLoading,
    error,
    create,
    isCreating,
    remove,
    isDeleting,
  } = useSearchConfigs();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<AddFormState>(emptyAddForm);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  function resetForm() {
    setForm(emptyAddForm());
    setShowForm(false);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();

    const validationError = validateForm(form);
    if (validationError) {
      toast.error(validationError);
      return;
    }

    try {
      await create(formToRequest(form));
      toast.success("Search config created.");
      resetForm();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to create config.",
      );
    }
  }

  async function handleDelete(id: string) {
    try {
      await remove(id);
      toast.success("Search config deleted.");
      setDeleteTarget(null);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to delete config.",
      );
    }
  }

  if (isLoading) {
    return <p className="text-muted-foreground">Loading search configs...</p>;
  }

  if (error) {
    return (
      <p className="text-destructive">
        Failed to load search configs:{" "}
        {error instanceof Error ? error.message : "Unknown error"}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Search Configuration</h2>
          <p className="mt-1 text-muted-foreground">
            Manage your platform search configs. Each config defines what jobs
            to scrape.
          </p>
        </div>
        {!showForm && (
          <Button onClick={() => setShowForm(true)}>Add Config</Button>
        )}
      </div>

      {/* Inline add form */}
      {showForm && (
        <Card>
          <form onSubmit={handleCreate}>
            <CardHeader>
              <CardTitle className="text-base">New Search Config</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Platform selector */}
              <div className="space-y-1">
                <label className="text-sm font-medium">Platform</label>
                <Select
                  value={form.platform}
                  onValueChange={(val) =>
                    setForm((prev) => ({
                      ...prev,
                      platform: val as Platform,
                      upworkFilters:
                        val !== prev.platform
                          ? emptyUpworkFilters()
                          : prev.upworkFilters,
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {platformValues.map((p) => (
                      <SelectItem key={p} value={p}>
                        {platformLabels[p]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Search query */}
              <div className="space-y-1">
                <label className="text-sm font-medium">Search Query</label>
                <Input
                  placeholder="e.g. unity developer"
                  value={form.query}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, query: e.target.value }))
                  }
                />
              </div>

              <Separator />

              {/* Platform-specific filters */}
              {form.platform === "upwork" && (
                <UpworkFiltersForm
                  filters={form.upworkFilters}
                  onChange={(upworkFilters) =>
                    setForm((prev) => ({ ...prev, upworkFilters }))
                  }
                />
              )}

              {form.platform === "linkedin" && (
                <p className="text-sm text-muted-foreground">
                  LinkedIn-specific filters are not yet available. Only the
                  search query will be used.
                </p>
              )}
            </CardContent>
            <CardFooter className="justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={resetForm}
                disabled={isCreating}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isCreating}>
                {isCreating ? "Creating..." : "Create Config"}
              </Button>
            </CardFooter>
          </form>
        </Card>
      )}

      {/* Existing configs */}
      {configs.length === 0 && !showForm ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No search configs yet. Add one to start scraping job postings.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {configs.map((config) => (
            <SearchConfigCard
              key={config.id}
              config={config}
              onDelete={(id) => setDeleteTarget(id)}
              isDeleting={isDeleting && deleteTarget === config.id}
            />
          ))}
        </div>
      )}

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Search Config</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this search config? This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteTarget(null)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={isDeleting}
              onClick={() => deleteTarget && handleDelete(deleteTarget)}
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
