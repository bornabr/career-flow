"use client";

import { useAppStore } from "@/lib/store";
import { UploadStep } from "@/components/upload-step";
import { CVEditor } from "@/components/cv-editor";
import { PreviewPanel } from "@/components/preview-panel";
import { ChatWorkspace } from "@/components/chat-workspace";
import { ArtifactPanel } from "@/components/artifact-panel";
import { Button } from "@/components/ui/button";

export default function Home() {
  const { uiMode, setUiMode, step } = useAppStore();

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header with mode toggle */}
      <header className="sticky top-0 z-10 border-b bg-card">
        <div className="flex h-16 items-center justify-between px-4">
          <h1 className="text-xl font-bold tracking-tight">Career Flow</h1>

          <div className="flex gap-2">
            <Button
              variant={uiMode === "assistant" ? "default" : "outline"}
              onClick={() => setUiMode("assistant")}
            >
              Assistant
            </Button>
            <Button
              variant={uiMode === "quick" ? "default" : "outline"}
              onClick={() => setUiMode("quick")}
            >
              Quick Generate
            </Button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex flex-1 overflow-hidden">
        {uiMode === "assistant" ? (
          <div className="flex w-full">
            {/* Left: Chat */}
            <div className="w-1/2 border-r">
              <ChatWorkspace />
            </div>
            {/* Right: Artifact */}
            <div className="w-1/2">
              <ArtifactPanel />
            </div>
          </div>
        ) : (
          <div className="w-full overflow-y-auto p-4 md:p-8">
            <div className="mx-auto max-w-[1600px]">
              {step === "upload" && <UploadStep />}
              {step === "edit" && (
                <div className="flex flex-col gap-8 lg:flex-row">
                  <div className="w-full lg:w-[55%]">
                    <CVEditor />
                  </div>
                  <div className="w-full lg:w-[45%]">
                    <PreviewPanel />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
