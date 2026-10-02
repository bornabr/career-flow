---
name: maintain
description: "Use to audit and maintain the private career knowledge base: stale facts, missing metrics, duplicate entries, broken links, inbox hygiene, and index validity."
---

# Maintain career knowledge

Resolve `<plugin-root>` from this file's installed path (two directories above) or
the expanded `${CLAUDE_PLUGIN_ROOT}` in Claude Code. Locate the private data repo
from the current directory (`config.yaml` and `data/`) or the `data_repo:` pointer
in `~/.config/career-flow/config`. If missing, suggest bootstrap and stop. Pull
before writing, inspect existing changes, then read `config.yaml`, `data/INDEX.md`,
and the relevant entity files including their raw notes.

Run `<plugin-root>/scripts/phase3_status.py <data-repo> --json`. Its report is
read-only and surfaces entries older than `memory.staleness_months`, `needs-metrics`
flags, similar skill/story titles, broken links, and whether INDEX matches the
current entities. Similarity is a review cue, not a merge instruction. If the user
asked only for a report, stop after explaining the findings.

For changes, propose a small, prioritized set and ask the user to verify current
facts. Update `last_verified` only for entries they actually confirm. Merge or
archive duplicates only after reviewing both full files and getting the user's
approval; preserve each source's original `## Raw notes` and repair incoming links.
Never silently delete a career entry or infer that an old skill has expired.
Triage inbox items only with explicit decisions. Fix schema and broken-link errors
without changing career claims beyond what the evidence supports. Regenerate
`data/INDEX.md` only through `<plugin-root>/scripts/validate.py <data-repo>`.

Show the proposed diff and validation result, then commit and push approved private
changes. Leave unapproved items unchanged and report them as open questions.
