import { create } from "zustand";
import type {
  CV,
  ExperienceEntry,
  EducationEntry,
  OneLineEntry,
  PersonalProjectEntry,
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
  cvData: null as CV | null,
  atsIssues: [] as string[],
  hallucinationWarnings: [] as string[],
  template: "engineering",
  customStyles: {} as Record<string, string>,
  previewHtml: "",
  isParsing: false,
  isGenerating: false,
  isLoadingPreview: false,
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

  reset: () => set(initialState),
}));
