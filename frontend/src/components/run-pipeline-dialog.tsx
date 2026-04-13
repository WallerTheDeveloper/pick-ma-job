/** Dialog for selecting platforms before starting a pipeline run. */

import { useState } from "react";
import { Link } from "react-router";
import { Play, Loader2, ExternalLink } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { usePlatforms } from "@/hooks/use-platforms";
import type { PlatformInfo } from "@/types/schemas";

interface RunPipelineDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRun: (platforms: string[]) => void;
  isRunning: boolean;
}

function PlatformRow({
  platform,
  checked,
  onToggle,
}: {
  platform: PlatformInfo;
  checked: boolean;
  onToggle: (slug: string) => void;
}) {
  const slug = platform.slug;
  const label = slug.charAt(0).toUpperCase() + slug.slice(1);

  return (
    <label
      className={`flex items-start gap-3 rounded-lg border p-3 transition-colors ${
        platform.has_config
          ? "cursor-pointer hover:bg-muted/50"
          : "cursor-not-allowed opacity-60"
      }`}
    >
      <input
        type="checkbox"
        className="mt-0.5 h-4 w-4 shrink-0 accent-primary"
        checked={checked}
        disabled={!platform.has_config}
        onChange={() => platform.has_config && onToggle(slug)}
      />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">{label}</p>
        {!platform.has_config && (
          <p className="mt-0.5 text-xs text-muted-foreground">
            Not configured.{" "}
            <Link
              to={`/search-config?platform=${slug}`}
              className="text-primary underline underline-offset-2 hover:text-primary/80"
              onClick={(e) => e.stopPropagation()}
            >
              Configure this platform first
              <ExternalLink className="ml-0.5 inline h-3 w-3" />
            </Link>
          </p>
        )}
      </div>
    </label>
  );
}

export function RunPipelineDialog({
  open,
  onOpenChange,
  onRun,
  isRunning,
}: RunPipelineDialogProps) {
  const { platforms, isLoading } = usePlatforms();
  const [selected, setSelected] = useState<string[]>([]);

  function togglePlatform(slug: string) {
    setSelected((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]
    );
  }

  function handleConfirm() {
    if (selected.length === 0) return;
    onRun(selected);
    onOpenChange(false);
  }

  function handleOpenChange(next: boolean) {
    if (!next) {
      setSelected([]);
    }
    onOpenChange(next);
  }

  const canConfirm = selected.length > 0 && !isRunning;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Run Pipeline</DialogTitle>
          <DialogDescription>
            Select the platforms to scrape and evaluate jobs from.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 py-1">
          {isLoading && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading platforms...
            </p>
          )}
          {!isLoading && platforms.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No platforms registered.
            </p>
          )}
          {platforms.map((platform) => (
            <PlatformRow
              key={platform.slug}
              platform={platform}
              checked={selected.includes(platform.slug)}
              onToggle={togglePlatform}
            />
          ))}
        </div>

        <DialogFooter>
          <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
          <Button onClick={handleConfirm} disabled={!canConfirm}>
            {isRunning ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
