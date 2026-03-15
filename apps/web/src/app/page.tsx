"use client";

import { useAppStore } from "@/lib/store";
import { UploadStep } from "@/components/upload-step";
import { CVEditor } from "@/components/cv-editor";
import { PreviewPanel } from "@/components/preview-panel";
import { Badge } from "@/components/ui/badge";

export default function Home() {
  const { step } = useAppStore();

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top Header Bar */}
      <header className="border-b bg-card sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight">Career Flow</h1>
          </div>
          
          <div className="flex items-center gap-2">
            <Badge 
              variant={step === "upload" ? "default" : "secondary"}
              className={step === "upload" ? "" : "opacity-50"}
            >
              1. Upload
            </Badge>
            <span className="text-muted-foreground text-sm">→</span>
            <Badge 
              variant={step === "edit" ? "default" : "secondary"}
              className={step === "edit" ? "" : "opacity-50"}
            >
              2. Edit & Preview
            </Badge>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-4 md:p-8">
        <div className="max-w-[1600px] mx-auto">
          {step === "upload" && <UploadStep />}
          {step === "edit" && (
            <div className="flex flex-col lg:flex-row gap-8">
              <div className="w-full lg:w-[55%]">
                <CVEditor />
              </div>
              <div className="w-full lg:w-[45%]">
                <PreviewPanel />
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
