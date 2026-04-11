/** SearchConfigCard — displays a single search config with delete action. */

import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Platform, SearchConfigResponse } from "@/types/schemas";

const platformLabels: Record<Platform, string> = {
  upwork: "Upwork",
  linkedin: "LinkedIn",
};

const configFiltersSchema = z.object({
  experienceLevel: z.array(z.string()).optional(),
  jobType: z.array(z.string()).optional(),
  paymentVerified: z.boolean().optional(),
  maxJobAge: z.object({ value: z.number(), unit: z.string() }).optional(),
});

export interface SearchConfigCardProps {
  config: SearchConfigResponse;
  onDelete: (id: string) => void;
  isDeleting: boolean;
}

export function SearchConfigCard({ config, onDelete, isDeleting }: SearchConfigCardProps) {
  const parsed = configFiltersSchema.safeParse(config.filters);
  const { experienceLevel, jobType, paymentVerified, maxJobAge } = parsed.success
    ? parsed.data
    : {};

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            {platformLabels[config.platform as Platform] ?? config.platform}
          </CardTitle>
          <Badge variant="secondary">{config.platform}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {config.query && (
          <div>
            <span className="font-medium">Query:</span>{" "}
            <span className="text-muted-foreground">{config.query}</span>
          </div>
        )}
        {experienceLevel && experienceLevel.length > 0 && (
          <div>
            <span className="font-medium">Experience:</span>{" "}
            <span className="text-muted-foreground">
              {experienceLevel.join(", ")}
            </span>
          </div>
        )}
        {jobType && jobType.length > 0 && (
          <div>
            <span className="font-medium">Job type:</span>{" "}
            <span className="text-muted-foreground">
              {jobType.join(", ")}
            </span>
          </div>
        )}
        {paymentVerified !== undefined && (
          <div>
            <span className="font-medium">Payment verified:</span>{" "}
            <span className="text-muted-foreground">
              {paymentVerified ? "Yes" : "No"}
            </span>
          </div>
        )}
        {maxJobAge && (
          <div>
            <span className="font-medium">Max age:</span>{" "}
            <span className="text-muted-foreground">
              {maxJobAge.value} {maxJobAge.unit}
            </span>
          </div>
        )}
        <div className="text-xs text-muted-foreground">
          Updated: {new Date(config.updated_at).toLocaleDateString()}
        </div>
      </CardContent>
      <CardFooter className="justify-end">
        <Button
          variant="destructive"
          size="sm"
          disabled={isDeleting}
          onClick={() => onDelete(config.id)}
        >
          {isDeleting ? "Deleting..." : "Delete"}
        </Button>
      </CardFooter>
    </Card>
  );
}
