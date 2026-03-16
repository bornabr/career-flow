# WEB APP (FRONTEND)

Next.js 16 App Router single-page application. Two-step flow: Upload → Edit & Preview.

## STRUCTURE

```
src/
├── app/              # Next.js App Router (layout.tsx, page.tsx, globals.css)
├── components/       # Custom app components (upload-step, cv-editor, preview-panel)
│   └── ui/           # shadcn/ui primitives (13 components) — DO NOT edit manually
└── lib/              # Shared logic
    ├── api.ts        # All backend API calls (fetch-based, no axios)
    ├── store.ts      # Zustand flat store — single store, no slices
    ├── types.ts      # CV TypeScript interfaces (mirrors backend Pydantic models)
    └── utils.ts      # Utility functions
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Modify page layout | `src/app/page.tsx` | Entire app is one page with step-based rendering |
| Add custom component | `src/components/` | Three main components: `upload-step`, `cv-editor`, `preview-panel` |
| Add shadcn component | Run `npx shadcn@latest add <name>` | Auto-generates into `src/components/ui/` |
| Add API call | `src/lib/api.ts` | All backend calls centralized here, raw fetch |
| Modify state | `src/lib/store.ts` | Zustand flat store with `useAppStore` hook |
| Change CV types | `src/lib/types.ts` | Must also update `backend/app/schemas/cv.py` |
| Global styles | `src/app/globals.css` | Tailwind 4 via PostCSS |

## CONVENTIONS

- **"use client"** at page level — entire app is client-rendered (SPA behavior).
- **State management**: Single Zustand store (`useAppStore`), flat structure with setter functions. No slices, no middleware.
- **API layer**: All backend calls in `api.ts` using native `fetch`. No axios or react-query.
- **Step navigation**: `step` state ("upload" | "edit") controls which view renders in `page.tsx`.
- **Type definitions**: `lib/types.ts` has local copies of CV interfaces + factory functions (`createEmptyCV`, etc.). Does NOT import from `packages/shared/`.
- **Tailwind 4**: Uses PostCSS config, no `tailwind.config.js`. CSS variables for theming via `globals.css`.
- **shadcn/ui**: All primitives in `components/ui/` — do not hand-edit, add new ones via CLI.

## ANTI-PATTERNS

- **DO NOT** add new pages/routes — this is a single-page app by design.
- **DO NOT** hand-edit files in `components/ui/` — use `npx shadcn@latest add` for new primitives.
- **DO NOT** import directly from `packages/shared/` in components — use `lib/types.ts` local copies.
