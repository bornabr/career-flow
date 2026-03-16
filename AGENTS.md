# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-15
**Commit:** 26f4515
**Branch:** dev

## OVERVIEW

AI-powered resume tailoring app. Upload resume + job description → AI generates a tailored CV → PDF export. Monorepo: Next.js 16 frontend (React 19, Tailwind 4) + FastAPI backend (Pydantic AI, LiteLLM).

## STRUCTURE

```
career-flow/
├── apps/web/          # Next.js App Router frontend (shadcn/ui, Zustand)
├── backend/           # FastAPI + AI agents (NOT in apps/, NOT managed by Turbo)
├── packages/shared/   # Shared TS types (CV schema) — currently minimal
├── turbo.json         # Turbo orchestrates JS/TS only (build, lint, type-check)
├── pnpm-workspace.yaml
└── .env               # Single .env at root, read by both frontend and backend
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `backend/app/api/` | FastAPI router, register in `main.py` |
| Add AI agent | `backend/app/agents/` | Uses pydantic-ai structured output |
| Modify CV schema | `backend/app/schemas/cv.py` + `packages/shared/src/cv.ts` | Keep in sync manually |
| Add UI component | `apps/web/src/components/` | Custom components here; `ui/` is shadcn |
| Add shadcn primitive | `apps/web/src/components/ui/` | Use `npx shadcn@latest add <component>` |
| Modify state | `apps/web/src/lib/store.ts` | Zustand flat store, no slices |
| Add CV template | `backend/app/templates/` | Jinja2 HTML, register in `services/pdf.py` |
| API client changes | `apps/web/src/lib/api.ts` | All backend calls centralized here |
| LLM provider support | `backend/app/services/llm.py` | Provider map pattern |
| Environment vars | `.env` at repo root | Backend reads via pydantic-settings, frontend via NEXT_PUBLIC_ |

## CONVENTIONS

- **Monorepo split**: pnpm + Turbo for JS/TS, Poetry for Python. No Turbo tasks for backend.
- **Dev command**: `pnpm dev:backend` runs both frontend and backend concurrently.
- **Backend runs from `backend/`**: `poetry run uvicorn app.main:app --reload --port 8000`
- **No linter/formatter configs**: No ESLint, Prettier, or Ruff configured.
- **No CI/CD**: No GitHub Actions, Dockerfiles, or deployment configs.
- **No tests**: No test framework configured for either frontend or backend.
- **Model format**: LLM models use `provider:model_id` string format (e.g., `google:gemini-2.5-pro`).
- **Settings**: Backend uses pydantic-settings with `@lru_cache` singleton. `.env` lookup chain: `backend/.env` → repo root `.env`.

## ANTI-PATTERNS (THIS PROJECT)

- **DO NOT** add information not in source documents when modifying AI prompts — anti-hallucination is the core safety constraint.
- **DO NOT** add Turbo tasks for the Python backend — it's managed separately via Poetry.
- **DO NOT** put shared Python/TS logic in `packages/shared/` — it's TS-only. Python has its own schemas in `backend/app/schemas/`.

## COMMANDS

```bash
# Development (both services)
pnpm dev:backend          # Starts Next.js + FastAPI concurrently

# Frontend only
pnpm dev:web              # Next.js dev server (port 3000)

# Backend only (from backend/)
poetry run uvicorn app.main:app --reload --port 8000

# Build
pnpm build                # Turbo builds all JS/TS packages
pnpm build:web            # Next.js production build only

# Type checking
pnpm type-check           # Turbo type-check across JS/TS

# Backend deps (from backend/)
poetry install            # Install Python dependencies
playwright install chromium  # Required for PDF generation
```

## NOTES

- Playwright (headless Chromium) is used server-side for PDF generation, NOT for testing. Browser singleton managed via lifespan.
- `packages/shared/` exports CV types but workspace is underutilized — `dist/` is committed.
- Tailwind 4 (not stable v3) — CSS config via PostCSS, no `tailwind.config.js`.
- Frontend is essentially a single-page app with two steps: upload → edit. No routing beyond `page.tsx`.
- Backend supports multi-provider LLM: Google, OpenAI, Anthropic via pydantic-ai + litellm.
- PDF templates use Jinja2 with custom `|md` filter for inline markdown (bold/italic).
