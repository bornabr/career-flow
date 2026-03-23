// CV types — mirrors backend Pydantic models and packages/shared/src/cv.ts

export interface SocialNetwork {
  network: string;
  username: string;
}

export interface ExperienceEntry {
  company: string;
  position: string;
  location?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  highlights: string[];
  summary?: string | null;
}

export interface EducationEntry {
  institution: string;
  area: string;
  degree?: string | null;
  location?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  highlights?: string[] | null;
  summary?: string | null;
}

export interface OneLineEntry {
  label: string;
  details: string;
}

export interface PersonalProjectEntry {
  name: string;
  summary: string;
  highlights?: string[] | null;
  url?: string | null;
}

export interface PublicationsEntry {
  title: string;
  authors: string[];
  doi?: string | null;
  journal: string;
  date?: string | null;
  url: string;
}

export interface Sections {
  Summary: string[];
  Skills: OneLineEntry[];
  Education: EducationEntry[];
  Experience: ExperienceEntry[];
  AdditionalExperience?: ExperienceEntry[] | null;
  Publications?: PublicationsEntry[] | null;
  PersonalProjects?: PersonalProjectEntry[] | null;
}

export interface CV {
  name: string;
  location: string;
  email?: string | null;
  phone?: string | null;
  website?: string | null;
  social_networks?: SocialNetwork[] | null;
  sections: Sections;
}

export interface ReviewMemo {
  reviewer: string;
  score: number;
  summary: string;
  suggestions: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  kind: "text" | "artifact";
  timestamp: Date;
}

export interface InteractiveReviewItem {
  item_key: string;
  recommendation: string;
  rationale: string;
  severity: "critical" | "warning" | "suggestion";
}

export interface InteractiveReviewMemo {
  reviewer_role: "hr" | "technical" | "ats";
  items: InteractiveReviewItem[];
  overall_score: number;
  overall_rationale: string;
}

export interface ReviewApprovalPayload {
  interactive_reviews: InteractiveReviewMemo[];
  hallucination_report: Record<string, unknown> | null;
  consensus_score: number;
}

// ─── Helpers ─────────────────────────────────────

export function createEmptyCV(): CV {
  return {
    name: "",
    location: "",
    email: "",
    phone: "",
    website: "",
    social_networks: [],
    sections: {
      Summary: [""],
      Skills: [{ label: "", details: "" }],
      Education: [
        {
          institution: "",
          area: "",
          degree: "",
          location: "",
          start_date: "",
          end_date: "",
          highlights: [],
        },
      ],
      Experience: [
        {
          company: "",
          position: "",
          location: "",
          start_date: "",
          end_date: "",
          highlights: [""],
        },
      ],
    },
  };
}

export function createEmptyExperience(): ExperienceEntry {
  return {
    company: "",
    position: "",
    location: "",
    start_date: "",
    end_date: "",
    highlights: [""],
    summary: "",
  };
}

export function createEmptyEducation(): EducationEntry {
  return {
    institution: "",
    area: "",
    degree: "",
    location: "",
    start_date: "",
    end_date: "",
    highlights: [],
    summary: "",
  };
}

export function createEmptySkill(): OneLineEntry {
  return { label: "", details: "" };
}

export function createEmptyProject(): PersonalProjectEntry {
  return { name: "", summary: "", highlights: [], url: "" };
}
