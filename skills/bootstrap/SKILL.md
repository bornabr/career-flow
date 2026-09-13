---
name: bootstrap
description: Use when setting up career-flow for the first time - scaffolds the user's private career-data repo, connects it to GitHub, and imports their existing resume/CV through a guided gap interview
---

# Bootstrap — create and seed the career-data repo

## Resolve bundled resources

Before acting, resolve `<plugin-root>` to the plugin directory containing `scripts/`,
`templates/`, and this skill's parent `skills/` directory:

- In Claude Code, use the expanded `${CLAUDE_PLUGIN_ROOT}` value.
- Otherwise derive it from the loaded `SKILL.md` path (two directories above this file).

Verify `<plugin-root>/scripts/validate.py` and `<plugin-root>/templates/data-repo`
exist. Stop with a clear installation error if they do not. Never run a command with
an unresolved placeholder and never persist an installed plugin root; hosts may move
cached plugins during updates.

## Guard

If `~/.config/career-flow/config` already exists and points at a valid data repo, tell
the user bootstrap has already run (offer capture instead) and STOP unless they
explicitly want a second repo.

## Part 1 — scaffold the repo

1. Ask where the data repo should live. Default: `~/Projects/career-data`.
2. Copy the scaffold: `cp -R "<plugin-root>/templates/data-repo" <chosen-path>`.
3. Replace the placeholder in `<path>/.github/workflows/validate.yml`:
   - `{{PLUGIN_REPO}}` → the plugin's GitHub `owner/name`. Derive it from
     `git -C "<plugin-root>" remote get-url origin` when available, otherwise from
     the `repository` URL in a plugin manifest; ask the user only if neither works.
4. `git init` the repo, initial commit of the scaffold.
5. Create the private remote (ask permission first — this is an outward-facing action):
   `gh repo create <name> --private --source <path> --push`.
6. Write the pointer file `~/.config/career-flow/config` (create the directory):
   `data_repo: <absolute path>`
7. Tell the user about CI: while the plugin repo is private, the data repo needs a
   `PLUGIN_REPO_TOKEN` actions secret (fine-grained PAT, read-only contents on the
   plugin repo). Offer the command:
   `gh secret set PLUGIN_REPO_TOKEN --repo <owner>/<data-repo>` — or note CI will fail
   until then; validation still runs locally either way.

## Part 2 — import existing career material

1. Ask for source material: resume/CV file, LinkedIn profile/export, publications
   list, transcripts — whatever they have. Read what's provided.
2. Fill `data/profile.md` (name, headline, contact, links) from the material + user.
3. Parse the material into entities, newest first, using templates from
   `<plugin-root>/templates/entities/`:
   experiences, education, publications, obvious major projects, and skill files for
   the skills those entries reference. Filename = id; original resume wording goes in
   `## Raw notes` verbatim.
4. **Gap interview, one question at a time, newest experiences first:** missing
   metrics, missing dates, notable projects the resume undersells, story-worthy
   moments (offer to create story entities). Apply
   `<plugin-root>/templates/reviewer-checklist.md` to every entry; use
   `flags: [needs-metrics]` where the user can't supply numbers — bootstrap should be
   thorough but not exhausting; the maintain flow revisits flagged entries later.
5. Set every imported entry's `last_verified` to today.

## Part 3 — validate and push

1. Run `"<plugin-root>/scripts/validate.py" <data-repo-path>` — fix every ERROR
   and rerun until OK.
2. Review WARN lines (orphan skills are fine at this stage if the user wants them kept).
3. `git add -A && git commit -m "bootstrap: import initial career knowledge base"` and push.
4. Summarize for the user: entity counts by type, entries flagged needs-metrics, and
   suggested next step (use the capture skill as things happen).

## Rules

- Never invent facts, dates, or metrics not provided by the user or their documents.
- Ask before creating the GitHub repo or pushing (outward-facing actions).
- All imported entries default to `visibility: private`.
