---
name: interview-prep
description: Use when preparing a role- and company-specific interview pack with likely questions, STAR story matches, talking points, and evidence-backed gap analysis
---

# Interview prep — evidence-backed pack

Resolve `<plugin-root>` from this skill path (two directories above) or expanded
`${CLAUDE_PLUGIN_ROOT}` in Claude Code. Locate the private data repo from the current
directory (`config.yaml` plus `data/`) or the `data_repo:` pointer in
`~/.config/career-flow/config`. Pull before writing; preserve existing changes.
Read `data/INDEX.md`, `data/profile.md`, and the relevant experience, project, and
story files, including their raw notes.

1. Get the posting and company, plus interview stage if known. Save the posting URL
   and access date when sourced from the web. Distinguish posting requirements from
   researched company context and from facts supplied by the user.
2. Match each major requirement to the strongest specific source ids. Read full
   stories and relevant experiences; do not build questions from the index alone.
3. Write `outputs/prep-packs/<company>-<role>-<YYYY-MM-DD>/prep.md` with:
   - a concise role and company snapshot with source links/dates;
   - a requirement-to-evidence table (requirement, source id, talking point);
   - likely behavioral and technical questions, each paired with a specific STAR
     story id or a clearly labeled practice outline;
   - per-experience talking points, metrics and caveats;
   - gaps between the posting and verified career data, with honest bridging ideas
     and questions for the interviewer;
   - thoughtful questions to ask the interviewers.
4. Check that every career claim traces to an entity, every story id exists, and
   uncertain company facts are labeled as such. Show the pack for review, revise,
   then commit and push the approved private output.

Do not invent experience to close a gap. Do not present speculative interview
questions as questions the company will definitely ask.
