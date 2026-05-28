/** Customize CV dialog — original (read-only) and AI-tailored panes with diff highlighting. */

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Copy, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  TooltipProvider,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useCV, useCustomizeCV } from "@/hooks/use-cv";
import type { JobResult, CVSectionDiff } from "@/types/schemas";

function formatStructured(structured: Record<string, unknown>): string {
  return Object.entries(structured)
    .map(([key, value]) => {
      const heading = key.toUpperCase();
      return `${heading}\n${String(value ?? "")}`;
    })
    .join("\n\n");
}

interface CustomizeCVDialogProps {
  result: JobResult;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CustomizeCVDialog({ result, open, onOpenChange }: CustomizeCVDialogProps) {
  const { data: cvData } = useCV();
  const customizeMutation = useCustomizeCV();
  const [customizedText, setCustomizedText] = useState("");
  const [sections, setSections] = useState<CVSectionDiff[] | null>(null);
  const [adjustmentNotes, setAdjustmentNotes] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [showChangesOnly, setShowChangesOnly] = useState(false);
  const [humanize, setHumanize] = useState(true);
  const [humanizedApplied, setHumanizedApplied] = useState(false);

  const cv = cvData?.cv ?? null;
  const originalText = cv ? formatStructured(cv.structured as Record<string, unknown>) : "";

  useEffect(() => {
    if (!open) return;
    if (customizeMutation.isPending || customizedText) return;

    customizeMutation.mutate(
      { jobResultId: result.id, humanize },
      {
        onSuccess: (data) => {
          setCustomizedText(data.customized_text);
          setSections(data.sections ?? null);
          setWarnings(data.warnings ?? []);
          setHumanizedApplied(humanize);
        },
        onError: (err) => {
          toast.error(err.message || "Failed to generate customized CV.");
          onOpenChange(false);
        },
      },
    );
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function handleRegenerate() {
    customizeMutation.mutate(
      { jobResultId: result.id, forceRegenerate: true, adjustmentNotes: adjustmentNotes || undefined, humanize },
      {
        onSuccess: (data) => {
          setCustomizedText(data.customized_text);
          setSections(data.sections ?? null);
          setWarnings(data.warnings ?? []);
          setAdjustmentNotes("");
          setHumanizedApplied(humanize);
          toast.success("CV regenerated.");
        },
        onError: (err) => toast.error(err.message || "Failed to regenerate CV."),
      },
    );
  }

  function handleCopy() {
    navigator.clipboard.writeText(customizedText).then(
      () => toast.success("Copied to clipboard."),
      () => toast.error("Failed to copy."),
    );
  }

  function handleDownload() {
    const blob = new Blob([customizedText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cv-${result.title.slice(0, 40).replace(/[^a-z0-9]/gi, "-")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const isGenerating = customizeMutation.isPending;

  // Determine how many sections changed for the toggle label
  const changedCount = sections ? sections.filter((s) => s.changed).length : 0;

  return (
    <Dialog open={open} onOpenChange={(next) => {
      if (!next) {
        setCustomizedText("");
        setSections(null);
        setAdjustmentNotes("");
        setWarnings([]);
        setShowChangesOnly(false);
        setHumanizedApplied(false);
      }
      onOpenChange(next);
    }}>
      <DialogContent className="w-[95vw] max-w-[95vw] sm:max-w-[95vw] h-[90vh] flex flex-col gap-0 p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b shrink-0">
          <DialogTitle className="text-base truncate">
            Customize CV — {result.title}
          </DialogTitle>
        </DialogHeader>

        <div className="flex items-center gap-2 px-6 pt-4">
          <span className="text-xs text-muted-foreground">
            AI-tell protection
          </span>
          <Switch
            checked={humanize}
            onCheckedChange={setHumanize}
          />
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger className="cursor-help">
                <Info className="h-3.5 w-3.5 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                Rewrites the CV to sound more natural and reduce AI detection markers.
                Turn off for raw AI output.
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        {warnings.length > 0 && !isGenerating && (
          <div className="mx-6 mt-4 rounded-md border border-yellow-500/50 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-200">
            <p className="font-medium">This CV includes enhanced claims. Please verify the highlighted items match your actual qualifications.</p>
            <ul className="mt-1 list-disc list-inside text-xs text-yellow-300/80">
              {warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex flex-col md:flex-row flex-1 min-h-0 divide-y md:divide-y-0 md:divide-x">
          {/* Original CV pane */}
          <div className="flex flex-col md:flex-1 min-w-0 min-h-0 max-h-[35vh] md:max-h-none">
            <p className="px-4 py-2 text-xs font-medium text-muted-foreground uppercase bg-muted border-b shrink-0">
              Original CV
            </p>
            <div className="flex-1 overflow-y-auto p-4">
              <pre className="text-xs whitespace-pre-wrap font-mono leading-relaxed">
                {originalText || "No CV uploaded."}
              </pre>
            </div>
          </div>

          {/* Customized CV pane */}
          <div className="flex flex-col md:flex-1 min-w-0 min-h-0 flex-1">
            <div className="flex items-center justify-between px-4 py-2 text-xs font-medium text-muted-foreground uppercase bg-muted border-b shrink-0">
              <span>Customized CV</span>
              <div className="flex items-center gap-1.5">
                {humanizedApplied && (
                  <Badge variant="secondary" className="text-xs">
                    Humanized
                  </Badge>
                )}
                {warnings.length > 0 && !isGenerating && (
                  <Badge variant="outline" className="text-xs text-yellow-600">
                    {warnings.length} warning{warnings.length > 1 ? 's' : ''}
                  </Badge>
                )}
              </div>
              {sections && sections.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => setShowChangesOnly((prev) => !prev)}
                >
                  {showChangesOnly ? "Show all sections" : `Show changes only (${changedCount})`}
                </Button>
              )}
            </div>
            <div className="flex-1 overflow-y-auto p-4 min-h-0">
              {isGenerating ? (
                <div className="flex h-full items-center justify-center">
                  <p className="text-sm text-muted-foreground">Generating tailored CV...</p>
                </div>
              ) : sections && sections.length > 0 ? (
                <div className="space-y-3">
                  {sections
                    .filter((s) => showChangesOnly ? s.changed : true)
                    .map((section) => (
                      <div key={section.title}>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-bold text-sm uppercase tracking-wider text-muted-foreground">
                            {section.title}
                          </h3>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-5 w-5"
                            onClick={() => {
                              navigator.clipboard.writeText(section.content).then(
                                () => toast.success(`Copied ${section.title}`),
                                () => toast.error("Failed to copy."),
                              );
                            }}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                        <div className={
                          section.changed
                            ? "bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 pl-3 py-2 rounded-r"
                            : "pl-3 py-2 opacity-60"
                        }>
                          <pre className="whitespace-pre-wrap text-sm font-mono leading-relaxed">{section.content}</pre>
                        </div>
                        {!section.changed && (
                          <span className="text-xs text-muted-foreground ml-3">No changes</span>
                        )}
                      </div>
                    ))}
                </div>
              ) : (
                <Textarea
                  className="h-full resize-none font-mono text-xs leading-relaxed"
                  value={customizedText}
                  onChange={(e) => setCustomizedText(e.target.value)}
                  placeholder="Customized CV will appear here..."
                />
              )}
            </div>
          </div>
        </div>

        {/* Feedback + actions footer */}
        <div className="flex flex-col gap-3 px-6 py-4 border-t shrink-0">
          <Textarea
            className="resize-none text-sm min-h-[60px]"
            placeholder="Feedback for regeneration (optional) — e.g. 'Emphasize Rust experience more' or 'Remove the WordPress mention'"
            value={adjustmentNotes}
            onChange={(e) => setAdjustmentNotes(e.target.value)}
            disabled={isGenerating}
          />
          <div className="flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isGenerating}
              onClick={handleRegenerate}
            >
              {adjustmentNotes ? "Regenerate with feedback" : "Regenerate"}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!customizedText || isGenerating}
              onClick={handleCopy}
            >
              Copy
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={!customizedText || isGenerating}
              onClick={handleDownload}
            >
              Download .txt
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
