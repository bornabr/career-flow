"use client";

import { useAppStore } from "@/lib/store";
import { Loader2, Check, AlertCircle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";

export function GenerationProgress() {
  const {
    runStatus,
    activeStep,
    completedSteps,
    liveReviewMemos,
    generationError,
  } = useAppStore();

  // Hidden when idle
  if (runStatus === "idle") return null;

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Generation Progress</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Error state */}
        {generationError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Generation Failed</AlertTitle>
            <AlertDescription>{generationError}</AlertDescription>
          </Alert>
        )}

        {/* Pipeline steps */}
        <div className="space-y-2">
          {/* Completed steps */}
          {completedSteps.map((step, idx) => (
            <div key={`${step}-${idx}`} className="flex items-center gap-2">
              <Check className="h-4 w-4 text-green-600" />
              <span className="text-sm">{step}</span>
            </div>
          ))}

          {/* Active step */}
          {activeStep && (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
              <span className="text-sm font-medium">{activeStep}</span>
            </div>
          )}
        </div>

        {/* Reviewer memos */}
        {liveReviewMemos.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Reviewer Feedback</h3>
            {liveReviewMemos.map((memo, idx) => (
              <Card key={idx} className="border-l-4 border-l-blue-500">
                <CardContent className="pt-4">
                  <div className="space-y-1">
                    <p className="text-sm font-medium">
                      {memo.reviewer} (Score: {memo.score}/10)
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {memo.summary}
                    </p>
                    {memo.suggestions && memo.suggestions.length > 0 && (
                      <ul className="text-xs text-muted-foreground list-disc list-inside">
                        {memo.suggestions.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Success state */}
        {runStatus === "completed" && !generationError && (
          <Alert>
            <Check className="h-4 w-4" />
            <AlertTitle>Generation Complete</AlertTitle>
            <AlertDescription>
              Your CV has been successfully tailored.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
