/** Single result row — expandable with score, title, recommendation, details. */

import { useState } from "react";
import { ChevronDownIcon, ExternalLinkIcon, Loader2Icon, Trash2Icon } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScoreBadge } from "@/components/score-badge";
import { AddToListMenu } from "@/components/add-to-list-menu";
import { CustomizeCVDialog } from "@/components/customize-cv-dialog";
import { evaluateJob } from "@/api/results";
import { useLists } from "@/hooks/use-lists";
import { useCV } from "@/hooks/use-cv";
import { useProfile } from "@/hooks/use-profile";
import { resultStatusValues, type JobResult, type ResultStatus } from "@/types/schemas";

interface ResultRowProps {
  result: JobResult;
  onStatusChange: (resultId: string, status: string) => void;
  onDelete: (resultId: string) => Promise<void>;
  isUpdating: boolean;
  isDeleting: boolean;
}

const statusLabels: Record<ResultStatus, string> = {
  new: "New",
  applied: "Applied",
  dismissed: "Dismissed",
};

export function ResultRow({ result, onStatusChange, onDelete, isUpdating, isDeleting }: ResultRowProps) {
  const [open, setOpen] = useState(false);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [customizeCVOpen, setCustomizeCVOpen] = useState(false);
  const evaluation = result.evaluation;
  const queryClient = useQueryClient();
  const { addJob, removeJob } = useLists();
  const { data: cvData } = useCV();
  const { profile } = useProfile();

  const evaluateJobMutation = useMutation({
    mutationFn: (resultId: string) => evaluateJob(resultId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["results"] });
      queryClient.invalidateQueries({ queryKey: ["lists"] });
    },
  });

  const cvThreshold = profile?.cv_customize_threshold ?? 7;
  const showCustomizeCV = (result.score ?? 0) >= cvThreshold && cvData?.cv != null;
  const showEvaluate = result.evaluation === null && result.score !== null;

  async function handleAddToList(listId: string) {
    await addJob({ listId, jobResultId: result.id });
    queryClient.invalidateQueries({ queryKey: ["result-lists", result.id] });
    queryClient.invalidateQueries({ queryKey: ["lists", "jobs", listId] });
  }

  async function handleRemoveFromList(listId: string) {
    await removeJob({ listId, jobResultId: result.id });
    queryClient.invalidateQueries({ queryKey: ["result-lists", result.id] });
    queryClient.invalidateQueries({ queryKey: ["lists", "jobs", listId] });
  }

  async function handleEvaluate() {
    try {
      await evaluateJobMutation.mutateAsync(result.id);
      toast.success("Evaluation complete");
      // Auto-expand the row to show the evaluation
      setOpen(true);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to evaluate job");
    }
  }

  return (
    <>
    <CustomizeCVDialog
      result={result}
      open={customizeCVOpen}
      onOpenChange={setCustomizeCVOpen}
    />
    <Dialog open={confirmDeleteOpen} onOpenChange={setConfirmDeleteOpen}>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>Delete this job?</DialogTitle>
          <DialogDescription>
            This will permanently remove "{result.title}" from your results. This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose render={<Button variant="outline">Cancel</Button>} />
          <Button
            variant="destructive"
            disabled={isDeleting}
            onClick={async () => {
              await onDelete(result.id);
              setConfirmDeleteOpen(false);
            }}
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card className="overflow-hidden">
        <div className="flex items-center gap-3 p-4">
          {/* Clickable expand/collapse area */}
          <CollapsibleTrigger className="flex min-w-0 flex-1 items-center gap-3 text-left">
            <ScoreBadge score={result.score} />

            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{result.title}</p>
              <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                <Badge variant="outline" className="text-xs">
                  {result.platform}
                </Badge>
                {result.skip_reason === "language" && result.detected_language && (
                  <Badge variant="secondary" className="text-xs">
                    {result.detected_language}
                  </Badge>
                )}
                {result.skip_reason === "language" && (
                  <span className="text-muted-foreground italic">
                    Language not in profile
                  </span>
                )}
                {evaluation?.recommendation && (
                  <span className="truncate">{evaluation.recommendation}</span>
                )}
              </div>
            </div>

            <ChevronDownIcon
              className={`size-4 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
            />
          </CollapsibleTrigger>

          {/* Interactive controls — outside the trigger to avoid nested buttons */}
          <div className="flex shrink-0 items-center gap-2">
            {showEvaluate && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleEvaluate}
                disabled={evaluateJobMutation.isPending}
              >
                {evaluateJobMutation.isPending ? (
                  <>
                    <Loader2Icon className="mr-1 size-3 animate-spin" />
                    Evaluating...
                  </>
                ) : (
                  "Evaluate"
                )}
              </Button>
            )}
            {showCustomizeCV && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCustomizeCVOpen(true)}
              >
                Customize CV
              </Button>
            )}
            <Select
              value={result.status}
              onValueChange={(val) => onStatusChange(result.id, val as string)}
              disabled={isUpdating}
            >
              <SelectTrigger size="sm">
                <SelectValue>{statusLabels[result.status as ResultStatus] ?? result.status}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {resultStatusValues.map((s) => (
                  <SelectItem key={s} value={s}>
                    {statusLabels[s]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <AddToListMenu
              jobResultId={result.id}
              onAdd={handleAddToList}
              onRemove={handleRemoveFromList}
            />

            <Button
              variant="ghost"
              size="icon"
              className="size-8 text-muted-foreground hover:text-destructive"
              onClick={() => setConfirmDeleteOpen(true)}
              disabled={isDeleting}
              aria-label="Delete job"
            >
              <Trash2Icon className="size-4" />
            </Button>
          </div>
        </div>

        <CollapsibleContent>
          <CardContent className="space-y-4 border-t pt-4">
            {/* Inline loading state for evaluation */}
            {evaluateJobMutation.isPending && (
              <div className="flex items-center gap-2 rounded-md bg-muted/50 p-3 text-sm">
                <Loader2Icon className="size-4 animate-spin text-muted-foreground" />
                <span className="text-muted-foreground">Evaluating with AI...</span>
              </div>
            )}

            {/* Summary */}
            {evaluation?.summary && (
              <div>
                <h4 className="mb-1 text-xs font-medium uppercase text-muted-foreground">
                  Summary
                </h4>
                <p className="text-sm break-words">{evaluation.summary}</p>
              </div>
            )}

            {/* Evaluation */}
            {evaluation?.evaluation && (
              <div>
                <h4 className="mb-1 text-xs font-medium uppercase text-muted-foreground">
                  Evaluation
                </h4>
                <p className="text-sm whitespace-pre-wrap break-words">{evaluation.evaluation}</p>
              </div>
            )}

            {/* Flags */}
            {evaluation?.flags && (
              <div>
                <h4 className="mb-1 text-xs font-medium uppercase text-muted-foreground">
                  Flags
                </h4>
                <p className="text-sm break-words">{evaluation.flags}</p>
              </div>
            )}

            {/* Scratchpad */}
            {evaluation?.scratchpad && (
              <div>
                <h4 className="mb-1 text-xs font-medium uppercase text-muted-foreground">
                  Scratchpad
                </h4>
                <p className="text-sm whitespace-pre-wrap break-words text-muted-foreground">
                  {evaluation.scratchpad}
                </p>
              </div>
            )}

            {/* Job link */}
            <div>
              <a
                href={result.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline dark:text-blue-400"
              >
                View job posting
                <ExternalLinkIcon className="size-3" />
              </a>
              <span className="ml-3 text-xs text-muted-foreground">
                {new Date(result.created_at).toLocaleDateString()}
              </span>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
    </>
  );
}
