"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAppStore } from "@/lib/store";

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
        <TabsContent value="cv" className="flex-1 overflow-y-auto p-4">
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <p>CV editor will go here</p>
          </div>
        </TabsContent>
        <TabsContent value="preview" className="flex-1 overflow-y-auto p-4">
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <p>CV preview will go here</p>
          </div>
        </TabsContent>
        <TabsContent value="reviews" className="flex-1 overflow-y-auto p-4">
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <p>Review panel (Phase 4)</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
