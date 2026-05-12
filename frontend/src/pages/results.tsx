/** Results page — filter, sort, paginate, and manage job evaluation results. */

import { useState, useDeferredValue, useEffect } from "react";
import { toast } from "sonner";
import { ListPlusIcon, Loader2Icon } from "lucide-react";
import { Button } from "@/components/ui/button";
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
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { buttonVariants } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ResultRow } from "@/components/result-row";
import { ListManager } from "@/components/list-manager";
import { useQueryClient } from "@tanstack/react-query";
import { BulkAddToListDialog } from "@/components/bulk-add-to-list-dialog";
import { useResults } from "@/hooks/use-results";
import { useListJobs } from "@/hooks/use-lists";
import { resultStatusValues, type ResultStatus } from "@/types/schemas";

const statusLabels: Record<string, string> = {
  "": "All statuses",
  new: "New",
  applied: "Applied",
  dismissed: "Dismissed",
};

const sortLabels: Record<string, string> = {
  score_desc: "Score (high → low)",
  score_asc: "Score (low → high)",
  date_desc: "Newest first",
  date_asc: "Oldest first",
};

const platformOptions = ["", "upwork", "linkedin"] as const;

const platformLabels: Record<string, string> = {
  "": "All platforms",
  upwork: "Upwork",
  linkedin: "LinkedIn",
};

type DateRange = "" | "today" | "last7" | "last30";

const dateRangeLabels: Record<DateRange, string> = {
  "": "All time",
  today: "Today",
  last7: "Last 7 days",
  last30: "Last 30 days",
};

