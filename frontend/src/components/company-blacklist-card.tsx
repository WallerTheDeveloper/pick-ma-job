import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/api/client";
import {
  useAddBlacklistEntry,
  useCompanyBlacklist,
  useRemoveBlacklistEntry,
} from "@/hooks/use-company-blacklist";

export function CompanyBlacklistCard() {
  const { data, isLoading, error: queryError } = useCompanyBlacklist();
  const addMutation = useAddBlacklistEntry();
  const removeMutation = useRemoveBlacklistEntry();

  const [inputValue, setInputValue] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);

  async function handleAdd() {
    const trimmed = inputValue.trim();
    if (trimmed.length < 3) {
      setInputError("Name must be at least 3 characters.");
      return;
    }
    setInputError(null);
    try {
      await addMutation.mutateAsync(trimmed);
      setInputValue("");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setInputError("Company is already blacklisted.");
      } else {
        setInputError(err instanceof Error ? err.message : "Failed to add entry.");
      }
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  }

  async function handleRemove(id: string) {
    try {
      await removeMutation.mutateAsync(id);
    } catch {
      // removal errors are non-critical; list will stay in sync via query
    }
  }

  const entries = data?.entries ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Blacklisted Companies</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1">
          <div className="flex gap-2">
            <Input
              placeholder="e.g. Google, Meta…"
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                if (inputError) setInputError(null);
              }}
              onKeyDown={handleKeyDown}
              disabled={addMutation.isPending}
            />
            <Button
              type="button"
              onClick={handleAdd}
              disabled={addMutation.isPending}
            >
              Add
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Matched case-insensitively as substrings. Minimum 3 characters.
          </p>
          {inputError && (
            <p className="text-xs text-destructive">{inputError}</p>
          )}
        </div>

        <div className="space-y-2">
          {isLoading && (
            <p className="text-sm text-muted-foreground">Loading…</p>
          )}
          {queryError && (
            <p className="text-sm text-destructive">
              Failed to load blacklist:{" "}
              {queryError instanceof Error ? queryError.message : "Unknown error"}
            </p>
          )}
          {!isLoading && !queryError && entries.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No companies blacklisted yet.
            </p>
          )}
          {entries.map((entry) => (
            <div
              key={entry.id}
              className="flex items-center justify-between rounded-md border px-3 py-2"
            >
              <span className="text-sm">{entry.name}</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => handleRemove(entry.id)}
                disabled={removeMutation.isPending}
                aria-label={`Remove ${entry.name}`}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
