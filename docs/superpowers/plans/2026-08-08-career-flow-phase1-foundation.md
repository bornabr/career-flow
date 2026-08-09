# Career-Flow Phase 1 (Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the career-flow plugin foundation: plugin repo skeleton, entity schema + templates, validate script with INDEX generation, data-repo scaffold, and the bootstrap + capture skills — ending with a working plugin that can create a private career-data repo and capture entries.

**Architecture:** This repo (`career-flow`) is a Claude Code plugin (also consumable by Codex/ChatGPT per spec). Career data lives in a *separate* private repo scaffolded by the bootstrap skill from templates shipped in this plugin. A single self-contained Python script (`scripts/validate.py`) enforces the entity schema, checks cross-links, and regenerates `data/INDEX.md`; it runs locally at the end of every flow and in the data repo's CI.

**Tech Stack:** Markdown + YAML frontmatter (data), Python 3.11+ via `uv` single-file script with PyYAML (validation), pytest (tests), Claude Code plugin format (`.claude-plugin/plugin.json`, `skills/*/SKILL.md`), GitHub Actions (data-repo CI), `gh` CLI (repo creation).

**Spec:** `docs/superpowers/specs/2026-08-08-career-flow-plugin-design.md` — Phase 1 scope only. Outputs (resume/ATS, cover letter, interview prep, outreach), checkin/maintain skills, passive capture, and webpage are LATER phases: do not build them.

## Global Constraints

- Python `>=3.11`; the validate script is a `uv` PEP-723 single-file script; **only runtime dependency: `pyyaml`**.
- Run tests with: `uv run --with pyyaml --with pytest -- pytest tests/ -v` (no pyproject.toml in this repo).
- Entity id prefixes (exact): `exp-`, `proj-`, `skill-`, `edu-`, `pub-`, `story-`, `app-`. Filename stem MUST equal the full id (e.g., `exp-acme.md` has `id: exp-acme`).
- Entity dirs under `data/` (exact): `experiences`, `projects`, `skills`, `education`, `publications`, `stories`, `applications`. `data/profile.md`, `data/inbox.md`, `data/INDEX.md` are NOT entities and are never schema-validated.
- Common required frontmatter for every entity: `id`, `type`, `title`, `summary` (one line, used in INDEX), `status` (`active|completed|archived`), `visibility` (`public|private`), `last_verified` (`YYYY-MM-DD`).
- Scaffold placeholders use exact tokens `{{PLUGIN_REPO}}` and `{{PLUGIN_LOCAL_PATH}}`, always inside double quotes in YAML files.
- Commit messages: conventional commits (`feat:`, `test:`, `docs:`, `chore:`), each ending with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- INDEX.md generation must be deterministic (fixed section order, fixed sort) so CI can `git diff --exit-code` it.

## File Structure (end state of Phase 1)

```
career-flow/
├── .claude-plugin/
│   ├── plugin.json              # plugin manifest
│   └── marketplace.json         # lets this repo be added as a local marketplace
├── skills/
│   ├── bootstrap/SKILL.md
│   └── capture/SKILL.md
├── templates/
│   ├── reviewer-checklist.md    # shared quality gate used by bootstrap + capture
│   ├── entities/                # one template per entity type (7 files)
│   └── data-repo/               # scaffold copied verbatim by bootstrap
│       ├── AGENTS.md
│       ├── CLAUDE.md
│       ├── config.yaml
│       ├── .github/workflows/validate.yml
│       ├── .gitignore
│       ├── data/{experiences,projects,skills,education,publications,stories,applications}/.gitkeep
│       ├── data/profile.md
│       └── data/inbox.md
├── scripts/validate.py          # schema + links + INDEX (uv single-file script)
├── tests/
│   ├── conftest.py
│   ├── test_schema.py
│   ├── test_links.py
│   ├── test_index.py
│   └── test_e2e.py
├── docs/schema.md               # human-readable entity schema reference
└── README.md
```

---

### Task 1: Plugin repo skeleton and manifests

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `.gitignore`
- Create: `README.md`

**Interfaces:**
- Produces: plugin name `career-flow` (skills invoke as `career-flow:bootstrap`, `career-flow:capture`); marketplace addable via `claude plugin marketplace add /Users/bornabarahimi/Projects/career-flow`.

- [ ] **Step 1: Create `.claude-plugin/plugin.json`**

```json
{
  "name": "career-flow",
  "version": "0.1.0",
  "description": "Memory-backed career knowledge plugin: capture experiences, projects, skills, publications, and stories into a private git-synced knowledge base; generate resumes, interview prep, and more.",
  "author": { "name": "Borna Barahimi" }
}
```

- [ ] **Step 2: Create `.claude-plugin/marketplace.json`**

```json
{
  "name": "career-flow-marketplace",
  "owner": { "name": "Borna Barahimi" },
  "plugins": [
    {
      "name": "career-flow",
      "source": "./",
      "description": "Memory-backed career knowledge plugin"
    }
  ]
}
```

- [ ] **Step 3: Create `.gitignore`**

```
__pycache__/
.pytest_cache/
*.pyc
.DS_Store
```

- [ ] **Step 4: Create `README.md`**

```markdown
# career-flow

Memory-backed career knowledge plugin for Claude Code / Cowork, Codex, and ChatGPT Work.

Your career data lives in a **separate private repo** (scaffolded by the `bootstrap` skill),
never in this plugin repo. See `docs/superpowers/specs/2026-08-08-career-flow-plugin-design.md`
for the full design and `docs/schema.md` for the entity schema.

## Install (Claude Code)

    claude plugin marketplace add /Users/bornabarahimi/Projects/career-flow
    claude plugin install career-flow@career-flow-marketplace

## First run

Invoke the `career-flow:bootstrap` skill — it scaffolds your private career-data repo
and imports your existing resume.

## Development

    uv run --with pyyaml --with pytest -- pytest tests/ -v
```

- [ ] **Step 5: Verify both JSON files parse**

