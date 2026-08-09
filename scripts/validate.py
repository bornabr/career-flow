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
