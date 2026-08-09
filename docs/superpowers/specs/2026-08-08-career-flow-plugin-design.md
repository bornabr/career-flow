# Career-Flow: Memory-Backed Career Knowledge Plugin — Design

## Context

Borna wants a system that tracks and maintains career knowledge — work experiences, projects, skills, publications, education, STAR stories — persisted between sessions in file-backed memory, with career-specific automatic memory management. The knowledge base feeds concrete outputs: tailored resumes/CVs, interview prep packs, cover letters and misc blurbs, and a personal web page.

The previous incarnation of this repo was a heavyweight FastAPI + LangGraph application; it was deliberately reset. The new approach is an **agent plugin**: the agent harness provides the runtime, the plugin provides structured flows and a plain-file knowledge base.

Decisions made during brainstorming:
- **Audience:** personal first, shareable later → plugin code and personal data live in **separate repos** from day one, so the plugin can be published without ever touching personal data.
- **Portability:** full flows in Claude Code, Claude Cowork, Codex, and ChatGPT Work.
- **Architecture:** plain files + Agent Skills as the engine; git/GitHub as sync; MCP server deferred to a later phase as the uniform ChatGPT bridge.
- **Data home:** a **separate private GitHub-synced repo** (the "data repo", e.g., `career-data`), distinct from this plugin repo. This repo (`career-flow`) holds only the shareable plugin code. The bootstrap flow scaffolds the data repo.
- **Capture modes:** bootstrap import, guided capture, periodic check-ins, passive capture — each individually toggleable in user config.
- **Outputs (all wanted, phased):** tailored resume (Typst → PDF), interview prep pack, cover letters/misc, personal web page (GitHub Pages, later phase).
- **Check-ins:** manually triggered command, no scheduling infra.

## Repo Layout

Two repos with a clean boundary: the **plugin repo** (this one, shareable) and the **data repo** (private, scaffolded by the bootstrap flow). Agents do career work with the data repo as their working directory; the plugin is installed globally in each tool.

**Plugin repo — `career-flow` (this repo):**

```
career-flow/
├── .claude-plugin/plugin.json   # Claude Code plugin manifest
├── skills/
│   ├── bootstrap/SKILL.md       # scaffold the data repo + one-time import: resume/LinkedIn/etc. + gap interview
│   ├── capture/SKILL.md         # guided capture: project / accomplishment / publication / role change
│   ├── checkin/SKILL.md         # periodic career journal (covers gap since last check-in)
│   ├── maintain/SKILL.md        # memory management: staleness review, dedup/merge, link repair, index rebuild
│   ├── resume/SKILL.md          # job posting → tailored Typst resume → PDF
│   ├── interview-prep/SKILL.md  # posting/company → prep pack (questions ↔ STAR stories, gap analysis)
│   ├── cover-letter/SKILL.md    # cover letters, LinkedIn summaries, bio blurbs
│   └── webpage/SKILL.md         # static portfolio site from public-visibility entries (later phase)
├── hooks/                       # optional passive-capture hook (opt-in via config)
├── templates/                   # data-repo scaffold (AGENTS.md, config.yaml, entry templates), Typst resume template, prep-pack template
├── scripts/
│   └── validate                 # schema check, link check, INDEX rebuild (plain script, any agent can run)
└── docs/superpowers/specs/      # design docs (this spec)
```

**Data repo — e.g., `career-data` (private, created by bootstrap from the scaffold templates):**

```
career-data/
├── AGENTS.md                    # universal entry point: conventions ANY agent must follow; points at plugin flows
├── CLAUDE.md                    # thin pointer to AGENTS.md
├── config.yaml                  # user config: capture toggles, cadences, staleness_months, output prefs, plugin location
├── .github/workflows/validate.yml  # CI: runs the validate script on every push
├── data/
│   ├── profile.md               # identity, contact, links, headline, preferences
│   ├── experiences/<slug>.md    # jobs/roles
│   ├── projects/<slug>.md
│   ├── skills/<slug>.md
│   ├── education/<slug>.md
│   ├── publications/<slug>.md
│   ├── stories/<slug>.md        # STAR stories, linked to experiences/projects
│   ├── inbox.md                 # staging area for passive-capture candidates
│   └── INDEX.md                 # generated compact index — the recall layer any agent loads first
└── outputs/                     # generated artifacts: resumes/, prep-packs/, letters/ (dated, per-company)
```

How the two find each other: skills resolve the data repo from the current working directory (presence of `config.yaml` + `data/`), falling back to a `data_repo` path recorded in `~/.config/career-flow/config` by bootstrap. The data repo's `config.yaml` records where the plugin lives for non-Claude tools (Codex/ChatGPT instructions reference it).

## Data Model

Every entity is one Markdown file with YAML frontmatter (portable, diff-able, any agent can edit):

```yaml
---
id: proj-career-flow
type: project                 # experience | project | skill | education | publication | story
title: Career-Flow Plugin
start: 2026-08                # YYYY-MM
end:                          # YYYY-MM; empty = current/ongoing
org: Personal                 # display text only; structural links go under links:
links:
  experience: exp-acme        # cross-links by id
  skills: [skill-python, skill-agent-design]
status: active                # active | completed | archived
visibility: public            # public (webpage-eligible) | private
last_verified: 2026-08-08     # drives staleness review
tags: [ai-agents, plugins]
---
# Narrative
...accomplishments with metrics, context, STAR notes...
```

