/** Results page — filter, sort, paginate, and manage job evaluation results. */

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ResultRow } from "@/components/result-row";
import { useResults } from "@/hooks/use-results";
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
  const {
    results,
    pagination,
    isLoading,
    error,
    filters,
    updateFilter,
    resetFilters,
    updateStatus,
    isUpdatingStatus,
  } = useResults();

  const hasActiveFilters =
    filters.status !== "" ||
    filters.minScore !== "" ||
    filters.platform !== "";

  return (
    <div className="space-y-6">
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
          <label className="text-xs font-medium text-muted-foreground">
            Platform
          </label>
          <Select
            value={filters.platform}
            onValueChange={(val) => updateFilter("platform", val as string)}
          >
            <SelectTrigger>
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
          <Button variant="ghost" size="sm" onClick={resetFilters}>
            Clear filters
          </Button>
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

      {/* Pagination */}
      {pagination && pagination.total_pages > 1 && (
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
  );
}
