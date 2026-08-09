# career-flow

Memory-backed career knowledge plugin for Claude Code / Cowork, Codex, and ChatGPT Work.

Your career data lives in a **separate private repo** (scaffolded by the `bootstrap` skill),
never in this plugin repo. See `docs/superpowers/specs/2026-08-08-career-flow-plugin-design.md`
for the full design and `docs/schema.md` for the entity schema.

## Install (Claude Code)

    claude plugin marketplace add /Users/bornabarahimi/Projects/career-flow
    claude plugin install career-flow@career-flow-marketplace

## First run

Invoke the `career-flow:bootstrap` skill — it scaffolds your private career-data repo
and imports your existing resume.

## Development

    uv run --with pyyaml --with pytest -- pytest tests/ -v
