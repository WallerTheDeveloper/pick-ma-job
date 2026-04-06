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
import { Badge } from "@/components/ui/badge";
import { useSearchConfigs } from "@/hooks/use-search-config";
import type {
  Platform,
  SearchConfigCreateRequest,
  SearchConfigResponse,
} from "@/types/schemas";
import { platformValues } from "@/types/schemas";

// ── Platform labels ─────────────────────────────────────────────────────────

const platformLabels: Record<Platform, string> = {
  upwork: "Upwork",
  linkedin: "LinkedIn",
};

// ── Upwork filter options ───────────────────────────────────────────────────

const experienceLevels = [
  { value: "entry", label: "Entry" },
  { value: "intermediate", label: "Intermediate" },
  { value: "expert", label: "Expert" },
] as const;

const jobTypes = [
  { value: "fixed", label: "Fixed Price" },
  { value: "hourly", label: "Hourly" },
] as const;

// ── Upwork filter form state ────────────────────────────────────────────────

interface UpworkFilters {
  experienceLevel: string[];
  jobType: string[];
  paymentVerified: boolean;
  perPage: string;
  maxJobAgeHours: string;
}

function emptyUpworkFilters(): UpworkFilters {
  return {
    experienceLevel: [],
    jobType: [],
    paymentVerified: true,
    perPage: "50",
    maxJobAgeHours: "24",
  };
}

function upworkFiltersToDict(f: UpworkFilters): Record<string, unknown> {
  const filters: Record<string, unknown> = {};
  if (f.experienceLevel.length > 0) filters.experienceLevel = f.experienceLevel;
  if (f.jobType.length > 0) filters.jobType = f.jobType;
  filters.paymentVerified = f.paymentVerified;
  const perPage = parseInt(f.perPage, 10);
  if (!isNaN(perPage) && perPage > 0) filters.perPage = perPage;
  const hours = parseInt(f.maxJobAgeHours, 10);
  if (!isNaN(hours) && hours > 0) {
    filters.maxJobAge = { value: hours, unit: "hours" };
  }
  filters.sort = "newest";
  return filters;
}

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
    form.platform === "upwork"
      ? upworkFiltersToDict(form.upworkFilters)
      : {};

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

// ── Toggle helper for multi-select arrays ───────────────────────────────────

function toggleInArray(arr: string[], value: string): string[] {
  return arr.includes(value)
    ? arr.filter((v) => v !== value)
    : [...arr, value];
}

// ── Config card component ───────────────────────────────────────────────────

interface ConfigCardProps {
  config: SearchConfigResponse;
  onDelete: (id: string) => void;
  isDeleting: boolean;
}

function ConfigCard({ config, onDelete, isDeleting }: ConfigCardProps) {
  const filters = config.filters as Record<string, unknown>;
  const experienceLevel = filters.experienceLevel as string[] | undefined;
  const jobType = filters.jobType as string[] | undefined;
  const paymentVerified = filters.paymentVerified as boolean | undefined;
  const maxJobAge = filters.maxJobAge as { value: number; unit: string } | undefined;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            {platformLabels[config.platform as Platform] ?? config.platform}
          </CardTitle>
          <Badge variant="secondary">{config.platform}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {config.query && (
          <div>
            <span className="font-medium">Query:</span>{" "}
            <span className="text-muted-foreground">{config.query}</span>
          </div>
        )}
        {experienceLevel && experienceLevel.length > 0 && (
          <div>
            <span className="font-medium">Experience:</span>{" "}
            <span className="text-muted-foreground">
              {experienceLevel.join(", ")}
            </span>
          </div>
        )}
        {jobType && jobType.length > 0 && (
          <div>
            <span className="font-medium">Job type:</span>{" "}
            <span className="text-muted-foreground">
              {jobType.join(", ")}
            </span>
          </div>
        )}
        {paymentVerified !== undefined && (
          <div>
            <span className="font-medium">Payment verified:</span>{" "}
            <span className="text-muted-foreground">
              {paymentVerified ? "Yes" : "No"}
            </span>
          </div>
        )}
        {maxJobAge && (
          <div>
            <span className="font-medium">Max age:</span>{" "}
            <span className="text-muted-foreground">
              {maxJobAge.value} {maxJobAge.unit}
            </span>
          </div>
        )}
        <div className="text-xs text-muted-foreground">
          Updated: {new Date(config.updated_at).toLocaleDateString()}
        </div>
      </CardContent>
      <CardFooter className="justify-end">
        <Button
          variant="destructive"
          size="sm"
          disabled={isDeleting}
          onClick={() => onDelete(config.id)}
        >
          {isDeleting ? "Deleting..." : "Delete"}
        </Button>
      </CardFooter>
    </Card>
  );
}

// ── Upwork filters form ─────────────────────────────────────────────────────

interface UpworkFiltersFormProps {
  filters: UpworkFilters;
  onChange: (filters: UpworkFilters) => void;
}

function UpworkFiltersForm({ filters, onChange }: UpworkFiltersFormProps) {
  function updateFilter<K extends keyof UpworkFilters>(
    key: K,
    value: UpworkFilters[K],
  ) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <div className="space-y-4">
      {/* Experience level — multi-toggle */}
      <div className="space-y-1">
        <label className="text-sm font-medium">Experience Level</label>
        <div className="flex flex-wrap gap-2">
          {experienceLevels.map((level) => {
            const selected = filters.experienceLevel.includes(level.value);
            return (
              <button
                key={level.value}
                type="button"
                className={`rounded-md border px-3 py-1 text-sm transition-colors ${
                  selected
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-input bg-background hover:bg-accent"
                }`}
                onClick={() =>
                  updateFilter(
                    "experienceLevel",
                    toggleInArray(filters.experienceLevel, level.value),
                  )
                }
              >
                {level.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Job type — multi-toggle */}
      <div className="space-y-1">
        <label className="text-sm font-medium">Job Type</label>
        <div className="flex flex-wrap gap-2">
          {jobTypes.map((jt) => {
            const selected = filters.jobType.includes(jt.value);
            return (
              <button
                key={jt.value}
                type="button"
                className={`rounded-md border px-3 py-1 text-sm transition-colors ${
                  selected
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-input bg-background hover:bg-accent"
                }`}
                onClick={() =>
                  updateFilter(
                    "jobType",
                    toggleInArray(filters.jobType, jt.value),
                  )
                }
              >
                {jt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Payment verified checkbox */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="paymentVerified"
          className="size-4 rounded border-input"
          checked={filters.paymentVerified}
          onChange={(e) => updateFilter("paymentVerified", e.target.checked)}
        />
        <label htmlFor="paymentVerified" className="text-sm font-medium">
          Payment Verified Only
        </label>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {/* Results per page */}
        <div className="space-y-1">
          <label className="text-sm font-medium">Results per Page</label>
          <Input
            type="number"
            min={1}
            max={100}
            value={filters.perPage}
            onChange={(e) => updateFilter("perPage", e.target.value)}
          />
        </div>

        {/* Max job age */}
        <div className="space-y-1">
          <label className="text-sm font-medium">Max Job Age (hours)</label>
          <Input
            type="number"
            min={1}
            value={filters.maxJobAgeHours}
            onChange={(e) => updateFilter("maxJobAgeHours", e.target.value)}
          />
        </div>
      </div>
    </div>
  );
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
            <ConfigCard
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
