/** Score badge with color coding based on relevancy score. */

import { Badge } from "@/components/ui/badge";

interface ScoreBadgeProps {
  score: number | null;
}

function getScoreColor(score: number): string {
  if (score >= 9) return "bg-green-600 text-white";
  if (score >= 7) return "bg-blue-600 text-white";
  if (score >= 5) return "bg-yellow-500 text-black";
  if (score >= 3) return "bg-orange-500 text-white";
  return "bg-red-600 text-white";
}

export function ScoreBadge({ score }: ScoreBadgeProps) {
  if (score === null) {
    return (
      <Badge variant="outline" className="tabular-nums">
        —
      </Badge>
    );
  }

  return (
    <Badge className={`${getScoreColor(score)} tabular-nums border-transparent`}>
      {score}/10
    </Badge>
  );
}
