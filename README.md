# career-flow

Memory-backed career knowledge plugin for Claude Code / Cowork, Codex, and ChatGPT Work.

Your career data lives in a **separate private repo** (scaffolded by the `bootstrap` skill),
never in this plugin repo. See `docs/superpowers/specs/2026-08-08-career-flow-plugin-design.md`
for the full design and `docs/schema.md` for the entity schema.

## Install (Claude Code)

    claude plugin marketplace add /Users/bornabarahimi/Projects/career-flow
    claude plugin install career-flow@career-flow-marketplace

## Install (OpenAI Codex CLI)

Codex supports the same Agent Skills format (SKILL.md). Symlink the skills into
Codex's personal skills directory so they stay in sync with this repo:

    mkdir -p ~/.codex/skills
    ln -s /Users/bornabarahimi/Projects/career-flow/skills/bootstrap ~/.codex/skills/career-bootstrap
    ln -s /Users/bornabarahimi/Projects/career-flow/skills/capture   ~/.codex/skills/career-capture

Skills load at Codex startup and activate automatically when your request matches
their description (e.g., "set up my career knowledge base", "log a new project").

Two Codex-specific notes:

- `${CLAUDE_PLUGIN_ROOT}` in the skill instructions is a Claude Code variable.
  In Codex it means this plugin repo's path — recorded as `plugin.local_path`
  in your data repo's `config.yaml` (the data repo's `AGENTS.md` says this too).
- Always run Codex from your career-data repo so its `AGENTS.md` conventions load.

## First run

Invoke the `career-flow:bootstrap` skill — it scaffolds your private career-data repo
and imports your existing resume.

## Development

    uv run --with pyyaml --with pytest -- pytest tests/ -v
