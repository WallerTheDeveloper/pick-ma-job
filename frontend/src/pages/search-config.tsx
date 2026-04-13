/** Search configuration page — manage per-platform search configs, tabbed by platform. */

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
import {
  LinkedInFiltersForm,
  emptyLinkedInFilters,
  linkedInFiltersToDict,
  type LinkedInFilters,
} from "@/components/search-config/linkedin-form";
import { useSearchConfigs } from "@/hooks/use-search-config";
import { usePlatforms } from "@/hooks/use-platforms";
import type {
  Platform,
  SearchConfigCreateRequest,
  SearchConfigResponse,
} from "@/types/schemas";

// ── Platform labels ─────────────────────────────────────────────────────────

const platformLabels: Record<Platform, string> = {
  upwork: "Upwork",
  linkedin: "LinkedIn",
};

// ── Add form state ──────────────────────────────────────────────────────────

interface AddFormState {
  platform: Platform;
  query: string;
  upworkFilters: UpworkFilters;
  linkedInFilters: LinkedInFilters;
}

function emptyAddForm(platform: Platform): AddFormState {
  return {
    platform,
    query: "",
    upworkFilters: emptyUpworkFilters(),
    linkedInFilters: emptyLinkedInFilters(),
  };
}

function formToRequest(form: AddFormState): SearchConfigCreateRequest {
  if (form.platform === "upwork") {
    return {
      platform: "upwork",
      query: form.query.trim() || null,
      filters: upworkFiltersToDict(form.upworkFilters),
    };
  }

  // LinkedIn: keywords go into filters.searchTerms; query is the display label.
  const { searchTerms } = form.linkedInFilters;
  const query = searchTerms.length > 0 ? searchTerms.join(", ") : form.query.trim() || null;
  return {
    platform: "linkedin",
    query,
    filters: linkedInFiltersToDict(form.linkedInFilters),
  };
}

function validateForm(form: AddFormState): string | null {
  if (form.platform === "upwork") {
    if (!form.query.trim()) return "Search query is required.";
  }
  if (form.platform === "linkedin") {
    if (form.linkedInFilters.searchTerms.length === 0) {
      return "At least one keyword is required.";
    }
    const maxItems = parseInt(form.linkedInFilters.maxItems, 10);
    if (!isNaN(maxItems) && maxItems < 150) {
      return "Max results must be at least 150.";
    }
    if (!isNaN(maxItems) && maxItems > 1000) {
      return "Max results cannot exceed 1000.";
    }
  }
  return null;
}

// ── Platform tab ─────────────────────────────────────────────────────────────

interface PlatformTabProps {
  platform: Platform;
  configs: SearchConfigResponse[];
  onDelete: (id: string) => void;
  isDeleting: boolean;
  deleteTarget: string | null;
  onCreate: (req: SearchConfigCreateRequest) => Promise<unknown>;
  isCreating: boolean;
}

function PlatformTab({
  platform,
  configs,
  onDelete,
  isDeleting,
  deleteTarget,
  onCreate,
  isCreating,
}: PlatformTabProps) {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<AddFormState>(() => emptyAddForm(platform));

  function resetForm() {
    setForm(emptyAddForm(platform));
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
      await onCreate(formToRequest(form));
      toast.success("Search config created.");
      resetForm();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create config.");
    }
  }

  return (
    <div className="space-y-4">
      {/* Add form */}
      {showForm ? (
        <Card>
          <form onSubmit={handleCreate}>
            <CardHeader>
              <CardTitle className="text-base">
                New {platformLabels[platform]} Config
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {platform === "upwork" && (
                <>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Search Query</label>
                    <input
                      className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      placeholder="e.g. unity developer"
                      value={form.query}
                      onChange={(e) => setForm((prev) => ({ ...prev, query: e.target.value }))}
                    />
                  </div>
                  <Separator />
                  <UpworkFiltersForm
                    filters={form.upworkFilters}
                    onChange={(upworkFilters) => setForm((prev) => ({ ...prev, upworkFilters }))}
                  />
                </>
              )}

              {platform === "linkedin" && (
                <LinkedInFiltersForm
                  filters={form.linkedInFilters}
                  onChange={(linkedInFilters) => setForm((prev) => ({ ...prev, linkedInFilters }))}
                />
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
      ) : (
        <div className="flex justify-end">
          <Button onClick={() => setShowForm(true)}>
            Add {platformLabels[platform]} Config
          </Button>
        </div>
      )}

      {/* Existing configs */}
      {configs.length === 0 && !showForm ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No {platformLabels[platform]} configs yet. Add one to start scraping.
          </CardContent>
        </Card>
      ) : configs.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {configs.map((config) => (
            <SearchConfigCard
              key={config.id}
              config={config}
              onDelete={onDelete}
              isDeleting={isDeleting && deleteTarget === config.id}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export function SearchConfigPage() {
  const { configs, isLoading, error, create, isCreating, remove, isDeleting } = useSearchConfigs();
  const { platforms, isLoading: platformsLoading } = usePlatforms();

  const [activeTab, setActiveTab] = useState<Platform>("upwork");
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  async function handleDelete(id: string) {
    try {
      await remove(id);
      toast.success("Search config deleted.");
      setDeleteTarget(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete config.");
    }
  }

  if (isLoading || platformsLoading) {
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

  // Derive tab list from the platforms registry; fall back to known platforms if empty.
  const tabPlatforms: Platform[] =
    platforms.length > 0
      ? (platforms.map((p) => p.slug).filter((s) => s === "upwork" || s === "linkedin") as Platform[])
      : ["upwork", "linkedin"];

  const configsByPlatform = Object.fromEntries(
    tabPlatforms.map((p) => [p, configs.filter((c) => c.platform === p)]),
  ) as Record<Platform, SearchConfigResponse[]>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold">Search Configuration</h2>
        <p className="mt-1 text-muted-foreground">
          Manage your platform search configs. Each config defines what jobs to scrape.
        </p>
      </div>

      {/* Platform tabs */}
      <div className="border-b border-border">
        <div className="flex gap-0">
          {tabPlatforms.map((p) => (
            <button
              key={p}
              type="button"
              className={`border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === p
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setActiveTab(p)}
            >
              {platformLabels[p]}
            </button>
          ))}
        </div>
      </div>

      {/* Active tab content */}
      <PlatformTab
        key={activeTab}
        platform={activeTab}
        configs={configsByPlatform[activeTab] ?? []}
        onDelete={(id) => setDeleteTarget(id)}
        isDeleting={isDeleting}
        deleteTarget={deleteTarget}
        onCreate={create}
        isCreating={isCreating}
      />

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
              Are you sure you want to delete this search config? This action cannot be undone.
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
