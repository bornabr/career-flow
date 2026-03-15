const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Parse ───────────────────────────────────────────────

export interface ParseFileResult {
  text: string;
  filename: string;
  content_type: string;
}

export interface ParseResponse {
  files: ParseFileResult[];
  combined_text: string;
}

export async function parseDocuments(files: File[]): Promise<ParseResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }

  const res = await fetch(`${API_BASE}/api/parse`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to parse documents");
  }

  return res.json();
}

// ─── Generate ────────────────────────────────────────────

export interface GenerateRequest {
  resume_text: string;
  job_description: string;
  user_instructions?: string | null;
  api_key?: string | null;
  model_name?: string | null;
}

export interface GenerateResponse {
  cv_data: Record<string, unknown>;
  ats_issues: string[];
  hallucination_warnings: string[];
}

export async function generateCV(body: GenerateRequest): Promise<GenerateResponse> {
  const res = await fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to generate CV");
  }

  return res.json();
}

// ─── Models ──────────────────────────────────────────────

export interface ModelsResponse {
  providers: Record<string, string[]>;
  available_providers: string[];
  default: string;
}

export async function getModels(): Promise<ModelsResponse> {
  const res = await fetch(`${API_BASE}/api/models`);

  if (!res.ok) {
    throw new Error("Failed to fetch models");
  }

  return res.json();
}

// ─── PDF ─────────────────────────────────────────────────

export interface PDFRequest {
  cv_data: Record<string, unknown>;
  template?: string;
  custom_styles?: Record<string, string> | null;
}

export async function generatePDF(body: PDFRequest): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to generate PDF");
  }

  return res.blob();
}

export async function getPreviewHTML(body: PDFRequest): Promise<string> {
  const res = await fetch(`${API_BASE}/api/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to get preview");
  }

  return res.text();
}

export interface TemplatesResponse {
  templates: string[];
}

export async function getTemplates(): Promise<TemplatesResponse> {
  const res = await fetch(`${API_BASE}/api/templates`);

  if (!res.ok) {
    throw new Error("Failed to fetch templates");
  }

  return res.json();
}

// ─── Cover Letter ────────────────────────────────────────

export interface CoverLetterRequest {
  cv_data: Record<string, unknown>;
  job_description: string;
  company_name?: string | null;
  user_instructions?: string | null;
  api_key?: string | null;
}

export interface CoverLetterResponse {
  greeting: string;
  opening: string;
  body: string[];
  closing: string;
  sign_off: string;
  full_text: string;
}

export async function generateCoverLetter(
  body: CoverLetterRequest
): Promise<CoverLetterResponse> {
  const res = await fetch(`${API_BASE}/api/cover-letter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to generate cover letter");
  }

  return res.json();
}
