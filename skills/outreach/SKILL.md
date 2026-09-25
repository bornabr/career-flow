---
name: outreach
description: Use when identifying likely hiring contacts, drafting LinkedIn or email outreach and follow-ups, recording contacts and follow-up dates, or viewing follow-ups due for applications
---

# Outreach — drafts and follow-up tracking

Resolve `<plugin-root>` from this skill path (two directories above) or expanded
`${CLAUDE_PLUGIN_ROOT}` in Claude Code. Verify `scripts/due_followups.py`,
`scripts/validate.py`, and `templates/entities/application.md` exist. Locate the
private data repo from the current directory (`config.yaml` plus `data/`) or the
`data_repo:` pointer in `~/.config/career-flow/config`. Pull before writes; inspect
existing changes and read `data/INDEX.md`, `data/profile.md`, and the relevant
application and career entities.

## Due follow-ups

For "what is due?", run `<plugin-root>/scripts/due_followups.py <data-repo>` (optional
`--as-of YYYY-MM-DD`). This read-only view uses active applications and lists only
unfinished follow-ups due on or before the date. Show the application id and date;
never mark a follow-up done without the user's confirmation.

## Drafting flow

1. Identify the target application, company, role, and outreach purpose. If no
   application exists, create one from the application template using only known
   facts and the user's original notes. Keep `visibility: private`.
2. Use contacts supplied by the user or research public, work-related sources for
   likely hiring managers or recruiters. Record a name/title/profile URL and access
   date only when verifiable. Label a merely possible contact as tentative. Do not
   guess private addresses or imply a relationship that does not exist.
3. Draft a short LinkedIn note or email with a concrete, source-backed reason for
   reaching out and a low-pressure ask. Save drafts under
   `outputs/outreach/<company>-<role>-<YYYY-MM-DD>/` with a `sources.md` file
   recording the application id, career entity ids, and contact-source URLs/dates.
   These are drafts only: never send, connect, or post on the user's behalf.
4. Ask the user to approve any contacts to retain and follow-up dates. Add strings
   to `contacts` and `{date: YYYY-MM-DD, note: ..., done: false}` items to
   `follow_ups` in the application entity. Preserve existing raw notes. If the user
   says a message was sent or a follow-up was completed, record only that confirmed
   status; do not infer it from a draft.
5. Run `<plugin-root>/scripts/validate.py <data-repo>`, resolve errors, review the
   diff, and commit and push approved private changes.
