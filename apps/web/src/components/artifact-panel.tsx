"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAppStore } from "@/lib/store";
import { CVEditor } from "@/components/cv-editor";
import { PreviewPanel } from "@/components/preview-panel";
import { ReviewCommitteePanel } from "@/components/review-committee-panel";

export function ArtifactPanel() {
  const { artifactTab, setArtifactTab } = useAppStore();

  return (
    <div className="flex h-full flex-col">
      <Tabs value={artifactTab} onValueChange={setArtifactTab} className="flex h-full flex-col">
        <TabsList className="w-full justify-start">
          <TabsTrigger value="cv">CV</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
          <TabsTrigger value="reviews">Reviews</TabsTrigger>
        </TabsList>
        <TabsContent value="cv" className="flex-1 overflow-y-auto">
          <CVEditor />
        </TabsContent>
        <TabsContent value="preview" className="flex-1 overflow-y-auto">
          <PreviewPanel />
        </TabsContent>
        <TabsContent value="reviews" className="flex-1 overflow-y-auto">
          <ReviewCommitteePanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
