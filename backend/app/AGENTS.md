# BACKEND APP

FastAPI application with AI-powered CV generation pipeline.

## STRUCTURE

```
app/
├── agents/       # AI agents (tailor, validator, cover letter) — see agents/AGENTS.md
├── api/          # FastAPI route handlers (parse, generate, pdf, cover_letter)
├── schemas/      # Pydantic models (CV schema is the core data model)
├── services/     # Business logic (LLM provider factory, document parser, PDF renderer)
├── templates/    # Jinja2 HTML templates for PDF rendering (engineering, classic, modern)
├── utils/        # Helpers (ATS text cleaning)
├── config.py     # Settings singleton via pydantic-settings + @lru_cache
└── main.py       # App factory: FastAPI instance, CORS, router registration, lifespan
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new API route | `api/` + register in `main.py` via `app.include_router()` |
| Add LLM provider | `services/llm.py` | Add to `_PROVIDER_MAP` dict |
| Add PDF template | `templates/` + register in `services/pdf.py` `AVAILABLE_TEMPLATES` |
| Change CV schema | `schemas/cv.py` | Must also update `packages/shared/src/cv.ts` |
| Add new agent | `agents/` | Pattern: pydantic-ai `Agent` with `output_type`, model overridden per-request |
| Change env vars | `config.py` `Settings` class | Reads `.env` from `backend/` then repo root |
| Add models | `config.py` `AVAILABLE_MODELS` dict | Format: `provider: [model_ids]` |

## CONVENTIONS

- **App factory pattern**: `create_app()` in `main.py` returns configured FastAPI instance.
- **Agent pattern**: Agents are created once with `"test"` as placeholder model, real model passed via `run(model=...)` per request.
- **API key resolution**: Request body `api_key` → provider-specific env var → generic `API_KEY` env var.
- **PDF pipeline**: Jinja2 HTML → Playwright headless Chromium → PDF bytes. Browser is a singleton, cleaned up via lifespan.
- **Jinja2 `|md` filter**: Custom filter in `services/pdf.py` converts `**bold**` and `*italic*` to HTML tags in templates.

## ANTI-PATTERNS

- **DO NOT** import from `apps/web/` or `packages/shared/` — Python has its own schemas.
- **DO NOT** add Turbo/pnpm tasks for this directory — use Poetry only.
- **DO NOT** use `litellm` directly for agent calls — use `services/llm.py` factory which wraps pydantic-ai providers.
