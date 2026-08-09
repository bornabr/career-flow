# Career Data Repo — Agent Instructions

This private repo is a career knowledge base managed by the career-flow plugin.
It stores work experiences, projects, skills, education, publications, STAR stories,
and job applications as Markdown files with YAML frontmatter.

## Before anything else

1. `git pull` — other tools may have pushed changes.
2. Read `data/INDEX.md` — the generated index of everything here. Load individual
   entity files only as needed; never assume INDEX is exhaustive detail.

## Layout and schema

- Entities live in `data/{experiences,projects,skills,education,publications,stories,applications}/`.
- One file per entity: `<id>.md`, id prefixes: exp- proj- skill- edu- pub- story- app-.
- Full schema: `docs/schema.md` in the plugin repo (path in `config.yaml` → `plugin.local_path`).
- Required frontmatter on every entity: id, type, title, summary (one line), status
  (active|completed|archived), visibility (public|private), last_verified (YYYY-MM-DD).
- Body: `# Narrative` (refined, metrics-heavy) and `## Raw notes` (user's words, verbatim —
  never rewrite or delete raw notes).

## Editing rules

1. Copy the matching template from the plugin repo `templates/entities/` for new entries.
2. Keep cross-links (`links:`) up to date; create missing skill files rather than
   leaving dangling references.
3. Quality gate before finalizing any entry: does it have quantified impact, dates, and
   a one-line summary? If the user can't supply metrics, add `flags: [needs-metrics]`.
4. After ANY change to `data/`: run the validate script and fix every ERROR:
   `<plugin.local_path>/scripts/validate.py .`  (regenerates data/INDEX.md)
5. Never hand-edit `data/INDEX.md`.
6. Commit with a descriptive message and push.

## data/inbox.md

Staging area for automatically noticed accomplishment candidates. Never promote inbox
items to entities without the user confirming; delete rejected items.

## Privacy

Everything here is private by default. `visibility: public` marks an entry as eligible
for the (future) public web page — set it only when the user says so.
