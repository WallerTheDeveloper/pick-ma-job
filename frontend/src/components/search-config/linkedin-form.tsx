/** LinkedInFiltersForm — form controls for LinkedIn-specific search filters. */

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { X } from "lucide-react";

// ── Option lists ─────────────────────────────────────────────────────────────

const publishedAtOptions = [
  { value: "r86400", label: "Past 24 hours" },
  { value: "r604800", label: "Past week" },
  { value: "r2592000", label: "Past month" },
] as const;

const jobTypeOptions = [
  { value: "full_time", label: "Full-time" },
  { value: "part_time", label: "Part-time" },
  { value: "contract", label: "Contract" },
  { value: "temporary", label: "Temporary" },
  { value: "internship", label: "Internship" },
  { value: "other", label: "Other" },
] as const;

const experienceLevelOptions = [
  { value: "internship", label: "Internship" },
  { value: "entry_level", label: "Entry Level" },
  { value: "associate", label: "Associate" },
  { value: "mid_senior_level", label: "Mid-Senior Level" },
  { value: "director", label: "Director" },
  { value: "executive", label: "Executive" },
] as const;

const workTypeOptions = [
  { value: "onsite", label: "On-site" },
  { value: "hybrid", label: "Hybrid" },
  { value: "remote", label: "Remote" },
] as const;

// ── Types ─────────────────────────────────────────────────────────────────────

export interface LinkedInFilters {
  searchTerms: string[];
  location: string;
  distance: string;
  publishedAt: string;
  jobType: string[];
  experienceLevel: string[];
  workType: string[];
  salaryBase: string;
  maxItems: string;
  saveOnlyUniqueItems: boolean;
}

export function emptyLinkedInFilters(): LinkedInFilters {
  return {
    searchTerms: [],
    location: "",
    distance: "",
    publishedAt: "r86400",
    jobType: [],
    experienceLevel: [],
    workType: [],
    salaryBase: "",
    maxItems: "50",
    saveOnlyUniqueItems: true,
  };
}

