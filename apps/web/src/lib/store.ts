import { create } from "zustand";
import type {
  CV,
  ExperienceEntry,
  EducationEntry,
  OneLineEntry,
  PersonalProjectEntry,
  ReviewMemo,
  ChatMessage,
  ReviewApprovalPayload,
} from "@/lib/types";

// Re-export types from shared definitions for convenience
export type { CV, ExperienceEntry, EducationEntry, OneLineEntry, PersonalProjectEntry };

export type AppStep = "upload" | "edit";

interface AppState {
  // ─── Navigation ──────────────────────────────────
  step: AppStep;
  setStep: (step: AppStep) => void;

  // ─── Upload inputs ──────────────────────────────
  resumeText: string;
  setResumeText: (text: string) => void;

  jobDescription: string;
  setJobDescription: (text: string) => void;

  userInstructions: string;
  setUserInstructions: (text: string) => void;

  apiKey: string;
  setApiKey: (key: string) => void;

  uploadedFileNames: string[];
  setUploadedFileNames: (names: string[]) => void;
  addUploadedFileName: (name: string) => void;
  removeUploadedFileName: (name: string) => void;

  // ─── Model selection ───────────────────────────
  selectedModel: string;
  setSelectedModel: (model: string) => void;

  // ─── Review committee ──────────────────────────
  reviewMode: boolean;
  setReviewMode: (enabled: boolean) => void;

  reviewModel: string;
  setReviewModel: (model: string) => void;

  // ─── Generated CV ───────────────────────────────
  cvData: CV | null;
  setCvData: (data: CV | null) => void;

  atsIssues: string[];
  setAtsIssues: (issues: string[]) => void;

  hallucinationWarnings: string[];
  setHallucinationWarnings: (warnings: string[]) => void;

  // ─── Template & Styling ─────────────────────────
  template: string;
  setTemplate: (template: string) => void;

  customStyles: Record<string, string>;
  setCustomStyles: (styles: Record<string, string>) => void;
  updateCustomStyle: (key: string, value: string) => void;

  // ─── Preview ────────────────────────────────────
  previewHtml: string;
  setPreviewHtml: (html: string) => void;

  // ─── Loading states ─────────────────────────────
  isParsing: boolean;
  setIsParsing: (v: boolean) => void;

  isGenerating: boolean;
  setIsGenerating: (v: boolean) => void;

  isLoadingPreview: boolean;
  setIsLoadingPreview: (v: boolean) => void;

  // ─── Streaming state ────────────────────────────
  generationTransport: "blocking" | "streaming";
  setGenerationTransport: (transport: "blocking" | "streaming") => void;

  activeThreadId: string | null;
  setActiveThreadId: (id: string | null) => void;

  runStatus: "idle" | "running" | "completed" | "failed";
  setRunStatus: (status: "idle" | "running" | "completed" | "failed") => void;

  activeStep: string | null;
  setActiveStep: (step: string | null) => void;

  completedSteps: string[];
  setCompletedSteps: (steps: string[]) => void;
  addCompletedStep: (step: string) => void;
  clearCompletedSteps: () => void;

  liveReviewMemos: ReviewMemo[];
  setLiveReviewMemos: (memos: ReviewMemo[]) => void;
  addLiveReviewMemo: (memo: ReviewMemo) => void;
  clearLiveReviewMemos: () => void;

  generationError: string | null;
  setGenerationError: (error: string | null) => void;

  // ─── Chat state ──────────────────────────────────
  uiMode: "assistant" | "quick";
  setUiMode: (mode: "assistant" | "quick") => void;

  chatMessages: ChatMessage[];
  setChatMessages: (messages: ChatMessage[]) => void;
  addChatMessage: (message: ChatMessage) => void;
  clearChatMessages: () => void;

  chatPhase: "intake" | "generation" | "refinement";
  setChatPhase: (phase: "intake" | "generation" | "refinement") => void;

  chatInput: string;
  setChatInput: (input: string) => void;

  artifactTab: "cv" | "preview" | "reviews";
  setArtifactTab: (tab: "cv" | "preview" | "reviews") => void;

  assistantStatus: "idle" | "thinking" | "streaming" | "awaiting_input";
  setAssistantStatus: (status: "idle" | "thinking" | "streaming" | "awaiting_input") => void;

  intakeReady: boolean;
  setIntakeReady: (ready: boolean) => void;

  // ─── Review approval flow ───────────────────────
  pendingReviewApproval: ReviewApprovalPayload | null;
  setPendingReviewApproval: (payload: ReviewApprovalPayload | null) => void;

  reviewDecisions: Record<string, boolean>;
  setReviewDecision: (itemKey: string, accepted: boolean) => void;
  clearReviewDecisions: () => void;

  isAwaitingReviewApproval: boolean;
  setIsAwaitingReviewApproval: (awaiting: boolean) => void;

  // ─── Reset ──────────────────────────────────────
  reset: () => void;
}

