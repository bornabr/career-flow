# Entity Schema

Every entity is one Markdown file: YAML frontmatter + body. Enforced by `scripts/validate.py`.

## Placement and naming

| type        | directory            | id prefix | example file                      |
|-------------|----------------------|-----------|-----------------------------------|
| experience  | data/experiences/    | exp-      | data/experiences/exp-acme.md      |
| project     | data/projects/       | proj-     | data/projects/proj-career-flow.md |
| skill       | data/skills/         | skill-    | data/skills/skill-python.md       |
| education   | data/education/      | edu-      | data/education/edu-uoft-bsc.md    |
| publication | data/publications/   | pub-      | data/publications/pub-nlp-2024.md |
| story       | data/stories/        | story-    | data/stories/story-outage-fix.md  |
| application | data/applications/   | app-      | data/applications/app-acme-2026-08.md |

Filename stem MUST equal `id`. `data/profile.md`, `data/inbox.md`, `data/INDEX.md` are not entities.

## Frontmatter — required for every entity

- `id` (string, prefixed as above)
- `type` (one of the seven types)
- `title` (string)
- `summary` (one line; shown in INDEX.md — write it as the recall hook)
- `status`: `active` | `completed` | `archived`
- `visibility`: `public` | `private`  (public = eligible for the future webpage)
- `last_verified`: `YYYY-MM-DD` (updated whenever the user confirms the entry is accurate)

## Frontmatter — per type

- experience: required `org` (string), `start` (`YYYY-MM`); optional `end` (`YYYY-MM`, absent = current)
- project: required `start`; optional `end`, `org` (display text)
- skill: optional `level`: `beginner` | `intermediate` | `advanced` | `expert`
- education: required `org` (institution), `start`; optional `end`, `credential` (string)
- publication: required `venue` (string), `date` (`YYYY` or `YYYY-MM` or `YYYY-MM-DD`); optional `url`
- story: no extra required fields, but `links` MUST reference at least one `experience` or `project`
- application: required `company`, `role`, `date` (`YYYY-MM-DD`); optional `resume_variant` (repo-relative
  path to the resume PDF used), `contacts` (list of strings), `follow_ups` (list of `{date, note, done}`)

## Optional on any entity

- `links`: `experience` (single id), `project` (single id), `skills` (list of ids). Every referenced id must exist.
- `tags` (list of strings), `flags` (list; e.g. `needs-metrics` when the reviewer pass found gaps the user could not fill)

## Body

- `# Narrative` — refined, resume-ready prose: accomplishments with metrics, context, STAR notes.
- `## Raw notes` — the user's original words from capture, preserved verbatim (provenance).

## Warnings (non-fatal)

- Orphan skill: a skill entity referenced by no other entity's `links.skills`.
