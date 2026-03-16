"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Eye, EyeOff, FileUp, Loader2, X } from "lucide-react";
import { toast } from "sonner";

import { parseDocuments, generateCV, getModels } from "@/lib/api";
import type { CV } from "@/lib/types";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

const ACCEPTED_FILE_TYPES = ".pdf,.docx,.png,.jpg,.jpeg,.webp,.txt";

interface ProviderModels {
  [provider: string]: string[];
}

export function UploadStep() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);

  // Model selector state
  const [providers, setProviders] = useState<ProviderModels>({});
  const [availableProviders, setAvailableProviders] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState("");
  const [defaultModel, setDefaultModel] = useState("");
  const [defaultReviewModel, setDefaultReviewModel] = useState("");
  const [reviewProvider, setReviewProvider] = useState("");

  const {
    jobDescription,
    setJobDescription,
    userInstructions,
    setUserInstructions,
    apiKey,
    setApiKey,
    uploadedFileNames,
    setUploadedFileNames,
    selectedModel,
    setSelectedModel,
    reviewMode,
    setReviewMode,
    reviewModel,
    setReviewModel,
    setResumeText,
    setCvData,
    setAtsIssues,
    setHallucinationWarnings,
    setStep,
    isParsing,
    setIsParsing,
    isGenerating,
    setIsGenerating,
  } = useAppStore();

  const isBusy = isParsing || isGenerating;

  // Load available models on mount
  useEffect(() => {
    getModels()
      .then((data) => {
        setProviders(data.providers);
        setAvailableProviders(data.available_providers);
        setDefaultModel(data.default);
        setDefaultReviewModel(data.default_review_model ?? "");

        const defaultProvider = data.default.includes(":")
          ? data.default.split(":")[0]
          : "openai";

        if (!selectedProvider) {
          if (data.available_providers.includes(defaultProvider)) {
            setSelectedProvider(defaultProvider);
          } else if (data.available_providers.length > 0) {
            setSelectedProvider(data.available_providers[0]);
          }
        }

        const defaultRevProvider = data.default_review_model?.includes(":")
          ? data.default_review_model.split(":")[0]
          : "";
        if (!reviewProvider && defaultRevProvider) {
          setReviewProvider(defaultRevProvider);
        }
      })
      .catch(() => {
        // Silently fail — user can still use the app with server defaults
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFilesSelect = useCallback(
    (newFiles: FileList | null) => {
      if (!newFiles || newFiles.length === 0) return;

      const added = Array.from(newFiles);
      setFiles((prev) => {
        // Prevent duplicates by name
        const existingNames = new Set(prev.map((f) => f.name));
        const unique = added.filter((f) => !existingNames.has(f.name));
        return [...prev, ...unique];
      });

      const newNames = added.map((f) => f.name);
      const existingSet = new Set(uploadedFileNames);
      const uniqueNames = newNames.filter((n) => !existingSet.has(n));
      if (uniqueNames.length > 0) {
        setUploadedFileNames([...uploadedFileNames, ...uniqueNames]);
      }
    },
    [uploadedFileNames, setUploadedFileNames]
  );

  const removeFile = useCallback(
    (fileName: string) => {
      setFiles((prev) => prev.filter((f) => f.name !== fileName));
      setUploadedFileNames(uploadedFileNames.filter((n) => n !== fileName));
    },
    [uploadedFileNames, setUploadedFileNames]
  );

  const onGenerate = async () => {
    if (files.length === 0) {
      toast.error("Please upload at least one document.");
      return;
    }

    if (!jobDescription.trim()) {
      toast.error("Please provide a job description.");
      return;
    }

    try {
      setIsParsing(true);
      const parsed = await parseDocuments(files);
      setResumeText(parsed.combined_text);
      setUploadedFileNames(parsed.files.map((f) => f.filename));
      setIsParsing(false);

      setIsGenerating(true);

      // Build the model_name to send: "provider:model-id" or null for server default
      const modelToSend = selectedModel || null;

      const generated = await generateCV({
        resume_text: parsed.combined_text,
        job_description: jobDescription.trim(),
        user_instructions: userInstructions.trim() || null,
        api_key: apiKey.trim() || null,
        model_name: modelToSend,
        review_mode: reviewMode,
        review_model: reviewModel || null,
      });

      setCvData(generated.cv_data as unknown as CV);
      setAtsIssues(generated.ats_issues);
      setHallucinationWarnings(generated.hallucination_warnings);
      setStep("edit");
      toast.success("CV generated. You can now refine every section.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to generate CV";
      toast.error(message);
    } finally {
      setIsParsing(false);
      setIsGenerating(false);
    }
  };

  const hasClientKey = apiKey.trim().length > 0;
  const providerNames = hasClientKey
    ? Object.keys(providers)
    : availableProviders.filter((p) => p in providers);
  const modelsForProvider = selectedProvider ? providers[selectedProvider] ?? [] : [];
  const reviewModelsForProvider = reviewProvider ? providers[reviewProvider] ?? [] : [];

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Upload and Generate</CardTitle>
        <CardDescription>
          Upload your documents (resume, portfolio, project descriptions, etc.) and target role to generate a tailored first draft.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* ─── File Upload ─────────────────────────────────── */}
        <div className="space-y-2">
          <Label htmlFor="file-upload">Source documents</Label>
          <input
            id="file-upload"
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_FILE_TYPES}
            multiple
            className="hidden"
            onChange={(event) => handleFilesSelect(event.target.files)}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              handleFilesSelect(event.dataTransfer.files);
            }}
            className={[
              "flex w-full flex-col items-center justify-center gap-3 rounded-xl border border-dashed px-6 py-10 text-center transition",
              dragging
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/60 hover:bg-muted/40",
            ].join(" ")}
            disabled={isBusy}
          >
            <FileUp className="size-8 text-muted-foreground" />
            <div className="space-y-1">
              <p className="text-sm font-medium">Drag and drop files here</p>
              <p className="text-xs text-muted-foreground">
                or click to browse — supports multiple files (PDF, DOCX, PNG, JPEG, WEBP, TXT)
              </p>
            </div>
          </button>

          {/* File list */}
          {uploadedFileNames.length > 0 && (
            <div className="space-y-1 pt-1">
              {uploadedFileNames.map((name) => (
                <div
                  key={name}
                  className="flex items-center justify-between rounded-lg border bg-muted/30 px-3 py-1.5 text-sm"
                >
                  <span className="truncate font-medium">{name}</span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => removeFile(name)}
                    disabled={isBusy}
                    className="shrink-0"
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ─── Job Description ─────────────────────────────── */}
        <div className="space-y-2">
          <Label htmlFor="job-description">Job description</Label>
          <Textarea
            id="job-description"
            value={jobDescription}
            onChange={(event) => setJobDescription(event.target.value)}
            placeholder="Paste the role description and requirements here..."
            className="min-h-44"
            disabled={isBusy}
          />
        </div>

        {/* ─── Advanced Options ─────────────────────────────── */}
        <div className="space-y-3 rounded-xl border p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium">Advanced options</p>
              <p className="text-xs text-muted-foreground">
                Optional: select model, bring your own API key, or fine-tune generation behavior.
              </p>
            </div>
            <Button
              variant="outline"
              type="button"
              onClick={() => setShowAdvanced((prev) => !prev)}
              disabled={isBusy}
            >
              {showAdvanced ? "Hide" : "Show"}
            </Button>
          </div>

          {showAdvanced && (
            <div className="space-y-4">
              {/* ─── Model Selector ─────────────────────────── */}
              {providerNames.length > 0 && (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Provider</Label>
                    <Select
                      value={selectedProvider}
                      onValueChange={(value) => {
                        if (value) {
                          setSelectedProvider(value);
                          // Reset model selection when provider changes
                          setSelectedModel("");
                        }
                      }}
                      disabled={isBusy}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select provider" />
                      </SelectTrigger>
                      <SelectContent>
                        {providerNames.map((p) => (
                          <SelectItem key={p} value={p}>
                            {p === "google" ? "Google (Gemini)" : p === "openai" ? "OpenAI" : p === "anthropic" ? "Anthropic" : p}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Model</Label>
                    <Select
                      value={selectedModel ? selectedModel.split(":").pop() ?? "" : ""}
                      onValueChange={(value) => {
                        if (value) {
                          setSelectedModel(`${selectedProvider}:${value}`);
                        }
                      }}
                      disabled={isBusy || !selectedProvider}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder={defaultModel ? `Default: ${defaultModel.split(":").pop()}` : "Select model"} />
                      </SelectTrigger>
                      <SelectContent>
                        {modelsForProvider.map((m) => (
                          <SelectItem key={m} value={m}>
                            {m}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}

              {/* ─── API Key ────────────────────────────────── */}
              <div className="space-y-2">
                <Label htmlFor="api-key">API key</Label>
                <div className="relative">
                  <Input
                    id="api-key"
                    value={apiKey}
                    type={showApiKey ? "text" : "password"}
                    onChange={(event) => setApiKey(event.target.value)}
                    placeholder="Leave empty to use server default"
                    className="pr-10"
                    disabled={isBusy}
                  />
                  <Button
                    type="button"
                    size="icon-sm"
                    variant="ghost"
                    className="absolute top-0 right-0"
                    onClick={() => setShowApiKey((prev) => !prev)}
                    disabled={isBusy}
                  >
                    {showApiKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </Button>
                </div>
              </div>

              {/* ─── Additional Instructions ────────────────── */}
              <div className="space-y-2">
                <Label htmlFor="instructions">Additional instructions</Label>
                <Textarea
                  id="instructions"
                  value={userInstructions}
                  onChange={(event) => setUserInstructions(event.target.value)}
                  className="min-h-24"
                  placeholder="Example: Prioritize achievements with measurable impact and keep tone concise."
                  disabled={isBusy}
                />
              </div>

              {/* ─── Review Committee ───────────────────────── */}
              <div className="space-y-3 rounded-lg border p-3">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="review-mode" className="text-sm font-medium">Review committee</Label>
                    <p className="text-xs text-muted-foreground">
                      Run parallel HR, Technical, and ATS reviewers on the generated CV, then synthesize feedback into a refined version.
                    </p>
                  </div>
                  <Switch
                    id="review-mode"
                    checked={reviewMode}
                    onCheckedChange={setReviewMode}
                    disabled={isBusy}
                  />
                </div>

                {reviewMode && providerNames.length > 0 && (
                  <div className="grid gap-4 pt-2 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Review provider</Label>
                      <Select
                        value={reviewProvider}
                        onValueChange={(value) => {
                          if (value) {
                            setReviewProvider(value);
                            setReviewModel("");
                          }
                        }}
                        disabled={isBusy}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select provider" />
                        </SelectTrigger>
                        <SelectContent>
                          {providerNames.map((p) => (
                            <SelectItem key={p} value={p}>
                              {p === "google" ? "Google (Gemini)" : p === "openai" ? "OpenAI" : p === "anthropic" ? "Anthropic" : p}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label>Review model</Label>
                      <Select
                        value={reviewModel ? reviewModel.split(":").pop() ?? "" : ""}
                        onValueChange={(value) => {
                          if (value) {
                            setReviewModel(`${reviewProvider}:${value}`);
                          }
                        }}
                        disabled={isBusy || !reviewProvider}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder={defaultReviewModel ? `Default: ${defaultReviewModel.split(":").pop()}` : "Select model"} />
                        </SelectTrigger>
                        <SelectContent>
                          {reviewModelsForProvider.map((m) => (
                            <SelectItem key={m} value={m}>
                              {m}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ─── Generate Button ─────────────────────────────── */}
        <Button onClick={onGenerate} disabled={isBusy} className="w-full sm:w-auto" size="lg">
          {isParsing ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Parsing documents...
            </>
          ) : isGenerating ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Generating CV...
            </>
          ) : (
            "Generate CV"
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
