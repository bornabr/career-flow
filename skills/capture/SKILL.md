---
name: capture
description: Use when the user wants to log career knowledge - a project, accomplishment, new role, publication, education, STAR story, or job application - into their career-data repo through a guided interview
---

# Capture — guided career entry

## Resolve bundled resources

Before acting, resolve `<plugin-root>` to the plugin directory containing `scripts/`,
`templates/`, and this skill's parent `skills/` directory:

- In Claude Code, use the expanded `${CLAUDE_PLUGIN_ROOT}` value.
- Otherwise derive it from the loaded `SKILL.md` path (two directories above this file).

Verify `<plugin-root>/scripts/validate.py` and `<plugin-root>/templates/entities`
exist. Stop with a clear installation error if they do not. Never run a command with
an unresolved placeholder and do not rely on a plugin path saved by another host.

## Preconditions

- Locate the data repo: current directory if it has `config.yaml` + `data/`; otherwise
  read `data_repo:` from `~/.config/career-flow/config`. If neither exists, tell the
  user to run the career-flow bootstrap skill first and STOP.
- `cd` into the data repo and `git pull` before writing anything.
- Read `data/INDEX.md` and `config.yaml`.

## Flow

1. **What are we logging?** Ask (or infer from the request): project, accomplishment
   within an existing experience, new role/experience, publication, education, STAR
   story, or job application. Accomplishments usually mean UPDATING an existing
   experience/project rather than creating a new entity — check INDEX first and prefer
   updating.
2. **Interview, one question at a time.** Cover, per type:
   - project/experience: what/where/when, your specific role, impact WITH metrics,
     skills used, anything story-worthy
   - publication: title, venue, date, co-authors, your contribution, url
   - story: situation, task, action, result (metrics), which experience/project it belongs to
   - application: company, role, date, posting summary, resume variant used, contacts
3. **Draft the entity.** Copy the matching template from
   `<plugin-root>/templates/entities/`, fill it in. Slug rules: lowercase,
   hyphens, short (`proj-career-flow`). Filename = id. Put the user's original words
   verbatim under `## Raw notes`.
4. **Update cross-links.** Add skill ids to `links.skills`; CREATE any missing skill
   files from the skill template (brief summary is enough). If updating an existing
   entity, bump its `last_verified` to today.
5. **Reviewer pass.** Work through `<plugin-root>/templates/reviewer-checklist.md`.
   Show the user the final draft and get their OK.
6. **Triage inbox (quick).** If `data/inbox.md` has unchecked items, ask whether to
   handle any now; promote or delete per the user's answer.
7. **Validate.** Run `"<plugin-root>/scripts/validate.py" .` — fix every ERROR
   and rerun until it prints OK (this also regenerates INDEX.md).
8. **Commit and push.** `git add -A && git commit` with a message like
   `capture: add proj-career-flow` then `git push`.

## Rules

- Never invent metrics or embellish — everything must come from the user.
- Never delete or rewrite existing `## Raw notes` content.
- Never hand-edit `data/INDEX.md`.