`INDEX.md` is regenerated by the validate script: one line per entity (id, title, dates, one-line hook) — the MEMORY.md pattern. Any agent in any tool loads `AGENTS.md` + `INDEX.md` and knows what exists without reading everything.

## Automatic Memory Management (career-specific)

1. **Write-time discipline:** every capture flow ends by (a) updating cross-links — a new project adds/updates its skill files, a story links its experience; (b) running the plugin's `scripts/validate` against the data repo, which checks frontmatter schema, broken links, orphan skills, and regenerates INDEX.md. Validation failure blocks flow completion.
2. **CI enforcement:** the data repo's GitHub Action checks out the plugin repo alongside and runs the same validate script on every push — so even edits made from ChatGPT Work (via GitHub connector) or Codex cloud get schema-checked.
3. **Staleness review:** `last_verified` dates; the maintain flow surfaces entries older than `staleness_months` (config) — "is this role still current? are these skills still accurate?"
4. **Consolidation:** the maintain flow detects near-duplicate skills/stories and proposes merges; archived items get compressed, never silently deleted.
5. **Inbox pattern:** passive capture never writes entities directly — it appends candidates to `data/inbox.md`; the next capture/check-in flow triages the inbox. Decouples noticing from committing.

## Capture Flows (each gated by `config.yaml`)

- **bootstrap** — one-time: user provides resume/LinkedIn export/publication list; agent parses into entities, then interviews to fill gaps (metrics, dates, missing stories).
- **capture** — on-demand guided interview: "log a project" → asks impact, metrics, skills used, story-worthy moments; produces resume-ready entries.
- **checkin** — manual command; reads date of last check-in, walks the gap ("what shipped, what did you learn"), triages inbox, ends with a mini staleness pass.
- **passive** (opt-in, default off) — Claude Code SessionEnd/Stop hook that scans the session for career-noteworthy work and appends candidates to `data/inbox.md`.

## Output Flows

- **resume** — input: job posting (text/URL). Selects relevant entries from INDEX + entity files, ranks by relevance to the posting, fills the Typst template, compiles to PDF in `outputs/resumes/<company>-<role>-<date>/`. Keeps the tailoring rationale alongside the PDF.
- **interview-prep** — input: posting + company. Produces a Markdown pack: likely questions mapped to specific STAR stories by id, talking points per relevant experience, gap analysis (posting requirements vs. knowledge base).
- **cover-letter** — small text artifacts (cover letter, LinkedIn about, bios) generated on demand.
- **webpage** (later phase) — static site from `visibility: public` entries → GitHub Pages.

## Cross-Tool Strategy

| Tool | How it works |
|---|---|
| Claude Code / Cowork | Full plugin: skills, optional hook, slash-command entry points |
| Codex CLI | `AGENTS.md` at the data repo root + the same SKILL.md files (Agent Skills format is portable; installed/symlinked into Codex's skills location) |
| ChatGPT Work | Private data repo via GitHub connector; condensed instructions (generated from the plugin's templates into the data repo) pasted as project instructions; writes land as commits/PRs, data-repo CI validates them |
| (Later) | Thin MCP server exposing capture/search/generate tools for a uniform ChatGPT/remote story |

Git is the sync layer: flows `git pull` before writing and commit after; conflicts surface as normal git conflicts.

## Implementation Phases

1. **Foundation** — plugin repo layout, entity schema + data-repo scaffold templates (`AGENTS.md`, `CLAUDE.md`, `config.yaml`, CI workflow), validate script + INDEX generation, **bootstrap** skill (scaffolds the private data repo + GitHub remote, then imports) and **capture** skill. *End state: separate private data repo created and populated from existing resume; new entries capturable.*
2. **Outputs** — **resume** (Typst template + compile), **cover-letter**, **interview-prep** skills.
3. **Maintenance cadence** — **checkin** and **maintain** skills; passive-capture hook (opt-in).
4. **Web page + adapter polish** — **webpage** skill → GitHub Pages; Codex/ChatGPT instruction files tuned by real use.
5. **Later / out of scope for now** — MCP server, marketplace packaging.

Phase 1 is the first implementation plan; each later phase gets its own plan.

## Error Handling

- Validate script failure blocks capture-flow completion (agent must fix or revert).
- Git: pull-before-write; on conflict, stop and surface to user.
- Privacy: data repo private and fully separate from the (eventually public) plugin repo; `visibility` frontmatter gates anything that leaves it (webpage); outputs directory reviewed before sending anywhere.

## Verification

- Run `scripts/validate` against seeded sample data (valid + deliberately broken fixtures).
- End-to-end dry run: bootstrap with the real resume → capture one project → confirm INDEX.md and cross-links correct.
- Compile the Typst template with sample data to PDF.
- CI run on the data repo's GitHub remote passes.
- **User acceptance loop:** after each phase, Borna enters real career info and exercises the flows, outputs, and memory management, giving feedback that drives fixes before the next phase begins.

## Next Steps

Produce the Phase 1 (Foundation) implementation plan via the writing-plans skill; later phases each get their own plan when their turn comes.
