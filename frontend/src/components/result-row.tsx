/** Single result row — expandable with score, title, recommendation, details. */

import { useState } from "react";
import { ChevronDownIcon, ExternalLinkIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScoreBadge } from "@/components/score-badge";
import { resultStatusValues, type JobResult, type ResultStatus } from "@/types/schemas";

interface ResultRowProps {
  result: JobResult;
  onStatusChange: (resultId: string, status: string) => void;
  isUpdating: boolean;
}

const statusLabels: Record<ResultStatus, string> = {
  new: "New",
  applied: "Applied",
  dismissed: "Dismissed",
};

export function ResultRow({ result, onStatusChange, isUpdating }: ResultRowProps) {
  const [open, setOpen] = useState(false);
  const evaluation = result.evaluation;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <Card className="overflow-hidden">
        <CollapsibleTrigger className="w-full text-left">
          <div className="flex items-center gap-3 p-4">
            <ScoreBadge score={result.score} />

            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{result.title}</p>
              <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                <Badge variant="outline" className="text-xs">
                  {result.platform}
                </Badge>
                {evaluation?.recommendation && (
                  <span className="truncate">{evaluation.recommendation}</span>
                )}
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              {/* Status dropdown — stop propagation to prevent collapsible toggle */}
              <div
                onClick={(e) => e.stopPropagation()}
                onKeyDown={(e) => e.stopPropagation()}
              >
                <Select
                  value={result.status}
                  onValueChange={(val) => onStatusChange(result.id, val as string)}
                  disabled={isUpdating}
                >
                  <SelectTrigger size="sm">
                    <SelectValue>{statusLabels[result.status]}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {resultStatusValues.map((s) => (
                      <SelectItem key={s} value={s}>
                        {statusLabels[s]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <ChevronDownIcon
                className={`size-4 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
              />
            </div>
          </div>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <CardContent className="space-y-4 border-t pt-4">
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
  );
}
