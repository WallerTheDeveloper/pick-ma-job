/** Proposal dialog — generate and display Upwork proposals with copy/download/regenerate. */

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
import { useGenerateProposal } from "@/hooks/use-proposal";
import { getCachedProposal } from "@/api/proposals";
import type { JobResult } from "@/types/schemas";

interface ProposalDialogProps {
  result: JobResult;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProposalDialog({ result, open, onOpenChange }: ProposalDialogProps) {
  const generateMutation = useGenerateProposal();
  const [proposalText, setProposalText] = useState("");
  const [adjustmentNotes, setAdjustmentNotes] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (generateMutation.isPending || proposalText) return;

    let cancelled = false;
    setIsLoading(true);

    // Try fetching cached first, then generate if not found
    getCachedProposal(result.id)
      .then((data) => {
        if (!cancelled) {
          setProposalText(data.proposal_text);
          setIsLoading(false);
        }
      })
      .catch(() => {
        // No cached proposal — generate one
        if (!cancelled) {
          generateMutation.mutate(
            { resultId: result.id },
            {
              onSuccess: (data) => {
                if (!cancelled) {
                  setProposalText(data.proposal_text);
                  setIsLoading(false);
                }
              },
              onError: (err) => {
                if (!cancelled) {
                  toast.error(err.message || "Failed to generate proposal.");
                  setIsLoading(false);
                  onOpenChange(false);
                }
              },
            },
          );
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function handleRegenerate() {
    generateMutation.mutate(
      { resultId: result.id, forceRegenerate: true, adjustmentNotes: adjustmentNotes || undefined },
      {
        onSuccess: (data) => {
          setProposalText(data.proposal_text);
          setAdjustmentNotes("");
          toast.success("Proposal regenerated.");
        },
        onError: (err) => toast.error(err.message || "Failed to regenerate proposal."),
      },
    );
  }

  function handleCopy() {
    navigator.clipboard.writeText(proposalText).then(
      () => toast.success("Copied to clipboard."),
      () => toast.error("Failed to copy."),
    );
  }

  function handleDownload() {
    const blob = new Blob([proposalText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `proposal-${result.title.slice(0, 40).replace(/[^a-z0-9]/gi, "-")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const isGenerating = generateMutation.isPending || isLoading;

  return (
    <Dialog open={open} onOpenChange={(next) => {
      if (!next) {
        setProposalText("");
        setAdjustmentNotes("");
        setIsLoading(false);
      }
      onOpenChange(next);
    }}>
      <DialogContent className="w-[90vw] max-w-[800px] h-[80vh] flex flex-col gap-0 p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b shrink-0">
          <DialogTitle className="text-base truncate">
            Write Proposal — {result.title}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 min-h-0 overflow-y-auto p-6">
          {isGenerating ? (
            <div className="flex h-full items-center justify-center">
              <p className="text-sm text-muted-foreground">Generating proposal...</p>
            </div>
          ) : proposalText ? (
            <div className="whitespace-pre-wrap text-sm font-mono leading-relaxed">
              {proposalText}
            </div>
          ) : (
            <div className="flex h-full items-center justify-center">
              <p className="text-sm text-muted-foreground">No proposal generated yet.</p>
            </div>
          )}
        </div>

        {/* Feedback + actions footer */}
        <div className="flex flex-col gap-3 px-6 py-4 border-t shrink-0">
          <Textarea
            className="resize-none text-sm min-h-[60px]"
            placeholder="Feedback for regeneration (optional) — e.g. 'Emphasize React experience more' or 'Make it shorter'"
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
              disabled={!proposalText || isGenerating}
              onClick={handleCopy}
            >
              Copy
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={!proposalText || isGenerating}
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