# Reviewer Pass — quality gate for every new/updated entry

Run this checklist before finalizing ANY entity. Ask the user for what's missing —
one question at a time. Only if they genuinely can't supply a metric, add
`flags: [needs-metrics]` and move on.

1. **Quantified impact** — does the Narrative contain at least one concrete number
   (%, $, time saved, users, scale, team size)? "Improved performance" fails;
   "cut p95 latency 40%" passes.
2. **Dates** — start (and end if finished) present and plausible?
3. **Summary line** — is `summary` a hook someone scanning INDEX.md would understand
   out of context? No jargon-only summaries.
4. **Skills linked** — are the 2–5 most important skills in `links.skills`, and does
   each linked skill file exist (create missing ones from the skill template)?
5. **Story-worthy?** — if the user described a challenge→action→result arc, offer to
   also capture it as a story entity now (don't force it).
6. **Raw notes preserved** — the user's original words are in `## Raw notes`, verbatim,
   not paraphrased.
