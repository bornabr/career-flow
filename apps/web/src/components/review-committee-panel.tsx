"use client";

import { useAppStore } from "@/lib/store";
import { ReviewerMemoCard } from "./reviewer-memo-card";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useState } from "react";

export function ReviewCommitteePanel() {
  const pendingReviewApproval = useAppStore(
    (state) => state.pendingReviewApproval
  );
  const reviewDecisions = useAppStore((state) => state.reviewDecisions);
  const isAwaitingReviewApproval = useAppStore(
    (state) => state.isAwaitingReviewApproval
  );
  const reviewSubmitHandler = useAppStore(
    (state) => state.reviewSubmitHandler
  );
  
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!pendingReviewApproval) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No Review Pending</CardTitle>
          <CardDescription>
            The AI review committee will display recommendations here when available.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const { interactive_reviews, consensus_score } = pendingReviewApproval;
  const hasDecisions = Object.keys(reviewDecisions).length > 0;

  const handleSubmit = async () => {
    if (!reviewSubmitHandler) {
      return;
    }

    setIsSubmitting(true);
    try {
      await reviewSubmitHandler();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <Card>
        <CardHeader>
          <CardTitle>AI Review Committee</CardTitle>
          <CardDescription>
            Consensus Score: {consensus_score}/10 — Review the recommendations
            below and accept or reject each item.
          </CardDescription>
        </CardHeader>
      </Card>

      <div className="flex-1 space-y-4 overflow-y-auto">
        {interactive_reviews.map((memo) => (
          <ReviewerMemoCard key={memo.reviewer_role} memo={memo} />
        ))}
      </div>

      <div className="flex justify-end gap-2 border-t pt-4">
        <Button
          onClick={handleSubmit}
          disabled={isAwaitingReviewApproval || !hasDecisions || isSubmitting}
        >
          {isSubmitting ? "Submitting..." : "Submit Review Decisions"}
        </Button>
      </div>
    </div>
  );
}
