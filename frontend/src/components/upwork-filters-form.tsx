/** UpworkFiltersForm — form controls for Upwork-specific search filters. */

import { Input } from "@/components/ui/input";

const experienceLevels = [
  { value: "entry", label: "Entry" },
  { value: "intermediate", label: "Intermediate" },
  { value: "expert", label: "Expert" },
] as const;

const jobTypes = [
  { value: "fixed", label: "Fixed Price" },
  { value: "hourly", label: "Hourly" },
] as const;

export interface UpworkFilters {
  experienceLevel: string[];
  jobType: string[];
  paymentVerified: boolean;
  perPage: string;
  maxJobAgeHours: string;
}

export function emptyUpworkFilters(): UpworkFilters {
  return {
    experienceLevel: [],
    jobType: [],
    paymentVerified: true,
    perPage: "50",
    maxJobAgeHours: "24",
  };
}

export function dictToUpworkFilters(d: Record<string, unknown>): UpworkFilters {
  const maxJobAgeRaw = d.maxJobAge != null && typeof d.maxJobAge === "object" ? (d.maxJobAge as { value?: number }) : undefined;
  return {
    experienceLevel: Array.isArray(d.experienceLevel) ? (d.experienceLevel as string[]) : [],
    jobType: Array.isArray(d.jobType) ? (d.jobType as string[]) : [],
    paymentVerified: typeof d.paymentVerified === "boolean" ? d.paymentVerified : true,
    perPage: String(typeof d.perPage === "number" ? d.perPage : 50),
    maxJobAgeHours: String(typeof maxJobAgeRaw?.value === "number" ? maxJobAgeRaw.value : 24),
  };
}

export function upworkFiltersToDict(f: UpworkFilters): Record<string, unknown> {
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

function toggleInArray(arr: string[], value: string): string[] {
  return arr.includes(value)
    ? arr.filter((v) => v !== value)
    : [...arr, value];
}

interface UpworkFiltersFormProps {
  filters: UpworkFilters;
  onChange: (filters: UpworkFilters) => void;
}

export function UpworkFiltersForm({ filters, onChange }: UpworkFiltersFormProps) {
  function updateFilter<K extends keyof UpworkFilters>(key: K, value: UpworkFilters[K]) {
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
