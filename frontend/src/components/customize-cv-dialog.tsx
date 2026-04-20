/** Customize CV dialog — original (read-only) and AI-tailored (editable) panes. */

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { useCV, useCustomizeCV } from "@/hooks/use-cv";
import type { JobResult } from "@/types/schemas";

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

  const cv = cvData?.cv ?? null;
  const originalText = cv ? formatStructured(cv.structured as Record<string, unknown>) : "";

  useEffect(() => {
    if (!open) return;
    if (customizeMutation.isPending || customizedText) return;

    customizeMutation.mutate(
      { jobResultId: result.id },
      {
        onSuccess: (data) => setCustomizedText(data.customized_text),
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
      { jobResultId: result.id, forceRegenerate: true },
      {
        onSuccess: (data) => {
          setCustomizedText(data.customized_text);
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

  return (
    <Dialog open={open} onOpenChange={(next) => {
      if (!next) setCustomizedText("");
      onOpenChange(next);
    }}>
      <DialogContent className="max-w-5xl h-[80vh] flex flex-col gap-0 p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b">
          <DialogTitle className="text-base truncate">
            Customize CV — {result.title}
          </DialogTitle>
        </DialogHeader>

        <div className="flex flex-1 min-h-0 gap-0 divide-x">
          {/* Original CV pane */}
          <div className="flex flex-col flex-1 min-w-0">
            <p className="px-4 py-2 text-xs font-medium text-muted-foreground uppercase bg-muted border-b">
              Original CV
            </p>
            <div className="flex-1 overflow-y-auto p-4">
              <pre className="text-xs whitespace-pre-wrap font-mono leading-relaxed">
                {originalText || "No CV uploaded."}
              </pre>
            </div>
          </div>

          {/* Customized CV pane */}
          <div className="flex flex-col flex-1 min-w-0">
            <p className="px-4 py-2 text-xs font-medium text-muted-foreground uppercase bg-muted border-b">
              Customized CV
            </p>
            <div className="flex-1 p-4">
              {isGenerating ? (
                <div className="flex h-full items-center justify-center">
                  <p className="text-sm text-muted-foreground">Generating tailored CV...</p>
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

        {/* Footer actions */}
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={isGenerating}
            onClick={handleRegenerate}
          >
            Regenerate
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
      </DialogContent>
    </Dialog>
  );
}
