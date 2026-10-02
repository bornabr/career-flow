---
name: checkin
description: Use for a periodic career check-in that reviews work since the last check-in, triages accomplishment candidates, and updates the private career-data repo with user-confirmed facts.
---

# Career check-in

Resolve `<plugin-root>` from this file's installed path (two directories above) or
the expanded `${CLAUDE_PLUGIN_ROOT}` in Claude Code. Locate the private data repo
from the current directory (`config.yaml` and `data/`) or the `data_repo:` pointer
in `~/.config/career-flow/config`. If neither exists, suggest bootstrap and stop.

Before writing, pull the data repo, inspect its worktree without overwriting other
changes, and read `config.yaml`, `data/INDEX.md`, and `data/inbox.md`. Run
`<plugin-root>/scripts/phase3_status.py <data-repo> --json` to see the last check-in,
configured interval, inbox count, stale entries, and validation problems. A due
date is a prompt to ask, not permission to run or commit automatically.
If `capture.passive.enabled` is true, `sources` includes `github`, and
`github_repos` is explicitly allowlisted, run
`<plugin-root>/scripts/passive_capture.py github <data-repo>` before
triaging the inbox. If `gh` is unavailable or the scan fails, report that and
continue the manual check-in; never widen the repository scope to make it work.

Ask what shipped, changed, or was learned since the last check-in (or a time window
the user chooses). Review inbox candidates one by one; a GitHub PR or Claude session
signal is only a lead, not proof of an accomplishment. Ask what the user owned,
when it happened, how it was evaluated, what changed, and what may be shared. Reuse
existing experience/project/skill/story entities where possible. Follow the capture
skill's evidence, raw-note, reviewer, and cross-link rules for any entity changes.
Never promote or discard an inbox candidate without the user's decision; preserve
untouched items.

After the user approves the proposed entries and inbox decisions, create
`data/checkins/YYYY-MM-DD.md` with the period covered, entity ids changed, inbox
decisions, and unresolved questions. This date is the cadence marker; do not create
it for a status-only question or an abandoned interview. Do a brief staleness review
from the status report, asking about only the few entries relevant to this check-in.
Run `<plugin-root>/scripts/validate.py <data-repo>`, review the diff, then commit and
push only the approved private changes. Do not publish career details elsewhere.