Run: `python3 -m json.tool .claude-plugin/plugin.json && python3 -m json.tool .claude-plugin/marketplace.json`
Expected: both print formatted JSON, exit 0.

- [ ] **Step 6: Commit**

```bash
git add .claude-plugin .gitignore README.md
git commit -m "feat: plugin skeleton and manifests

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Entity schema doc and entity templates

**Files:**
- Create: `docs/schema.md`
- Create: `templates/entities/experience.md`, `templates/entities/project.md`, `templates/entities/skill.md`, `templates/entities/education.md`, `templates/entities/publication.md`, `templates/entities/story.md`, `templates/entities/application.md`

**Interfaces:**
- Produces: the frontmatter schema that `scripts/validate.py` (Tasks 3–5) enforces and the templates that the capture/bootstrap skills (Tasks 8–9) copy from. Field names here are the single source of truth — later tasks must match exactly.

- [ ] **Step 1: Create `docs/schema.md`**

```markdown
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
```

- [ ] **Step 2: Create the seven entity templates**

`templates/entities/experience.md`:
```markdown
---
id: exp-SLUG
type: experience
title: ROLE TITLE
summary: ONE-LINE HOOK FOR INDEX
org: COMPANY
start: YYYY-MM
# end: YYYY-MM        # omit while current
status: active
visibility: private
last_verified: YYYY-MM-DD
links:
  skills: []
tags: []
---
# Narrative

What the role is, scope, and accomplishments with metrics.

## Raw notes

