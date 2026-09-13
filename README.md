# career-flow

Memory-backed career knowledge plugin for Claude Code / Cowork, Codex, and ChatGPT Work.

Your career data lives in a **separate private repo** (scaffolded by the `bootstrap` skill),
never in this plugin repo. See `docs/superpowers/specs/2026-08-08-career-flow-plugin-design.md`
for the full design and `docs/schema.md` for the entity schema.

## Install

Clone this repository, then run the commands for your agent from the repository root.

### Claude Code

    claude plugin marketplace add .
    claude plugin install career-flow@career-flow-marketplace

Invoke skills as `/career-flow:bootstrap` and `/career-flow:capture`.

### OpenAI Codex CLI

    codex plugin marketplace add .
    codex plugin add career-flow@career-flow-marketplace

Start a new Codex session after installation. Invoke skills as
`$career-flow:bootstrap` and `$career-flow:capture`, or describe the matching task
and let Codex activate the skill automatically.

## First run

Invoke the `career-flow:bootstrap` skill using the syntax for your agent above. It
scaffolds your private career-data repo and imports your existing resume.

## Development

    uv run --with pyyaml --with pytest -- pytest tests/ -v