const initialState = {
  step: "upload" as AppStep,
  resumeText: "",
  jobDescription: "",
  userInstructions: "",
  apiKey: "",
  uploadedFileNames: [] as string[],
  selectedModel: "",
  reviewMode: false,
  reviewModel: "",
  cvData: null as CV | null,
  atsIssues: [] as string[],
  hallucinationWarnings: [] as string[],
  template: "engineering",
  customStyles: {} as Record<string, string>,
  previewHtml: "",
  isParsing: false,
  isGenerating: false,
  isLoadingPreview: false,
  generationTransport: "blocking" as const,
  activeThreadId: null as string | null,
  runStatus: "idle" as const,
  activeStep: null as string | null,
  completedSteps: [] as string[],
  liveReviewMemos: [] as ReviewMemo[],
  generationError: null as string | null,
  uiMode: "quick" as const,
  chatMessages: [] as ChatMessage[],
  chatPhase: "intake" as const,
  chatInput: "",
  artifactTab: "cv" as const,
  assistantStatus: "idle" as const,
  intakeReady: false,
  pendingReviewApproval: null as ReviewApprovalPayload | null,
  reviewDecisions: {} as Record<string, boolean>,
  isAwaitingReviewApproval: false,
};

export const useAppStore = create<AppState>()((set) => ({
  ...initialState,

  setStep: (step) => set({ step }),

  setResumeText: (resumeText) => set({ resumeText }),
  setJobDescription: (jobDescription) => set({ jobDescription }),
  setUserInstructions: (userInstructions) => set({ userInstructions }),
  setApiKey: (apiKey) => set({ apiKey }),
  setUploadedFileNames: (uploadedFileNames) => set({ uploadedFileNames }),
  addUploadedFileName: (name) =>
    set((state) => ({
      uploadedFileNames: [...state.uploadedFileNames, name],
    })),
  removeUploadedFileName: (name) =>
    set((state) => ({
      uploadedFileNames: state.uploadedFileNames.filter((n) => n !== name),
    })),

  setSelectedModel: (selectedModel) => set({ selectedModel }),

  setReviewMode: (reviewMode) => set({ reviewMode }),
  setReviewModel: (reviewModel) => set({ reviewModel }),

  setCvData: (cvData) => set({ cvData }),
  setAtsIssues: (atsIssues) => set({ atsIssues }),
  setHallucinationWarnings: (hallucinationWarnings) =>
    set({ hallucinationWarnings }),

  setTemplate: (template) => set({ template }),
  setCustomStyles: (customStyles) => set({ customStyles }),
  updateCustomStyle: (key, value) =>
    set((state) => ({
      customStyles: { ...state.customStyles, [key]: value },
    })),

  setPreviewHtml: (previewHtml) => set({ previewHtml }),

  setIsParsing: (isParsing) => set({ isParsing }),
  setIsGenerating: (isGenerating) => set({ isGenerating }),
  setIsLoadingPreview: (isLoadingPreview) => set({ isLoadingPreview }),

  setGenerationTransport: (generationTransport) => set({ generationTransport }),
  setActiveThreadId: (activeThreadId) => set({ activeThreadId }),
  setRunStatus: (runStatus) => set({ runStatus }),
  setActiveStep: (activeStep) => set({ activeStep }),
  setCompletedSteps: (completedSteps) => set({ completedSteps }),
  addCompletedStep: (step) =>
    set((state) => ({
      completedSteps: [...state.completedSteps, step],
    })),
  clearCompletedSteps: () => set({ completedSteps: [] }),
  setLiveReviewMemos: (liveReviewMemos) => set({ liveReviewMemos }),
  addLiveReviewMemo: (memo) =>
    set((state) => ({
      liveReviewMemos: [...state.liveReviewMemos, memo],
    })),
  clearLiveReviewMemos: () => set({ liveReviewMemos: [] }),
  setGenerationError: (generationError) => set({ generationError }),

  setUiMode: (uiMode) => set({ uiMode }),
  setChatMessages: (chatMessages) => set({ chatMessages }),
  addChatMessage: (message) =>
    set((state) => ({
      chatMessages: [...state.chatMessages, message],
    })),
  clearChatMessages: () => set({ chatMessages: [] }),
  setChatPhase: (chatPhase) => set({ chatPhase }),
  setChatInput: (chatInput) => set({ chatInput }),
  setArtifactTab: (artifactTab) => set({ artifactTab }),
  setAssistantStatus: (assistantStatus) => set({ assistantStatus }),
  setIntakeReady: (intakeReady) => set({ intakeReady }),

  setPendingReviewApproval: (pendingReviewApproval) =>
    set({ pendingReviewApproval }),
  setReviewDecision: (itemKey, accepted) =>
    set((state) => ({
      reviewDecisions: { ...state.reviewDecisions, [itemKey]: accepted },
    })),
  clearReviewDecisions: () => set({ reviewDecisions: {} }),
  setIsAwaitingReviewApproval: (isAwaitingReviewApproval) =>
    set({ isAwaitingReviewApproval }),

  reset: () => set(initialState),
}));
