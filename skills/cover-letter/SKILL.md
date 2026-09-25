---
name: cover-letter
description: Use when drafting a tailored cover letter, LinkedIn about section, short biography, or similar career blurb from verified career-data entries
---

# Cover letter and short career writing

Resolve `<plugin-root>` from this skill path (two directories above) or expanded
`${CLAUDE_PLUGIN_ROOT}` in Claude Code. Locate the private data repo from the current
directory (`config.yaml` plus `data/`) or the `data_repo:` pointer in
`~/.config/career-flow/config`. Stop and suggest bootstrap if neither is valid. Pull
before writes, read `data/INDEX.md` and `data/profile.md`, and inspect only the
relevant source entities. Avoid overwriting a dirty worktree.

1. Determine the requested format, audience, target role/company, length, and tone.
   For a tailored application, obtain the posting text or URL and save its source
   URL/access date. For a generic bio or LinkedIn summary, use the user's target-role
   preferences instead.
2. Build a brief claim map from source ids. Use `## Raw notes` to preserve nuance,
   and honor dates, contribution level, and any `needs-metrics` flags. Never invent
   results, motivations, relationships, or company knowledge. Ask for an important
   missing fact when it would change the message.
3. Draft direct, specific prose in the user's voice. For a letter, connect two or
   three supported examples to the posting and include a clear closing. For a short
   bio, fit the requested length. Avoid generic praise of the company and unsupported
   claims of fit.
4. Save a letter under `outputs/letters/<company>-<role>-<YYYY-MM-DD>/letter.md` or a
   generic blurb under `outputs/blurbs/<topic>-<YYYY-MM-DD>.md`. Include a short
   `sources.md` alongside it listing source ids, posting URL if any, and the claims
   drawn from each. Keep personal contact details only if the user wants them in the
   artifact.
5. Show the draft for review, revise, check every claim against its source, then
   commit and push the approved output. Never send or post it for the user.
