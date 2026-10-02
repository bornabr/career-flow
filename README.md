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
`/career-flow:interview-prep`, `/career-flow:outreach`,
`/career-flow:checkin`, and `/career-flow:maintain`.

### OpenAI Codex CLI

    codex plugin marketplace add .
    codex plugin add career-flow@career-flow-marketplace

Start a new Codex session after installation. Invoke skills as
`$career-flow:bootstrap`, `$career-flow:capture`, `$career-flow:resume`,
`$career-flow:cover-letter`, `$career-flow:interview-prep`,
`$career-flow:outreach`, `$career-flow:checkin`, and `$career-flow:maintain`,
or describe the matching task and let Codex activate the
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

## Phase 3 maintenance

`checkin` guides a periodic review of work since the last approved check-in and
triages candidates in `data/inbox.md`. `maintain` reports stale facts, missing metrics,
similar entries, broken links, and index drift before proposing any changes. Approved
check-ins are dated files under `data/checkins/`. The read-only status helper is:

    uv run scripts/phase3_status.py <data-repo> --json

Passive capture is **off by default**. To opt in, set
`capture.passive.enabled: true` in the private data repo and explicitly allowlist
source repositories in `github_repos` and/or absolute directories in
`session_projects`. The GitHub source scans merged PR titles, dates, and URLs only when
you run `python3 scripts/passive_capture.py github <data-repo>`; the Claude Code
`SessionEnd` hook scans only allowlisted workspaces and writes no transcript text.
Both sources append review candidates to `data/inbox.md`, never career entities;
`data/passive-state.json` stores deduplication checkpoints after an enabled scan.
They do not publish output or commit on their own. GitHub scanning uses the
authenticated `gh` CLI; the session hook uses only local transcript data. Keep
passive capture disabled for confidential work unless you deliberately allowlist
its source.

Draft-only or test outreach no longer creates an application entity. An application
log begins only when the user confirms an actual submission.

## Development

    uv run --with pyyaml --with pytest -- pytest tests/ -v
