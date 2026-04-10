/** Results page — filter, sort, paginate, and manage job evaluation results. */

import { useState } from "react";
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
import { ResultRow } from "@/components/result-row";
import { ListManager } from "@/components/list-manager";
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

export function ResultsPage() {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [selectedListId, setSelectedListId] = useState<string | null>(null);

  const {
    results: allResults,
    pagination,
    isLoading: allLoading,
    error: allError,
    filters,
    updateFilter,
    resetFilters,
    updateStatus,
    isUpdatingStatus,
    bulkDismiss,
    isBulkDismissing,
  } = useResults();

  const { data: listJobsData, isLoading: listLoading } = useListJobs(selectedListId);

  const results = selectedListId !== null ? (listJobsData?.jobs ?? []) : allResults;
  const isLoading = selectedListId !== null ? listLoading : allLoading;
  const error = selectedListId !== null ? null : allError;

  const hasActiveFilters =
    filters.status !== "" ||
    filters.minScore !== "" ||
    filters.platform !== "";

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
        {/* Status filter */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">
            Status
          </label>
          <Select
            value={filters.status}
            onValueChange={(val) => updateFilter("status", val as string)}
          >
            <SelectTrigger>
              <SelectValue>
                {(value) => statusLabels[value as string] ?? "All statuses"}
              </SelectValue>
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
          <label className="text-xs font-medium text-muted-foreground">
            Platform
          </label>
          <Select
            value={filters.platform}
            onValueChange={(val) => updateFilter("platform", val as string)}
          >
            <SelectTrigger>
              <SelectValue>
                {(value) => platformLabels[value as string] ?? "All platforms"}
              </SelectValue>
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
          <label className="text-xs font-medium text-muted-foreground">
            Sort
          </label>
          <Select
            value={filters.sort}
            onValueChange={(val) => updateFilter("sort", val as string)}
          >
            <SelectTrigger>
              <SelectValue>
                {(value) => sortLabels[value as string] ?? String(value)}
              </SelectValue>
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
          <Button variant="ghost" size="sm" onClick={resetFilters}>
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
                        max_score: Number(filters.minScore),
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

      {/* Results list */}
      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((result) => (
            <ResultRow
              key={result.id}
              result={result}
              onStatusChange={(id, status) =>
                updateStatus({ resultId: id, status })
              }
              isUpdating={isUpdatingStatus}
            />
          ))}
        </div>
      )}

      {/* Pagination — only shown when viewing all results (not a specific list) */}
      {selectedListId === null && pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {pagination.page} of {pagination.total_pages} ({pagination.total}{" "}
            results)
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={pagination.page <= 1}
              onClick={() => updateFilter("page", pagination.page - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={pagination.page >= pagination.total_pages}
              onClick={() => updateFilter("page", pagination.page + 1)}
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
