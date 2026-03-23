"use client";

import { useAppStore } from "@/lib/store";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import type { InteractiveReviewMemo } from "@/lib/types";

interface ReviewerMemoCardProps {
  memo: InteractiveReviewMemo;
}

function capitalizeRole(role: string): string {
  if (role === "ats") return "ATS";
  if (role === "hr") return "HR";
  return role.charAt(0).toUpperCase() + role.slice(1);
}

function getSeverityBadgeClassName(
  severity: "critical" | "warning" | "suggestion"
): string {
  switch (severity) {
    case "critical":
      return "bg-red-500 text-white";
    case "warning":
      return "bg-yellow-500 text-black";
    case "suggestion":
      return "bg-blue-500 text-white";
    default:
      return "";
  }
}

export function ReviewerMemoCard({ memo }: ReviewerMemoCardProps) {
  const reviewDecisions = useAppStore((state) => state.reviewDecisions);
  const setReviewDecision = useAppStore((state) => state.setReviewDecision);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{capitalizeRole(memo.reviewer_role)} Reviewer</CardTitle>
        <CardDescription>
          Score: {memo.overall_score}/10 — {memo.overall_rationale}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {memo.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No recommendations from this reviewer.
          </p>
        ) : (
          memo.items.map((item) => {
            const isAccepted = reviewDecisions[item.item_key] ?? true;

            return (
              <div
                key={item.item_key}
                className="flex items-start gap-3 rounded-lg border p-3"
              >
                <Switch
                  checked={isAccepted}
                  onCheckedChange={(checked) =>
                    setReviewDecision(item.item_key, checked)
                  }
                  aria-label={`Accept recommendation: ${item.recommendation}`}
                />
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={getSeverityBadgeClassName(item.severity)}
                    >
                      {item.severity}
                    </Badge>
                    <Label className="font-medium">
                      {item.recommendation}
                    </Label>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {item.rationale}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
