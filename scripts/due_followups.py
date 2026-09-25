#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""List due, unfinished application follow-ups without changing the data repo."""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import yaml


def due_items(repo: Path, as_of: dt.date) -> list[tuple[dt.date, str, str, str, str]]:
    directory = repo / "data" / "applications"
    if not directory.is_dir():
        raise ValueError(f"application directory not found: {directory}")
    results = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text()
        if not text.startswith("---\n") or "\n---" not in text[4:]:
            raise ValueError(f"invalid frontmatter: {path}")
        fm = yaml.safe_load(text[4:text.find("\n---", 4)])
        if not isinstance(fm, dict):
            raise ValueError(f"invalid frontmatter: {path}")
        if fm.get("status") != "active":
            continue
        for item in fm.get("follow_ups") or []:
            if not isinstance(item, dict) or not isinstance(item.get("done"), bool):
                raise ValueError(f"invalid follow_up in {path}; run validate.py")
            raw_date = item.get("date")
            try:
                date = raw_date if isinstance(raw_date, dt.date) else dt.date.fromisoformat(raw_date)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid follow_up date in {path}; run validate.py") from exc
            if not item["done"] and date <= as_of:
                results.append((date, str(fm.get("id", path.stem)), str(fm.get("company", "")),
                                str(fm.get("role", "")), str(item.get("note", ""))))
    return sorted(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path, help="career-data repo root")
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.date.today())
    args = parser.parse_args(argv)
    try:
        items = due_items(args.repo, args.as_of)
    except (ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for date, eid, company, role, note in items:
        print(f"{date.isoformat()}\t{eid}\t{company}\t{role}\t{note}")
    if not items:
        print("No follow-ups due.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