export function linkedInFiltersToDict(f: LinkedInFilters): Record<string, unknown> {
  const dict: Record<string, unknown> = {};

  if (f.searchTerms.length > 0) dict.searchTerms = f.searchTerms;
  if (f.location.trim()) dict.location = f.location.trim();

  const distance = parseInt(f.distance, 10);
  if (!isNaN(distance) && distance > 0) dict.distance = distance;

  dict.publishedAt = f.publishedAt;

  if (f.jobType.length > 0) dict.jobType = f.jobType;
  if (f.experienceLevel.length > 0) dict.experienceLevel = f.experienceLevel;
  if (f.workType.length > 0) dict.workType = f.workType;

  const salaryBase = parseInt(f.salaryBase, 10);
  if (!isNaN(salaryBase) && salaryBase > 0) dict.salaryBase = salaryBase;

  const maxItems = parseInt(f.maxItems, 10);
  if (!isNaN(maxItems) && maxItems > 0) dict.maxItems = Math.min(maxItems, 1000);

  dict.saveOnlyUniqueItems = f.saveOnlyUniqueItems;

  return dict;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function toggleInArray(arr: string[], value: string): string[] {
  return arr.includes(value)
    ? arr.filter((v) => v !== value)
    : [...arr, value];
}

// ── Component ─────────────────────────────────────────────────────────────────

interface LinkedInFiltersFormProps {
  filters: LinkedInFilters;
  onChange: (filters: LinkedInFilters) => void;
}

export function LinkedInFiltersForm({ filters, onChange }: LinkedInFiltersFormProps) {
  function updateFilter<K extends keyof LinkedInFilters>(key: K, value: LinkedInFilters[K]) {
    onChange({ ...filters, [key]: value });
  }

  function handleKeywordKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key !== "Enter" && e.key !== ",") return;
    e.preventDefault();
    const input = e.currentTarget;
    const term = input.value.trim();
    if (term && !filters.searchTerms.includes(term)) {
      updateFilter("searchTerms", [...filters.searchTerms, term]);
    }
    input.value = "";
  }

  function removeKeyword(term: string) {
    updateFilter("searchTerms", filters.searchTerms.filter((t) => t !== term));
  }

  return (
    <div className="space-y-4">
      {/* Keywords (tag input) */}
      <div className="space-y-1">
        <label className="text-sm font-medium">Keywords</label>
        <div className="flex min-h-9 flex-wrap gap-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm focus-within:ring-1 focus-within:ring-ring">
          {filters.searchTerms.map((term) => (
            <span
              key={term}
              className="flex items-center gap-1 rounded bg-secondary px-2 py-0.5 text-xs"
            >
              {term}
              <button
                type="button"
                className="text-muted-foreground hover:text-foreground"
                onClick={() => removeKeyword(term)}
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
          <input
            type="text"
            className="min-w-24 flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
            placeholder={filters.searchTerms.length === 0 ? "Type and press Enter" : "Add more..."}
            onKeyDown={handleKeywordKeyDown}
          />
        </div>
        <p className="text-xs text-muted-foreground">Press Enter or comma to add each keyword.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {/* Location */}
        <div className="space-y-1">
          <label className="text-sm font-medium">Location</label>
          <Input
            placeholder="e.g. Remote, Berlin"
            value={filters.location}
            onChange={(e) => updateFilter("location", e.target.value)}
          />
        </div>

        {/* Distance */}
        <div className="space-y-1">
          <label className="text-sm font-medium">Distance (km)</label>
          <Input
            type="number"
            min={0}
            placeholder="e.g. 25"
            value={filters.distance}
            onChange={(e) => updateFilter("distance", e.target.value)}
          />
        </div>
      </div>

      {/* Published at */}
      <div className="space-y-1">
        <label className="text-sm font-medium">Date Posted</label>
        <Select
          value={filters.publishedAt}
          onValueChange={(val) => updateFilter("publishedAt", val)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {publishedAtOptions.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Job type — multi-toggle */}
      <div className="space-y-1">
        <label className="text-sm font-medium">Job Type</label>
        <div className="flex flex-wrap gap-2">
          {jobTypeOptions.map((opt) => {
            const selected = filters.jobType.includes(opt.value);
            return (
              <button
                key={opt.value}
                type="button"
                className={`rounded-md border px-3 py-1 text-sm transition-colors ${
                  selected
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-input bg-background hover:bg-accent"
                }`}
                onClick={() => updateFilter("jobType", toggleInArray(filters.jobType, opt.value))}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Experience level — multi-toggle */}
      <div className="space-y-1">
        <label className="text-sm font-medium">Experience Level</label>
        <div className="flex flex-wrap gap-2">
          {experienceLevelOptions.map((opt) => {
            const selected = filters.experienceLevel.includes(opt.value);
            return (
              <button
                key={opt.value}
                type="button"
                className={`rounded-md border px-3 py-1 text-sm transition-colors ${
                  selected
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-input bg-background hover:bg-accent"
                }`}
                onClick={() =>
                  updateFilter("experienceLevel", toggleInArray(filters.experienceLevel, opt.value))
                }
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Work type — multi-toggle */}
      <div className="space-y-1">
        <label className="text-sm font-medium">Work Type</label>
        <div className="flex flex-wrap gap-2">
          {workTypeOptions.map((opt) => {
            const selected = filters.workType.includes(opt.value);
            return (
              <button
                key={opt.value}
                type="button"
                className={`rounded-md border px-3 py-1 text-sm transition-colors ${
                  selected
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-input bg-background hover:bg-accent"
                }`}
                onClick={() =>
                  updateFilter("workType", toggleInArray(filters.workType, opt.value))
                }
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {/* Salary base */}
        <div className="space-y-1">
          <label className="text-sm font-medium">Minimum Salary</label>
          <Input
            type="number"
            min={0}
            placeholder="e.g. 50000"
            value={filters.salaryBase}
            onChange={(e) => updateFilter("salaryBase", e.target.value)}
          />
        </div>

        {/* Max items */}
        <div className="space-y-1">
          <label className="text-sm font-medium">Max Results (≤ 1000)</label>
          <Input
            type="number"
            min={1}
            max={1000}
            value={filters.maxItems}
            onChange={(e) => updateFilter("maxItems", e.target.value)}
          />
        </div>
      </div>

      {/* Save only unique items */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="saveOnlyUniqueItems"
          className="size-4 rounded border-input"
          checked={filters.saveOnlyUniqueItems}
          onChange={(e) => updateFilter("saveOnlyUniqueItems", e.target.checked)}
        />
        <label htmlFor="saveOnlyUniqueItems" className="text-sm font-medium">
          Save Only Unique Items
        </label>
      </div>
    </div>
  );
}