export function ResultsPage() {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmDeleteAllOpen, setConfirmDeleteAllOpen] = useState(false);
  const [confirmBulkDeleteOpen, setConfirmBulkDeleteOpen] = useState(false);
  const [selectedListId, setSelectedListId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [dateRange, setDateRange] = useState<DateRange>("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkAddListOpen, setBulkAddListOpen] = useState(false);
  const queryClient = useQueryClient();

  const {
    results: allResults,
    pagination,
    isLoading: allLoading,
    error: allError,
    filters,
    updateFilter,
    resetFilters,
    hasNextPage,
    hasPrevPage,
    nextPage,
    prevPage,
    updateStatus,
    isUpdatingStatus,
    bulkDismiss,
    isBulkDismissing,
    deleteResult,
    isDeletingResult,
    bulkDelete,
    isBulkDeleting,
    bulkDeleteByIds,
    isBulkDeletingByIds,
    bulkUpdateStatusByIds,
    isBulkUpdatingStatus,
    bulkEvaluate,
    isBulkEvaluating,
  } = useResults();

  // Clear selection when filters, search, date range, or list changes
  useEffect(() => {
    setSelectedIds(new Set());
  }, [
    filters.status,
    filters.platform,
    filters.minScore,
    filters.sort,
    searchTerm,
    dateRange,
    selectedListId,
  ]);

  const listJobsParams = selectedListId !== null
    ? {
        ...(filters.status && { status: filters.status }),
        ...(filters.platform && { platform: filters.platform }),
        ...(filters.minScore && !isNaN(Number(filters.minScore)) && { min_score: Number(filters.minScore) }),
        sort: filters.sort,
      }
    : undefined;
  const { data: listJobsData, isLoading: listLoading } = useListJobs(selectedListId, listJobsParams);

  const rawResults = selectedListId !== null ? (listJobsData?.jobs ?? []) : allResults;
  const isLoading = selectedListId !== null ? listLoading : allLoading;
  const error = selectedListId !== null ? null : allError;

  const deferredSearch = useDeferredValue(searchTerm);
  const searchFiltered =
    deferredSearch.trim() === ""
      ? rawResults
      : rawResults.filter((r) => {
          const q = deferredSearch.toLowerCase();
          return (
            r.title.toLowerCase().includes(q) ||
            (r.evaluation?.summary ?? "").toLowerCase().includes(q) ||
            r.url.toLowerCase().includes(q)
          );
        });

  const results = (() => {
    if (dateRange === "") return searchFiltered;
    const now = new Date();
    let cutoff: Date;
    if (dateRange === "today") {
      cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    } else if (dateRange === "last7") {
      cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    } else {
      cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    }
    return searchFiltered.filter((r) => new Date(r.created_at) >= cutoff);
  })();

  const hasActiveFilters =
    filters.status !== "" ||
    filters.minScore !== "" ||
    filters.platform !== "" ||
    searchTerm !== "" ||
    dateRange !== "";

  const visibleIds = results.map((r) => r.id);
  const allVisibleSelected =
    visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id));
  const someVisibleSelected =
    visibleIds.some((id) => selectedIds.has(id)) && !allVisibleSelected;

  function toggleSelectAll() {
    if (allVisibleSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        visibleIds.forEach((id) => next.delete(id));
        return next;
      });
    } else {
      setSelectedIds((prev) => new Set([...prev, ...visibleIds]));
    }
  }

  function toggleSelectOne(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  return (
    <div className="flex gap-6">
      {/* Sidebar — list manager */}
      <aside className="w-48 shrink-0">
        <ListManager
          selectedListId={selectedListId}
          onSelectList={setSelectedListId}
        />
      </aside>

      {/* Main content */}
      <div className="min-w-0 flex-1 space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Results</h2>
        <p className="mt-1 text-muted-foreground">
          Job evaluation results from your pipeline runs.
        </p>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-end gap-3">
        {/* Search */}
        <div className="space-y-1">
          <label htmlFor="search-field" className="text-xs font-medium text-muted-foreground">
            Search
          </label>
          <Input
            id="search-field"
            type="search"
            placeholder="Title, summary…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="h-8 w-48"
          />
        </div>

        {/* Status filter */}
        <div className="space-y-1">
          <label htmlFor="status-filter" className="text-xs font-medium text-muted-foreground">
            Status
          </label>
          <Select
            value={filters.status}
            onValueChange={(val) => updateFilter("status", val ?? "")}
          >
            <SelectTrigger id="status-filter">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All statuses</SelectItem>
              {resultStatusValues.map((s: ResultStatus) => (
                <SelectItem key={s} value={s}>
                  {statusLabels[s]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Platform filter */}
        <div className="space-y-1">
          <label htmlFor="platform-filter" className="text-xs font-medium text-muted-foreground">
            Platform
          </label>
          <Select
            value={filters.platform}
            onValueChange={(val) => updateFilter("platform", val ?? "")}
          >
            <SelectTrigger id="platform-filter">
              <SelectValue placeholder="All platforms" />
            </SelectTrigger>
            <SelectContent>
              {platformOptions.map((p) => (
                <SelectItem key={p} value={p}>
                  {platformLabels[p]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Date range filter */}
        <div className="space-y-1">
          <label htmlFor="date-filter" className="text-xs font-medium text-muted-foreground">
            Date added
          </label>
          <Select
            value={dateRange}
            onValueChange={(val) => setDateRange(val as DateRange)}
          >
            <SelectTrigger id="date-filter">
              <SelectValue placeholder="All time" />
            </SelectTrigger>
            <SelectContent>
              {(Object.entries(dateRangeLabels) as [DateRange, string][]).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Min score filter */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">
            Min score
          </label>
          <Input
            type="number"
            min={1}
            max={10}
            placeholder="Any"
            value={filters.minScore}
            onChange={(e) => updateFilter("minScore", e.target.value)}
            className="h-8 w-20"
          />
        </div>

        {/* Sort */}
        <div className="space-y-1">
          <label htmlFor="sort-filter" className="text-xs font-medium text-muted-foreground">
            Sort
          </label>
          <Select
            value={filters.sort}
            onValueChange={(val) => updateFilter("sort", val ?? "")}
          >
            <SelectTrigger id="sort-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(sortLabels).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Reset */}
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              resetFilters();
              setSearchTerm("");
              setDateRange("");
            }}
          >
            Clear filters
          </Button>
        )}

        {/* Bulk dismiss */}
        {results.length > 0 && (
          <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
            <DialogTrigger render={
              <Button variant="outline" size="sm">
                Dismiss all filtered
              </Button>
            } />
            <DialogContent showCloseButton={false}>
              <DialogHeader>
                <DialogTitle>Dismiss all filtered results?</DialogTitle>
                <DialogDescription>
                  This will mark all{" "}
                  {pagination ? pagination.total : results.length} currently
                  filtered result{pagination && pagination.total !== 1 ? "s" : ""}{" "}
                  as dismissed. You can find them later by filtering for
                  "Dismissed" status.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <DialogClose render={<Button variant="outline">Cancel</Button>} />
                <Button
                  variant="destructive"
                  disabled={isBulkDismissing}
                  onClick={async () => {
                    await bulkDismiss({
                      ...(filters.status && { status: filters.status }),
                      ...(filters.platform && { platform: filters.platform }),
                      ...(filters.minScore && {
                        min_score: Number(filters.minScore),
                      }),
                    });
                    setConfirmOpen(false);
                  }}
                >
                  {isBulkDismissing ? "Dismissing..." : "Dismiss all"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}

        {/* Bulk delete */}
        {results.length > 0 && (
          <Dialog open={confirmDeleteAllOpen} onOpenChange={setConfirmDeleteAllOpen}>
            <DialogTrigger render={
              <Button variant="outline" size="sm">
                Delete all filtered
              </Button>
            } />
            <DialogContent showCloseButton={false}>
              <DialogHeader>
                <DialogTitle>Delete all filtered results?</DialogTitle>
                <DialogDescription>
                  This will permanently delete all{" "}
                  {pagination ? pagination.total : results.length} currently
                  filtered result{pagination && pagination.total !== 1 ? "s" : ""}. This action cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <DialogClose render={<Button variant="outline">Cancel</Button>} />
                <Button
                  variant="destructive"
                  disabled={isBulkDeleting}
                  onClick={async () => {
                    await bulkDelete({
                      ...(filters.status && { status: filters.status }),
                      ...(filters.platform && { platform: filters.platform }),
                      ...(filters.minScore && {
                        min_score: Number(filters.minScore),
                      }),
                    });
                    setConfirmDeleteAllOpen(false);
                  }}
                >
                  {isBulkDeleting ? "Deleting..." : "Delete all"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <p className="text-muted-foreground">Loading results...</p>
      )}

      {/* Error state */}
      {error && (
        <p className="text-destructive">
          Failed to load results:{" "}
          {error instanceof Error ? error.message : "Unknown error"}
        </p>
      )}

      {/* Empty state */}
      {!isLoading && !error && results.length === 0 && (
        <p className="text-muted-foreground">
          {hasActiveFilters
            ? "No results match your filters."
            : "No results yet. Run the pipeline from the dashboard to get started."}
        </p>
      )}

      {/* Bulk-select action bar — fixed floating bar, always in DOM to prevent layout shift */}
      <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 transition-opacity duration-150 ${
        selectedIds.size > 0 ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
      }`}>
        <div className="flex items-center gap-3 rounded-md border bg-background shadow-lg px-4 py-2">
          <span className="text-sm font-medium">
            {selectedIds.size} selected
          </span>
          <DropdownMenu>
            <DropdownMenuTrigger
              disabled={isBulkUpdatingStatus}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              Mark as…
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              {(["new", "applied", "dismissed"] as const).map((s) => (
                <DropdownMenuItem
                  key={s}
                  onClick={async () => {
                    const ids = [...selectedIds];
                    await bulkUpdateStatusByIds({ ids, status: s });
                    toast.success(`Marked ${ids.length} job${ids.length !== 1 ? "s" : ""} as ${s.charAt(0).toUpperCase() + s.slice(1)}`);
                    setSelectedIds(new Set());
                  }}
                >
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <Button
            variant="outline"
            size="sm"
            disabled={isBulkEvaluating}
            onClick={async () => {
              const ids = [...selectedIds];
              toast.info(`Evaluating ${ids.length} job${ids.length !== 1 ? "s" : ""}...`);
              try {
                const result = await bulkEvaluate({ result_ids: ids });
                toast.success(`Evaluated ${result.evaluated} job${result.evaluated !== 1 ? "s" : ""}`);
                setSelectedIds(new Set());
              } catch (err: unknown) {
                toast.error(err instanceof Error ? err.message : "Failed to evaluate jobs");
              }
            }}
          >
            {isBulkEvaluating ? (
              <>
                <Loader2Icon className="mr-1 size-3 animate-spin" />
                Evaluating...
              </>
            ) : (
              "Evaluate selected"
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={isBulkEvaluating}
            onClick={async () => {
              // Evaluate all unevaluated jobs matching current filters
              const filter: Record<string, unknown> = {};
              if (filters.platform) filter.platform = filters.platform;
              if (filters.minScore && !isNaN(Number(filters.minScore))) filter.min_score = Number(filters.minScore);
              if (filters.status) filter.status = filters.status;

              toast.info("Evaluating all filtered jobs...");
              try {
                const result = await bulkEvaluate({ filter });
                toast.success(`Evaluated ${result.evaluated} job${result.evaluated !== 1 ? "s" : ""}`);
              } catch (err: unknown) {
                toast.error(err instanceof Error ? err.message : "Failed to evaluate jobs");
              }
            }}
          >
            {isBulkEvaluating ? (
              <>
                <Loader2Icon className="mr-1 size-3 animate-spin" />
                Evaluating...
              </>
            ) : (
              "Evaluate all"
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={selectedIds.size === 0}
            onClick={() => setBulkAddListOpen(true)}
          >
            <ListPlusIcon className="mr-1 h-4 w-4" />
            Add to list
          </Button>
          <Dialog open={confirmBulkDeleteOpen} onOpenChange={setConfirmBulkDeleteOpen}>
            <DialogTrigger render={
              <Button variant="destructive" size="sm">
                Delete {selectedIds.size} selected
              </Button>
            } />
            <DialogContent showCloseButton={false}>
              <DialogHeader>
                <DialogTitle>Delete {selectedIds.size} selected result{selectedIds.size !== 1 ? "s" : ""}?</DialogTitle>
                <DialogDescription>
                  This will permanently delete {selectedIds.size} selected result{selectedIds.size !== 1 ? "s" : ""}. This action cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <DialogClose render={<Button variant="outline">Cancel</Button>} />
                <Button
                  variant="destructive"
                  disabled={isBulkDeletingByIds}
                  onClick={async () => {
                    await bulkDeleteByIds([...selectedIds]);
                    setSelectedIds(new Set());
                    setConfirmBulkDeleteOpen(false);
                  }}
                >
                  {isBulkDeletingByIds ? "Deleting..." : "Delete"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedIds(new Set())}
          >
            Clear selection
          </Button>
        </div>
      </div>

      <BulkAddToListDialog
        open={bulkAddListOpen}
        onOpenChange={setBulkAddListOpen}
        selectedIds={selectedIds}
        onSuccess={() => {
          setSelectedIds(new Set());
          queryClient.invalidateQueries({ queryKey: ["results"] });
        }}
      />

      {/* Results list */}
      {results.length > 0 && (
        <div className="space-y-3">
          {/* Header checkbox row */}
          <div className="flex items-center gap-3 px-1">
            <Checkbox
              aria-label="Select all visible results"
              checked={allVisibleSelected}
              indeterminate={someVisibleSelected}
              onCheckedChange={() => toggleSelectAll()}
            />
            <span className="text-xs text-muted-foreground">
              Select all visible
            </span>
          </div>
          {results.map((result) => (
            <div key={result.id} className="flex items-center gap-3">
              <Checkbox
                aria-label={`Select "${result.title}"`}
                checked={selectedIds.has(result.id)}
                onCheckedChange={() => toggleSelectOne(result.id)}
              />
              <div className="min-w-0 flex-1">
                <ResultRow
                  result={result}
                  onStatusChange={(id, status) =>
                    updateStatus({ resultId: id, status })
                  }
                  onDelete={async (id) => {
                    try {
                      await deleteResult(id);
                    } catch (err: unknown) {
                      toast.error(err instanceof Error ? err.message : "Failed to delete result");
                    }
                  }}
                  isUpdating={isUpdatingStatus}
                  isDeleting={isDeletingResult}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination — only shown when viewing all results (not a specific list) */}
      {selectedListId === null && pagination && (hasNextPage || hasPrevPage) && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {pagination.total} total results
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!hasPrevPage}
              onClick={prevPage}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasNextPage}
              onClick={nextPage}
            >
              Next
            </Button>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
