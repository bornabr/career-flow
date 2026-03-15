"use client";

import { useEffect, useMemo, useState, useRef } from "react";
import { Download, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { generatePDF, getPreviewHTML } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

const MARGIN_OPTIONS = {
  compact: "0.55in",
  normal: "0.75in",
  spacious: "1in",
} as const;

export function PreviewPanel() {
  const {
    cvData,
    template,
    setTemplate,
    customStyles,
    updateCustomStyle,
    previewHtml,
    setPreviewHtml,
    isLoadingPreview,
    setIsLoadingPreview,
    setStep,
  } = useAppStore();

  const [isDownloading, setIsDownloading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  const primaryColor = customStyles.primary_color ?? "#0f172a";
  const fontFamily = customStyles.font_family ?? "Georgia, serif";
  const margin = useMemo(() => {
    const current = customStyles.margin ?? MARGIN_OPTIONS.normal;
    return current === MARGIN_OPTIONS.compact || current === MARGIN_OPTIONS.normal || current === MARGIN_OPTIONS.spacious
      ? current
      : MARGIN_OPTIONS.normal;
  }, [customStyles.margin]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const width = entry.contentRect.width;
        // The iframe content is 8.5in wide (816px at 96dpi)
        setScale(width / 816);
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!cvData) {
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      try {
        setIsLoadingPreview(true);
        const cvPayload = cvData as unknown as Record<string, unknown>;
        const html = await getPreviewHTML({
          cv_data: cvPayload,
          template,
          custom_styles: customStyles,
        });
        setPreviewHtml(html);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to load preview";
        toast.error(message);
      } finally {
        setIsLoadingPreview(false);
      }
    }, 400);

    return () => window.clearTimeout(timeoutId);
  }, [cvData, template, customStyles, setIsLoadingPreview, setPreviewHtml]);

  const onDownloadPdf = async () => {
    if (!cvData) {
      toast.error("No CV data available to export.");
      return;
    }

    try {
      setIsDownloading(true);
      const cvPayload = cvData as unknown as Record<string, unknown>;
      const blob = await generatePDF({
        cv_data: cvPayload,
        template,
        custom_styles: customStyles,
      });

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${cvData.name || "career-flow-cv"}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
      toast.success("PDF generated and download started.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to generate PDF";
      toast.error(message);
    } finally {
      setIsDownloading(false);
    }
  };

  if (!cvData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No CV data yet</CardTitle>
          <CardDescription>Generate and edit your CV before using preview and export.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => setStep("upload")}>Back to Upload</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6 sticky top-24">
      <Card className="h-fit">
        <CardHeader>
          <CardTitle>Preview Controls</CardTitle>
          <CardDescription>Select a template and customize style before export.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Template</Label>
              <Select
                value={template}
                onValueChange={(value) => {
                  if (value) {
                    setTemplate(value);
                  }
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="engineering">Engineering</SelectItem>
                  <SelectItem value="classic">Classic</SelectItem>
                  <SelectItem value="modern">Modern</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Font family</Label>
              <Select
                value={fontFamily}
                onValueChange={(value) => {
                  if (value) {
                    updateCustomStyle("font_family", value);
                  }
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Georgia, serif">Georgia</SelectItem>
                  <SelectItem value="Helvetica, Arial, sans-serif">Helvetica</SelectItem>
                  <SelectItem value="'Times New Roman', serif">Times New Roman</SelectItem>
                  <SelectItem value="'Trebuchet MS', sans-serif">Trebuchet MS</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="primary-color">Primary color</Label>
              <div className="flex gap-2">
                <Input
                  id="primary-color"
                  value={primaryColor}
                  onChange={(event) => updateCustomStyle("primary_color", event.target.value)}
                  placeholder="#0f172a"
                />
                <Input
                  type="color"
                  value={primaryColor}
                  onChange={(event) => updateCustomStyle("primary_color", event.target.value)}
                  className="h-8 w-11 p-1"
                  aria-label="Pick primary color"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Margins</Label>
              <Select
                value={margin}
                onValueChange={(value) => {
                  if (value) {
                    updateCustomStyle("margin", value);
                  }
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={MARGIN_OPTIONS.compact}>Compact</SelectItem>
                  <SelectItem value={MARGIN_OPTIONS.normal}>Normal</SelectItem>
                  <SelectItem value={MARGIN_OPTIONS.spacious}>Spacious</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Separator />

          <div className="flex flex-col gap-2">
            <Button onClick={onDownloadPdf} disabled={isDownloading || isLoadingPreview} className="w-full">
              {isDownloading ? (
                <>
                  <Loader2 className="size-4 animate-spin mr-2" />
                  Downloading...
                </>
              ) : (
                <>
                  <Download className="size-4 mr-2" />
                  Download PDF
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Live Preview</CardTitle>
          <CardDescription>Review layout and typography before final export.</CardDescription>
        </CardHeader>
        <CardContent>
          <div ref={containerRef} className="overflow-hidden rounded-xl border bg-muted/30 w-full" style={{ height: `${2200 * scale}px` }}>
            {isLoadingPreview && !previewHtml ? (
              <div className="space-y-3 p-6">
                <Skeleton className="h-8 w-1/2" />
                <Skeleton className="h-5 w-full" />
                <Skeleton className="h-5 w-11/12" />
                <Skeleton className="h-5 w-10/12" />
                <Skeleton className="h-48 w-full" />
              </div>
            ) : (
              <div style={{ transform: `scale(${scale})`, transformOrigin: 'top left', width: '816px', height: '2200px' }}>
                <iframe title="CV preview" className="h-full w-full bg-white" srcDoc={previewHtml} />
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
