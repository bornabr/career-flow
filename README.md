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

Invoke skills as `/career-flow:bootstrap`, `/career-flow:capture`,
`/career-flow:resume`, `/career-flow:cover-letter`,
`/career-flow:interview-prep`, and `/career-flow:outreach`.

### OpenAI Codex CLI

    codex plugin marketplace add .
    codex plugin add career-flow@career-flow-marketplace

Start a new Codex session after installation. Invoke skills as
`$career-flow:bootstrap`, `$career-flow:capture`, `$career-flow:resume`,
`$career-flow:cover-letter`, `$career-flow:interview-prep`, and
`$career-flow:outreach`, or describe the matching task and let Codex activate the
skill automatically.

## First run

Invoke the `career-flow:bootstrap` skill using the syntax for your agent above. It
scaffolds your private career-data repo and imports your existing resume.

## Phase 2 outputs

The output skills write only to the private data repo: resumes in `outputs/resumes/`,
letters in `outputs/letters/`, interview packs in `outputs/prep-packs/`, and
outreach drafts in `outputs/outreach/`. The resume skill supports a general resume
without a job posting, optionally focused on a target role, as well as a resume
tailored to a posting. Resume generation needs `typst` and
Poppler's `pdfinfo`, `pdftotext`, and `pdftoppm` commands. A resume is compiled
from the single-column template, with grouped skills immediately after the summary,
then checked for readable PDF text, section order, and selected publication links.
The skill asks a short setup interview about focus and inclusion before drafting.
Every included experience requires at least two coherent, evidence-backed bullets;
metrics must clearly belong to the work described in that bullet.
Tailored resumes also check supported job-posting terms; general resumes
skip that check because there is no posting. Neither check guarantees an employer's
screening result.

`scripts/due_followups.py <data-repo>` lists active applications with unfinished
follow-ups due today. It does not change data or send messages.

## Development

    uv run --with pyyaml --with pytest -- pytest tests/ -v