(user's original words, verbatim)
```

`templates/entities/project.md`:
```markdown
---
id: proj-SLUG
type: project
title: PROJECT TITLE
summary: ONE-LINE HOOK FOR INDEX
start: YYYY-MM
# end: YYYY-MM
# org: COMPANY OR "Personal"
status: active
visibility: private
last_verified: YYYY-MM-DD
links:
  # experience: exp-SLUG
  skills: []
tags: []
---
# Narrative

What it is, your role, impact with metrics.

## Raw notes

(user's original words, verbatim)
```

`templates/entities/skill.md`:
```markdown
---
id: skill-SLUG
type: skill
title: SKILL NAME
summary: ONE-LINE HOOK FOR INDEX
# level: advanced     # beginner | intermediate | advanced | expert
status: active
visibility: private
last_verified: YYYY-MM-DD
tags: []
---
# Narrative

Evidence lives in the projects/experiences that link here; add context only if needed.

## Raw notes

(user's original words, verbatim)
```

`templates/entities/education.md`:
```markdown
---
id: edu-SLUG
type: education
title: DEGREE / PROGRAM
summary: ONE-LINE HOOK FOR INDEX
org: INSTITUTION
start: YYYY-MM
# end: YYYY-MM
# credential: B.Sc. Computer Science
status: completed
visibility: private
last_verified: YYYY-MM-DD
tags: []
---
# Narrative

Focus areas, thesis, honors, relevant coursework.

## Raw notes

(user's original words, verbatim)
```

`templates/entities/publication.md`:
```markdown
---
id: pub-SLUG
type: publication
title: PAPER / ARTICLE TITLE
summary: ONE-LINE HOOK FOR INDEX
venue: VENUE
date: YYYY-MM
# url: https://...
status: completed
visibility: private
last_verified: YYYY-MM-DD
links:
  skills: []
tags: []
---
# Narrative

Abstract-level summary, your contribution, citations/impact.

## Raw notes

(user's original words, verbatim)
```

`templates/entities/story.md`:
```markdown
---
id: story-SLUG
type: story
title: STORY TITLE
summary: ONE-LINE HOOK FOR INDEX
status: active
visibility: private
last_verified: YYYY-MM-DD
links:
  experience: exp-SLUG     # at least one of experience/project required
  # project: proj-SLUG
  skills: []
tags: []
---
# Narrative

**Situation:**
**Task:**
**Action:**
**Result:** (with metrics)

## Raw notes

(user's original words, verbatim)
```

`templates/entities/application.md`:
```markdown
---
id: app-SLUG
type: application
title: ROLE @ COMPANY
summary: ONE-LINE HOOK FOR INDEX
company: COMPANY
role: ROLE
date: YYYY-MM-DD
# resume_variant: outputs/resumes/COMPANY-ROLE-DATE/resume.pdf
# contacts: ["Jane Doe — recruiter — linkedin.com/in/..."]
# follow_ups:
#   - {date: YYYY-MM-DD, note: "polite nudge", done: false}
status: active
visibility: private
last_verified: YYYY-MM-DD
tags: []
---
# Narrative

Posting summary, why applied, tailoring notes.

## Raw notes

(user's original words, verbatim)
```

- [ ] **Step 3: Verify all templates have parseable frontmatter**

Run:
```bash
uv run --with pyyaml python3 -c "
import yaml, pathlib
for p in sorted(pathlib.Path('templates/entities').glob('*.md')):
    fm = p.read_text().split('---')[1]
    yaml.safe_load(fm)
    print('ok', p.name)
"
```
Expected: seven `ok` lines, exit 0.

- [ ] **Step 4: Commit**

```bash
git add docs/schema.md templates/entities
git commit -m "feat: entity schema reference and templates

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: validate.py — frontmatter parsing and schema validation

**Files:**
- Create: `scripts/validate.py`
- Create: `tests/conftest.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Produces (used by Tasks 4–5 and tests):
  - `parse_frontmatter(text: str) -> tuple[dict | None, str | None]` — returns `(frontmatter, error)`.
  - `load_entities(data_dir: Path) -> tuple[dict[str, dict], list[str]]` — returns `(entities_by_id, errors)`; each entity dict gains `_path: Path`. Handles: unreadable frontmatter, filename≠id, wrong prefix for directory, duplicate ids, plus `check_schema` errors.
  - `check_schema(entity: dict) -> list[str]` — per-entity field errors.
  - Module constants: `ENTITY_DIRS`, `COMMON_REQUIRED`, `TYPE_REQUIRED`, `STATUS_VALUES`, `VISIBILITY_VALUES`.

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "validate.py"

ENTITY_DIRNAMES = [
    "experiences", "projects", "skills", "education",
    "publications", "stories", "applications",
]


@pytest.fixture(scope="session")
def vmod():
    spec = importlib.util.spec_from_file_location("validate_mod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def data_repo(tmp_path):
    for d in ENTITY_DIRNAMES:
        (tmp_path / "data" / d).mkdir(parents=True)
    return tmp_path


def write_entity(repo, dirname, filename, frontmatter, body="Body.\n"):
    path = repo / "data" / dirname / filename
    path.write_text(f"---\n{frontmatter}---\n\n{body}")
    return path


VALID_PROJECT = """id: proj-alpha
type: project
title: Alpha
summary: Built the Alpha pipeline
status: active
visibility: private
last_verified: 2026-08-08
start: 2026-01
links:
  skills: [skill-python]
"""

VALID_SKILL = """id: skill-python
type: skill
title: Python
summary: Primary language
status: active
visibility: private
last_verified: 2026-08-08
"""
```

- [ ] **Step 2: Write the failing tests in `tests/test_schema.py`**

```python
from conftest import VALID_PROJECT, VALID_SKILL, write_entity


def test_parse_frontmatter_valid(vmod):
    fm, err = vmod.parse_frontmatter("---\nid: x\ntitle: T\n---\nbody")
    assert err is None
    assert fm == {"id": "x", "title": "T"}


def test_parse_frontmatter_missing(vmod):
    fm, err = vmod.parse_frontmatter("no frontmatter here")
    assert fm is None
    assert "frontmatter" in err


def test_load_valid_entity(vmod, data_repo):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)
    write_entity(data_repo, "skills", "skill-python.md", VALID_SKILL)
    entities, errors = vmod.load_entities(data_repo / "data")
    assert errors == []
    assert set(entities) == {"proj-alpha", "skill-python"}
    assert entities["proj-alpha"]["title"] == "Alpha"


def test_filename_must_match_id(vmod, data_repo):
    write_entity(data_repo, "projects", "proj-wrongname.md", VALID_PROJECT)
    _, errors = vmod.load_entities(data_repo / "data")
    assert any("filename" in e for e in errors)


def test_wrong_prefix_for_directory(vmod, data_repo):
    bad = VALID_PROJECT.replace("id: proj-alpha", "id: exp-alpha")
    write_entity(data_repo, "projects", "exp-alpha.md", bad)
    _, errors = vmod.load_entities(data_repo / "data")
    assert any("prefix" in e for e in errors)


def test_missing_required_field(vmod):
    entity = {"id": "proj-a", "type": "project", "title": "A",
              "status": "active", "visibility": "private",
              "last_verified": "2026-08-08", "start": "2026-01"}
    errors = vmod.check_schema(entity)          # summary missing
    assert any("summary" in e for e in errors)


def test_bad_enum_values(vmod):
    entity = {"id": "skill-x", "type": "skill", "title": "X", "summary": "s",
              "status": "открыт", "visibility": "everyone",
              "last_verified": "2026-08-08"}
    errors = vmod.check_schema(entity)
    assert any("status" in e for e in errors)
    assert any("visibility" in e for e in errors)


def test_bad_dates(vmod):
    entity = {"id": "proj-a", "type": "project", "title": "A", "summary": "s",
              "status": "active", "visibility": "private",
              "last_verified": "yesterday", "start": "January 2026"}
    errors = vmod.check_schema(entity)
    assert any("last_verified" in e for e in errors)
    assert any("start" in e for e in errors)


def test_story_requires_experience_or_project_link(vmod):
    entity = {"id": "story-x", "type": "story", "title": "X", "summary": "s",
              "status": "active", "visibility": "private",
              "last_verified": "2026-08-08", "links": {"skills": []}}
    errors = vmod.check_schema(entity)
    assert any("story" in e and "link" in e for e in errors)


def test_duplicate_ids(vmod, data_repo):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)
    dup = VALID_PROJECT.replace("proj-alpha", "proj-beta") \
                       .replace("id: proj-beta", "id: proj-alpha")
    write_entity(data_repo, "projects", "proj-beta.md", dup)
    _, errors = vmod.load_entities(data_repo / "data")
    assert any("duplicate" in e for e in errors)
```

Note on `test_duplicate_ids`: the double-replace writes a file named `proj-beta.md` whose `id:` is still `proj-alpha` — expect BOTH a filename-mismatch error and a duplicate-id error; the assertion only needs the duplicate one.

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run --with pyyaml --with pytest -- pytest tests/test_schema.py -v`
Expected: FAIL — `scripts/validate.py` does not exist (conftest import error).

- [ ] **Step 4: Write `scripts/validate.py` (parsing + schema portion)**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Validate a career-data repo and regenerate data/INDEX.md.

Usage: validate.py [DATA_REPO_ROOT]   (defaults to cwd)
Exit codes: 0 ok, 1 validation errors, 2 usage/structure errors.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# directory -> (type, id prefix)
ENTITY_DIRS = {
    "experiences": ("experience", "exp-"),
    "projects": ("project", "proj-"),
    "skills": ("skill", "skill-"),
    "education": ("education", "edu-"),
    "publications": ("publication", "pub-"),
    "stories": ("story", "story-"),
    "applications": ("application", "app-"),
}

COMMON_REQUIRED = ["id", "type", "title", "summary", "status", "visibility", "last_verified"]
TYPE_REQUIRED = {
    "experience": ["org", "start"],
    "project": ["start"],
    "skill": [],
    "education": ["org", "start"],
    "publication": ["venue", "date"],
    "story": [],
    "application": ["company", "role", "date"],
}
STATUS_VALUES = {"active", "completed", "archived"}
VISIBILITY_VALUES = {"public", "private"}
LEVEL_VALUES = {"beginner", "intermediate", "advanced", "expert"}

FULL_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")      # last_verified, application date
LOOSE_DATE_RE = re.compile(r"^\d{4}(-\d{2})?(-\d{2})?$")  # start/end/publication date


def parse_frontmatter(text: str) -> tuple[dict | None, str | None]:
    if not text.startswith("---\n"):
        return None, "missing frontmatter (file must start with ---)"
    end = text.find("\n---", 4)
    if end == -1:
        return None, "unterminated frontmatter"
    try:
        fm = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        return None, f"invalid YAML in frontmatter: {exc}"
    if not isinstance(fm, dict):
        return None, "frontmatter is not a mapping"
    return fm, None


def _date_ok(value, pattern) -> bool:
    return isinstance(value, str) and bool(pattern.match(value))


def check_schema(entity: dict) -> list[str]:
    eid = entity.get("id", "<no id>")
    errors: list[str] = []
    for field in COMMON_REQUIRED:
        if field not in entity or entity[field] in (None, ""):
            errors.append(f"{eid}: missing required field '{field}'")
    etype = entity.get("type")
    if etype not in TYPE_REQUIRED:
        errors.append(f"{eid}: unknown type '{etype}'")
        return errors
    for field in TYPE_REQUIRED[etype]:
        if field not in entity or entity[field] in (None, ""):
            errors.append(f"{eid}: missing required field '{field}' for type {etype}")
    if "status" in entity and entity["status"] not in STATUS_VALUES:
        errors.append(f"{eid}: status must be one of {sorted(STATUS_VALUES)}")
    if "visibility" in entity and entity["visibility"] not in VISIBILITY_VALUES:
        errors.append(f"{eid}: visibility must be one of {sorted(VISIBILITY_VALUES)}")
    if "last_verified" in entity and not _date_ok(str(entity.get("last_verified")), FULL_DATE_RE):
        errors.append(f"{eid}: last_verified must be YYYY-MM-DD")
    for field in ("start", "end", "date"):
        if field in entity and entity[field] is not None \
                and not _date_ok(str(entity[field]), LOOSE_DATE_RE):
            errors.append(f"{eid}: {field} must be YYYY[-MM[-DD]]")
    if etype == "application" and "date" in entity \
            and not _date_ok(str(entity.get("date")), FULL_DATE_RE):
        errors.append(f"{eid}: application date must be YYYY-MM-DD")
    if etype == "skill" and entity.get("level") is not None \
            and entity["level"] not in LEVEL_VALUES:
        errors.append(f"{eid}: level must be one of {sorted(LEVEL_VALUES)}")
    links = entity.get("links") or {}
    if not isinstance(links, dict):
        errors.append(f"{eid}: links must be a mapping")
        links = {}
    if "skills" in links and not isinstance(links["skills"], list):
        errors.append(f"{eid}: links.skills must be a list")
    for single in ("experience", "project"):
        if single in links and not isinstance(links[single], str):
            errors.append(f"{eid}: links.{single} must be a single id string")
    if etype == "story" and not (links.get("experience") or links.get("project")):
        errors.append(f"{eid}: story must link at least one experience or project")
    for listfield in ("tags", "flags", "contacts", "follow_ups"):
        if listfield in entity and entity[listfield] is not None \
                and not isinstance(entity[listfield], list):
            errors.append(f"{eid}: {listfield} must be a list")
    return errors


def load_entities(data_dir: Path) -> tuple[dict[str, dict], list[str]]:
    entities: dict[str, dict] = {}
    errors: list[str] = []
    for dirname, (etype, prefix) in ENTITY_DIRS.items():
        subdir = data_dir / dirname
        if not subdir.is_dir():
            errors.append(f"data/{dirname}: directory missing")
            continue
        for path in sorted(subdir.glob("*.md")):
            rel = f"data/{dirname}/{path.name}"
            fm, err = parse_frontmatter(path.read_text())
            if err:
                errors.append(f"{rel}: {err}")
                continue
            eid = str(fm.get("id", ""))
            if path.stem != eid:
                errors.append(f"{rel}: filename must match id '{eid}'")
            if not eid.startswith(prefix):
                errors.append(f"{rel}: id must use prefix '{prefix}' in data/{dirname}")
            if fm.get("type") != etype:
                errors.append(f"{rel}: type must be '{etype}' in data/{dirname}")
            if eid in entities:
                errors.append(f"{rel}: duplicate id '{eid}'")
                continue
            fm["_path"] = path
            errors.extend(check_schema(fm))
            entities[eid] = fm
    return entities, errors
```

(The `main()` function and INDEX generation are added in Tasks 4–5; the module must import cleanly without them at this point — do not add a `if __name__ == "__main__"` block yet.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --with pyyaml --with pytest -- pytest tests/test_schema.py -v`
Expected: 10 PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/validate.py tests/conftest.py tests/test_schema.py
git commit -m "feat: validate.py frontmatter parsing and schema checks

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: validate.py — link integrity and orphan-skill warnings

**Files:**
- Modify: `scripts/validate.py` (append after `load_entities`)
- Test: `tests/test_links.py`

**Interfaces:**
- Consumes: `load_entities`, constants from Task 3.
- Produces: `check_links(entities: dict[str, dict]) -> tuple[list[str], list[str]]` — `(errors, warnings)`. Errors: any `links.experience` / `links.project` / `links.skills` id that doesn't exist. Warnings: `orphan skill` for skill entities referenced by no other entity.

- [ ] **Step 1: Write the failing tests in `tests/test_links.py`**

```python
from conftest import VALID_PROJECT, VALID_SKILL, write_entity


def _load(vmod, data_repo):
    entities, errors = vmod.load_entities(data_repo / "data")
    assert errors == []
    return entities


def test_valid_links_no_errors(vmod, data_repo):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)
    write_entity(data_repo, "skills", "skill-python.md", VALID_SKILL)
    errors, warnings = vmod.check_links(_load(vmod, data_repo))
    assert errors == []
    assert warnings == []


def test_broken_link_is_error(vmod, data_repo):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)  # -> skill-python
    errors, _ = vmod.check_links(_load(vmod, data_repo))
    assert any("skill-python" in e and "not exist" in e for e in errors)


def test_orphan_skill_is_warning(vmod, data_repo):
    write_entity(data_repo, "skills", "skill-python.md", VALID_SKILL)
    errors, warnings = vmod.check_links(_load(vmod, data_repo))
    assert errors == []
    assert any("orphan" in w and "skill-python" in w for w in warnings)


def test_broken_experience_link(vmod, data_repo):
    story = """id: story-x
type: story
title: X
summary: s
status: active
visibility: private
last_verified: 2026-08-08
links:
  experience: exp-ghost
"""
    write_entity(data_repo, "stories", "story-x.md", story)
    errors, _ = vmod.check_links(_load(vmod, data_repo))
    assert any("exp-ghost" in e for e in errors)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pyyaml --with pytest -- pytest tests/test_links.py -v`
Expected: FAIL with `AttributeError: ... has no attribute 'check_links'`.

- [ ] **Step 3: Append `check_links` to `scripts/validate.py`**

```python
def check_links(entities: dict[str, dict]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    referenced: set[str] = set()
    for eid, entity in entities.items():
        links = entity.get("links") or {}
        if not isinstance(links, dict):
            continue  # already reported by check_schema
        targets: list[str] = []
        for single in ("experience", "project"):
            if isinstance(links.get(single), str):
                targets.append(links[single])
        if isinstance(links.get("skills"), list):
            targets.extend(t for t in links["skills"] if isinstance(t, str))
        for target in targets:
            referenced.add(target)
            if target not in entities:
                errors.append(f"{eid}: linked id '{target}' does not exist")
    warnings = [
        f"orphan skill: '{eid}' is referenced by no other entity"
        for eid, e in sorted(entities.items())
        if e.get("type") == "skill" and eid not in referenced
    ]
    return errors, warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --with pyyaml --with pytest -- pytest tests/test_links.py tests/test_schema.py -v`
Expected: all PASS (schema tests still green).

- [ ] **Step 5: Commit**

```bash
git add scripts/validate.py tests/test_links.py
git commit -m "feat: validate.py link integrity and orphan-skill warnings

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: validate.py — INDEX.md generation and CLI entry point

**Files:**
- Modify: `scripts/validate.py` (append; add `__main__` block; `chmod +x`)
- Test: `tests/test_index.py`

**Interfaces:**
- Consumes: `load_entities`, `check_links`.
- Produces:
  - `build_index(entities: dict[str, dict]) -> str` — deterministic INDEX.md content.
  - `main(argv: list[str]) -> int` — full CLI: loads, checks, prints `ERROR:`/`WARN:` lines, writes `data/INDEX.md` on success. Exit 0 ok / 1 errors / 2 missing `data/` dir.
  - INDEX format (exact):
    - header line `# INDEX` then blank line then `<!-- generated by scripts/validate.py — do not edit by hand -->`
    - sections in fixed order with fixed titles: `## Experiences`, `## Projects`, `## Skills`, `## Education`, `## Publications`, `## Stories`, `## Applications` (a section is omitted when empty)
    - entry line: `- {id} — {title} ({dates}) — {summary}` where `{dates}` is `start – end`, `start –` if ongoing, or `date`; the ` ({dates})` part is omitted when the entity has no dates (e.g., skills)
    - entries sorted by date descending (newest first), ties by id ascending

- [ ] **Step 1: Write the failing tests in `tests/test_index.py`**

```python
from conftest import VALID_PROJECT, VALID_SKILL, write_entity

EXP = """id: exp-acme
type: experience
title: Senior Engineer
summary: Led the platform team
org: Acme
start: 2022-03
status: active
visibility: private
last_verified: 2026-08-08
links:
  skills: [skill-python]
"""

OLD_PROJECT = VALID_PROJECT.replace("proj-alpha", "proj-old") \
                           .replace("start: 2026-01", "start: 2020-05")


def test_index_content_and_order(vmod, data_repo):
    write_entity(data_repo, "experiences", "exp-acme.md", EXP)
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)
    write_entity(data_repo, "projects", "proj-old.md", OLD_PROJECT)
    write_entity(data_repo, "skills", "skill-python.md", VALID_SKILL)
    entities, errors = vmod.load_entities(data_repo / "data")
    assert errors == []
    index = vmod.build_index(entities)
    assert index.startswith("# INDEX\n")
    assert "do not edit by hand" in index
    assert "- exp-acme — Senior Engineer (2022-03 –) — Led the platform team" in index
    assert "- skill-python — Python — Primary language" in index
    assert index.index("## Experiences") < index.index("## Projects") < index.index("## Skills")
    # newest project first
    assert index.index("proj-alpha") < index.index("proj-old")
    # empty sections omitted
    assert "## Stories" not in index


def test_index_deterministic(vmod, data_repo):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)
    write_entity(data_repo, "skills", "skill-python.md", VALID_SKILL)
    entities, _ = vmod.load_entities(data_repo / "data")
    assert vmod.build_index(entities) == vmod.build_index(entities)


def test_main_success_writes_index(vmod, data_repo, capsys):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)
    write_entity(data_repo, "skills", "skill-python.md", VALID_SKILL)
    rc = vmod.main([str(data_repo)])
    assert rc == 0
    assert (data_repo / "data" / "INDEX.md").exists()
    assert "OK" in capsys.readouterr().out


def test_main_errors_no_index(vmod, data_repo, capsys):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)  # broken link
    rc = vmod.main([str(data_repo)])
    assert rc == 1
    assert not (data_repo / "data" / "INDEX.md").exists()
    assert "ERROR:" in capsys.readouterr().out


def test_main_missing_data_dir(vmod, tmp_path):
    assert vmod.main([str(tmp_path)]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pyyaml --with pytest -- pytest tests/test_index.py -v`
Expected: FAIL with `AttributeError: ... 'build_index'`.

- [ ] **Step 3: Append to `scripts/validate.py`**

```python
SECTION_ORDER = [
    ("experience", "Experiences"), ("project", "Projects"), ("skill", "Skills"),
    ("education", "Education"), ("publication", "Publications"),
    ("story", "Stories"), ("application", "Applications"),
]


def _dates_label(entity: dict) -> str:
    if entity.get("start"):
        return f"{entity['start']} – {entity.get('end') or ''}".rstrip()
    if entity.get("date"):
        return str(entity["date"])
    return ""


def _sort_key(entity: dict) -> tuple[str, str]:
    date = str(entity.get("start") or entity.get("date") or "0000")
    return date, entity["id"]


def build_index(entities: dict[str, dict]) -> str:
    lines = ["# INDEX", "",
             "<!-- generated by scripts/validate.py — do not edit by hand -->"]
    for etype, title in SECTION_ORDER:
        group = [e for e in entities.values() if e.get("type") == etype]
        if not group:
            continue
        group.sort(key=lambda e: e["id"])                       # tie-break: id asc
        group.sort(key=lambda e: _sort_key(e)[0], reverse=True)  # primary: date desc (stable)
        lines += ["", f"## {title}", ""]
        for e in group:
            dates = _dates_label(e)
            datepart = f" ({dates})" if dates else ""
            lines.append(f"- {e['id']} — {e['title']}{datepart} — {e['summary']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    repo_root = Path(argv[0]) if argv else Path.cwd()
    data_dir = repo_root / "data"
    if not data_dir.is_dir():
        print(f"ERROR: {data_dir} is not a directory (run from the data repo root)")
        return 2
    entities, errors = load_entities(data_dir)
    link_errors, warnings = check_links(entities)
    errors.extend(link_errors)
    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"FAILED: {len(errors)} error(s)")
        return 1
    (data_dir / "INDEX.md").write_text(build_index(entities))
    print(f"OK: {len(entities)} entities validated, data/INDEX.md regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Make executable and run all tests**

Run: `chmod +x scripts/validate.py && uv run --with pyyaml --with pytest -- pytest tests/ -v`
Expected: all tests PASS.

- [ ] **Step 5: Smoke-test the script standalone**

Run: `mkdir -p /tmp/cf-smoke/data/{experiences,projects,skills,education,publications,stories,applications} && ./scripts/validate.py /tmp/cf-smoke && cat /tmp/cf-smoke/data/INDEX.md && rm -rf /tmp/cf-smoke`
Expected: `OK: 0 entities validated...`, INDEX.md contains only the header.

- [ ] **Step 6: Commit**

```bash
git add scripts/validate.py tests/test_index.py
git commit -m "feat: validate.py INDEX generation and CLI entry point

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Data-repo scaffold templates

**Files:**
- Create: `templates/data-repo/AGENTS.md`
- Create: `templates/data-repo/CLAUDE.md`
- Create: `templates/data-repo/config.yaml`
- Create: `templates/data-repo/.gitignore`
- Create: `templates/data-repo/.github/workflows/validate.yml`
- Create: `templates/data-repo/data/profile.md`
- Create: `templates/data-repo/data/inbox.md`
- Create: `templates/data-repo/data/{experiences,projects,skills,education,publications,stories,applications}/.gitkeep`

**Interfaces:**
- Consumes: schema from Task 2; validate.py CLI from Task 5.
- Produces: the scaffold that `bootstrap` (Task 9) copies verbatim, then replaces `{{PLUGIN_REPO}}` (e.g., `bornabarahimi/career-flow`) and `{{PLUGIN_LOCAL_PATH}}` (e.g., `/Users/bornabarahimi/Projects/career-flow`) in `config.yaml` and `.github/workflows/validate.yml`.

- [ ] **Step 1: Create `templates/data-repo/AGENTS.md`**

```markdown
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
```

- [ ] **Step 2: Create `templates/data-repo/CLAUDE.md`**

```markdown
Read AGENTS.md — it contains all conventions for this repo.
```

- [ ] **Step 3: Create `templates/data-repo/config.yaml`**

```yaml
# career-flow user configuration (read by all flows before acting)
plugin:
  repo: "{{PLUGIN_REPO}}"              # GitHub owner/name of the plugin repo
  local_path: "{{PLUGIN_LOCAL_PATH}}"  # local clone of the plugin repo

capture:
  checkin_interval_days: 14
  passive:
    enabled: false                     # Phase 3 feature; keep false
    sources: [github, claude_sessions]

memory:
  staleness_months: 6                  # maintain flow flags entries older than this

outputs:
  resume:
    engine: typst                      # Phase 2 feature
```

- [ ] **Step 4: Create `templates/data-repo/.gitignore`**

```
.DS_Store
```

- [ ] **Step 5: Create `templates/data-repo/.github/workflows/validate.yml`**

```yaml
name: validate
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/checkout@v4
        with:
          repository: "{{PLUGIN_REPO}}"
          token: ${{ secrets.PLUGIN_REPO_TOKEN }}   # PAT with read access while plugin repo is private
          path: .career-flow-plugin
      - uses: astral-sh/setup-uv@v5
      - name: validate entities and INDEX freshness
        run: |
          uv run .career-flow-plugin/scripts/validate.py .
          git diff --exit-code data/INDEX.md
```

- [ ] **Step 6: Create `templates/data-repo/data/profile.md`**

```markdown
---
name:
headline:
email:
location:
links:
  github:
  linkedin:
  website:
preferences:
  target_roles: []
  locations: []
---
# Profile

Free-form notes about career direction, positioning, constraints.
```

- [ ] **Step 7: Create `templates/data-repo/data/inbox.md`**

```markdown
# Inbox

Staging area for accomplishment candidates noticed by passive capture (or jotted quickly).
Each item is triaged during the next capture/check-in: promoted to an entity or deleted.

<!-- format: - [ ] YYYY-MM-DD source: one-line candidate -->
```

- [ ] **Step 8: Create the seven `.gitkeep` files**

Run: `mkdir -p templates/data-repo/data/{experiences,projects,skills,education,publications,stories,applications} && touch templates/data-repo/data/{experiences,projects,skills,education,publications,stories,applications}/.gitkeep`

- [ ] **Step 9: Verify the YAML files parse (with placeholders in place)**

Run:
```bash
uv run --with pyyaml python3 -c "
import yaml
yaml.safe_load(open('templates/data-repo/config.yaml'))
print('config ok')
yaml.safe_load(open('templates/data-repo/.github/workflows/validate.yml'))
print('workflow ok')
"
```
Expected: `config ok`, `workflow ok`.

- [ ] **Step 10: Commit**

```bash
git add templates/data-repo
git commit -m "feat: data-repo scaffold templates

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: End-to-end test — scaffold + sample data + validate

**Files:**
- Test: `tests/test_e2e.py`

**Interfaces:**
- Consumes: `templates/data-repo/` scaffold (Task 6), `scripts/validate.py` CLI (Task 5), conftest `EXP`-style entity strings (defined inline here).

- [ ] **Step 1: Write the failing e2e test in `tests/test_e2e.py`**

```python
import shutil
import subprocess
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SCAFFOLD = PLUGIN / "templates" / "data-repo"
SCRIPT = PLUGIN / "scripts" / "validate.py"

EXP = """---
id: exp-acme
type: experience
title: Senior Engineer
summary: Led the platform team
org: Acme
start: 2022-03
status: active
visibility: private
last_verified: 2026-08-08
links:
  skills: [skill-python]
---
# Narrative
Led a team of five.

## Raw notes
raw
"""

SKILL = """---
id: skill-python
type: skill
title: Python
summary: Primary language
status: active
visibility: private
last_verified: 2026-08-08
---
# Narrative
n

## Raw notes
raw
"""


def run_validate(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", str(SCRIPT), str(repo)],
        capture_output=True, text=True,
    )


def scaffold(tmp_path: Path) -> Path:
    repo = tmp_path / "career-data"
    shutil.copytree(SCAFFOLD, repo)
    return repo


def test_fresh_scaffold_validates_clean(tmp_path):
    repo = scaffold(tmp_path)
    result = run_validate(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / "data" / "INDEX.md").exists()
    assert (repo / "AGENTS.md").exists()
    assert (repo / "config.yaml").exists()
    assert (repo / ".github" / "workflows" / "validate.yml").exists()


def test_scaffold_with_entities_builds_index(tmp_path):
    repo = scaffold(tmp_path)
    (repo / "data" / "experiences" / "exp-acme.md").write_text(EXP)
    (repo / "data" / "skills" / "skill-python.md").write_text(SKILL)
    result = run_validate(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    index = (repo / "data" / "INDEX.md").read_text()
    assert "- exp-acme — Senior Engineer (2022-03 –) — Led the platform team" in index
    assert "- skill-python — Python — Primary language" in index


def test_broken_data_fails_validation(tmp_path):
    repo = scaffold(tmp_path)
    (repo / "data" / "experiences" / "exp-acme.md").write_text(
        EXP.replace("org: Acme\n", ""))          # drop required field
    result = run_validate(repo)
    assert result.returncode == 1
    assert "ERROR:" in result.stdout
```

- [ ] **Step 2: Run the e2e tests**

Run: `uv run --with pyyaml --with pytest -- pytest tests/test_e2e.py -v`
Expected: PASS if Tasks 5–6 are correct. If any fail, fix validate.py or the scaffold — this test is the integration gate.

- [ ] **Step 3: Run the full suite**

Run: `uv run --with pyyaml --with pytest -- pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: end-to-end scaffold + validate integration test

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Reviewer checklist and capture skill

**Files:**
- Create: `templates/reviewer-checklist.md`
- Create: `skills/capture/SKILL.md`

**Interfaces:**
- Consumes: entity templates (`templates/entities/*.md`), schema (`docs/schema.md`), validate CLI (Task 5).
- Produces: `templates/reviewer-checklist.md` — referenced by BOTH capture and bootstrap (Task 9) via `${CLAUDE_PLUGIN_ROOT}/templates/reviewer-checklist.md`.

- [ ] **Step 1: Create `templates/reviewer-checklist.md`**

```markdown
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
```

- [ ] **Step 2: Create `skills/capture/SKILL.md`**

```markdown
---
name: capture
description: Use when the user wants to log career knowledge - a project, accomplishment, new role, publication, education, STAR story, or job application - into their career-data repo through a guided interview
---

# Capture — guided career entry

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
   `${CLAUDE_PLUGIN_ROOT}/templates/entities/`, fill it in. Slug rules: lowercase,
   hyphens, short (`proj-career-flow`). Filename = id. Put the user's original words
   verbatim under `## Raw notes`.
4. **Update cross-links.** Add skill ids to `links.skills`; CREATE any missing skill
   files from the skill template (brief summary is enough). If updating an existing
   entity, bump its `last_verified` to today.
5. **Reviewer pass.** Work through `${CLAUDE_PLUGIN_ROOT}/templates/reviewer-checklist.md`.
   Show the user the final draft and get their OK.
6. **Triage inbox (quick).** If `data/inbox.md` has unchecked items, ask whether to
   handle any now; promote or delete per the user's answer.
7. **Validate.** Run `${CLAUDE_PLUGIN_ROOT}/scripts/validate.py .` — fix every ERROR
   and rerun until it prints OK (this also regenerates INDEX.md).
8. **Commit and push.** `git add -A && git commit` with a message like
   `capture: add proj-career-flow` then `git push`.

## Rules

- Never invent metrics or embellish — everything must come from the user.
- Never delete or rewrite existing `## Raw notes` content.
- Never hand-edit `data/INDEX.md`.
```

- [ ] **Step 3: Verify skill frontmatter parses and required fields exist**

Run:
```bash
uv run --with pyyaml python3 -c "
import yaml
fm = yaml.safe_load(open('skills/capture/SKILL.md').read().split('---')[1])
assert fm['name'] == 'capture' and fm['description'], fm
print('capture skill ok')
"
```
Expected: `capture skill ok`.

- [ ] **Step 4: Commit**

```bash
git add templates/reviewer-checklist.md skills/capture
git commit -m "feat: capture skill and shared reviewer checklist

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: Bootstrap skill

**Files:**
- Create: `skills/bootstrap/SKILL.md`

**Interfaces:**
- Consumes: scaffold `templates/data-repo/` (Task 6), entity templates + reviewer checklist (Tasks 2, 8), validate CLI (Task 5), `gh` CLI.
- Produces: a scaffolded private data repo; `~/.config/career-flow/config` containing `data_repo: <absolute path>` (YAML) — the pointer the capture skill (Task 8) reads.

- [ ] **Step 1: Create `skills/bootstrap/SKILL.md`**

```markdown
---
name: bootstrap
description: Use when setting up career-flow for the first time - scaffolds the user's private career-data repo, connects it to GitHub, and imports their existing resume/CV through a guided gap interview
---

# Bootstrap — create and seed the career-data repo

## Guard

If `~/.config/career-flow/config` already exists and points at a valid data repo, tell
the user bootstrap has already run (offer capture instead) and STOP unless they
explicitly want a second repo.

## Part 1 — scaffold the repo

1. Ask where the data repo should live. Default: `~/Projects/career-data`.
2. Copy the scaffold: `cp -R ${CLAUDE_PLUGIN_ROOT}/templates/data-repo <chosen-path>`.
3. Replace placeholders in `<path>/config.yaml` and `<path>/.github/workflows/validate.yml`:
   - `{{PLUGIN_REPO}}` → the plugin's GitHub `owner/name` (derive from
     `git -C ${CLAUDE_PLUGIN_ROOT} remote get-url origin`; if no remote, ask the user).
   - `{{PLUGIN_LOCAL_PATH}}` → absolute path of `${CLAUDE_PLUGIN_ROOT}`.
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
   `${CLAUDE_PLUGIN_ROOT}/templates/entities/`:
   experiences, education, publications, obvious major projects, and skill files for
   the skills those entries reference. Filename = id; original resume wording goes in
   `## Raw notes` verbatim.
4. **Gap interview, one question at a time, newest experiences first:** missing
   metrics, missing dates, notable projects the resume undersells, story-worthy
   moments (offer to create story entities). Apply
   `${CLAUDE_PLUGIN_ROOT}/templates/reviewer-checklist.md` to every entry; use
   `flags: [needs-metrics]` where the user can't supply numbers — bootstrap should be
   thorough but not exhausting; the maintain flow revisits flagged entries later.
5. Set every imported entry's `last_verified` to today.

## Part 3 — validate and push

1. Run `${CLAUDE_PLUGIN_ROOT}/scripts/validate.py <data-repo-path>` — fix every ERROR
   and rerun until OK.
2. Review WARN lines (orphan skills are fine at this stage if the user wants them kept).
3. `git add -A && git commit -m "bootstrap: import initial career knowledge base"` and push.
4. Summarize for the user: entity counts by type, entries flagged needs-metrics, and
   suggested next step (use the capture skill as things happen).

## Rules

- Never invent facts, dates, or metrics not provided by the user or their documents.
- Ask before creating the GitHub repo or pushing (outward-facing actions).
- All imported entries default to `visibility: private`.
```

- [ ] **Step 2: Verify skill frontmatter**

Run:
```bash
uv run --with pyyaml python3 -c "
import yaml
fm = yaml.safe_load(open('skills/bootstrap/SKILL.md').read().split('---')[1])
assert fm['name'] == 'bootstrap' and fm['description'], fm
print('bootstrap skill ok')
"
```
Expected: `bootstrap skill ok`.

- [ ] **Step 3: Dry-run the scaffold procedure manually (no GitHub)**

Run:
```bash
cp -R templates/data-repo /tmp/cf-dryrun \
  && sed -i '' 's|{{PLUGIN_REPO}}|bornabarahimi/career-flow|; s|{{PLUGIN_LOCAL_PATH}}|/Users/bornabarahimi/Projects/career-flow|' /tmp/cf-dryrun/config.yaml \
  && ./scripts/validate.py /tmp/cf-dryrun \
  && uv run --with pyyaml python3 -c "import yaml; c=yaml.safe_load(open('/tmp/cf-dryrun/config.yaml')); assert c['plugin']['repo']=='bornabarahimi/career-flow'; print('placeholders ok')" \
  && rm -rf /tmp/cf-dryrun
```
Expected: `OK: 0 entities...` then `placeholders ok`.

- [ ] **Step 4: Commit**

```bash
git add skills/bootstrap
git commit -m "feat: bootstrap skill

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 10: Install plugin locally and hand off to acceptance testing

**Files:**
- None created (verification task).

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Full test suite green**

Run: `uv run --with pyyaml --with pytest -- pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 2: Register this repo as a local marketplace and install**

Run: `claude plugin marketplace add /Users/bornabarahimi/Projects/career-flow && claude plugin install career-flow@career-flow-marketplace`
Expected: both commands succeed. If the CLI syntax differs in the installed version, check `claude plugin --help` and adapt — the goal is: plugin installed from this directory.

- [ ] **Step 3: Verify the skills are visible**

Run: `claude plugin list 2>/dev/null || claude plugin --help`
Expected: `career-flow` listed/installed. In a fresh interactive session the skills should appear as `career-flow:bootstrap` and `career-flow:capture`.

- [ ] **Step 4: Report and hand off — user acceptance (spec requirement)**

Per the spec's verification section, Phase 1 acceptance is Borna running the real flows:
1. In a fresh Claude Code session, invoke `career-flow:bootstrap` with a real resume.
2. Confirm: private data repo created on GitHub, entities look right, INDEX.md reads
   well, gap interview felt reasonable, validate passes.
3. Invoke `career-flow:capture` to log one new real project.
4. Give feedback; fixes land before Phase 2 begins.

Report to the user exactly what was built, the test results, and these acceptance steps. Do NOT start Phase 2.
