# BACKEND APP

FastAPI application with AI-powered CV generation pipeline. Supports two modes: standard (single-agent) and review committee (multi-agent with parallel reviewers + synthesis).

## STRUCTURE

```
app/
├── agents/       # AI agents (7 agents + 1 orchestrator) — see agents/AGENTS.md
├── api/          # FastAPI route handlers (parse, generate, pdf, cover_letter)
├── schemas/      # Pydantic models (CV schema + review schemas)
├── services/     # Business logic (LLM provider factory, document parser, PDF renderer)
├── templates/    # Jinja2 HTML templates for PDF rendering (engineering, classic, modern)
├── utils/        # Helpers (ATS text cleaning)
├── config.py     # Settings singleton via pydantic-settings + @lru_cache
└── main.py       # App factory: FastAPI instance, CORS, router registration, lifespan
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new API route | `api/` + register in `main.py` via `app.include_router()` | |
| Add LLM provider | `services/llm.py` | Add to `_PROVIDER_MAP` dict |
| Add PDF template | `templates/` + register in `services/pdf.py` `AVAILABLE_TEMPLATES` | |
| Change CV schema | `schemas/cv.py` | Must also update `packages/shared/src/cv.ts` |
| Change review schemas | `schemas/review.py` | ReviewMemo, HallucinationReport, ReviewPanelResult |
| Add new agent | `agents/` | Pattern: pydantic-ai `Agent` with `output_type`, model overridden per-request |
| Add new reviewer | `agents/` | Follow hr_reviewer.py pattern, add to `pipeline.py` gather |
| Change pipeline flow | `agents/pipeline.py` | Orchestrates standard and review pipelines |
| Change env vars | `config.py` `Settings` class | Reads `.env` from `backend/` then repo root |
| Add models | `config.py` `AVAILABLE_MODELS` dict | Format: `provider: [model_ids]` |
| Change review defaults | `config.py` `Settings.default_review_model` | Default model used for reviewer agents |

## CONVENTIONS

- **App factory pattern**: `create_app()` in `main.py` returns configured FastAPI instance.
- **Agent pattern**: Agents are created once with `"test"` as placeholder model, real model passed via `run(model=...)` per request.
- **Pipeline pattern**: `api/generate.py` calls `pipeline.py` functions, never agents directly. `pipeline.py` orchestrates agent calls.
- **Review mode**: Opt-in via `review_mode=true` in the generate request. Uses `review_model` (default: `google:gemini-2.5-flash`) for cost-efficient parallel reviews.
- **API key resolution**: Request body `api_key` → provider-specific env var → generic `API_KEY` env var.
- **PDF pipeline**: Jinja2 HTML → Playwright headless Chromium → PDF bytes. Browser is a singleton, cleaned up via lifespan. Has retry logic (2 retries) and 30s timeout.
- **Jinja2 `|md` filter**: Custom filter in `services/pdf.py` converts `**bold**` and `*italic*` to HTML tags in templates.
- **Validation**: Two layers — deterministic (`validator.py`: fuzzy matching, synonym-aware, numeric claims) and AI-powered (`hallucination_checker.py`: semantic comparison).
- **Parser**: `parse_document()` for single files, `parse_documents()` for multi-doc with source labels. Text normalization applied automatically.

## ANTI-PATTERNS

- **DO NOT** import from `apps/web/` or `packages/shared/` — Python has its own schemas.
- **DO NOT** add Turbo/pnpm tasks for this directory — use Poetry only.
- **DO NOT** use `litellm` directly for agent calls — use `services/llm.py` factory which wraps pydantic-ai providers.
- **DO NOT** call agents directly from API routes — use `agents/pipeline.py` orchestration functions.
- **DO NOT** add information not in source documents when modifying AI prompts — anti-hallucination is the core safety constraint.
