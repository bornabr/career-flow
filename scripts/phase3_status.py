#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Read-only check-in and maintenance report for a private career-data repo."""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import difflib
import json
import re
import sys
from pathlib import Path

import yaml

from validate import build_index, check_links, load_entities


def months_ago(day: dt.date, count: int) -> dt.date:
    month_index = day.year * 12 + day.month - 1 - count
    year, zero_month = divmod(month_index, 12)
    month = zero_month + 1
    return dt.date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def latest_checkin(repo: Path) -> dt.date | None:
    directory = repo / "data" / "checkins"
    if not directory.is_dir():
        return None
    dates = []
    for path in directory.glob("*.md"):
        try:
            dates.append(dt.date.fromisoformat(path.stem))
        except ValueError:
            continue
    return max(dates, default=None)


def duplicate_candidates(entities: dict[str, dict]) -> list[dict[str, str]]:
    results = []
    for kind in ("skill", "story"):
        group = sorted((e for e in entities.values() if e.get("type") == kind
                        and isinstance(e.get("title"), str)),
                       key=lambda e: e["id"])
        for index, left in enumerate(group):
            for right in group[index + 1:]:
                first = re.sub(r"[^a-z0-9]+", " ", left["title"].lower()).strip()
                second = re.sub(r"[^a-z0-9]+", " ", right["title"].lower()).strip()
                score = difflib.SequenceMatcher(None, first, second).ratio()
                if score >= 0.84:
                    results.append({"first": left["id"], "second": right["id"],
                                    "title_similarity": round(score, 2)})
    return results


def status(repo: Path, as_of: dt.date) -> dict:
    config_path = repo / "config.yaml"
    data_dir = repo / "data"
    if not config_path.is_file() or not data_dir.is_dir():
        raise ValueError("expected a career-data repo with config.yaml and data/")
    config = yaml.safe_load(config_path.read_text()) or {}
    if not isinstance(config, dict):
        raise ValueError("config.yaml must contain a mapping")
    capture = config.get("capture") or {}
    memory = config.get("memory") or {}
    if not isinstance(capture, dict) or not isinstance(memory, dict):
        raise ValueError("capture and memory config must be mappings")
    interval = capture.get("checkin_interval_days", 14)
    staleness_months = memory.get("staleness_months", 6)
    if type(interval) is not int or interval < 1:
        raise ValueError("capture.checkin_interval_days must be a positive integer")
    if type(staleness_months) is not int or staleness_months < 1:
        raise ValueError("memory.staleness_months must be a positive integer")

    entities, schema_errors = load_entities(data_dir)
    link_errors, link_warnings = check_links(entities)
    last = latest_checkin(repo)
    cutoff = months_ago(as_of, staleness_months)
    stale = []
    flagged = []
    for entity in entities.values():
        verified = entity.get("last_verified")
        try:
            verified_date = (verified if isinstance(verified, dt.date)
                             else dt.date.fromisoformat(str(verified)))
        except ValueError:
            continue  # schema_errors already reports malformed dates
        if verified_date < cutoff:
            stale.append({"id": entity["id"], "last_verified": verified_date.isoformat()})
        if "needs-metrics" in (entity.get("flags") or []):
            flagged.append(entity["id"])
    index_path = data_dir / "INDEX.md"
    index_current = (not schema_errors and index_path.is_file()
                     and index_path.read_text() == build_index(entities))
    inbox_path = data_dir / "inbox.md"
    inbox = inbox_path.read_text() if inbox_path.is_file() else ""
    pending = sum(1 for line in inbox.splitlines() if re.match(r"^\s*- \[ \] ", line))
    due_date = last + dt.timedelta(days=interval) if last else None
    return {
        "as_of": as_of.isoformat(),
        "last_checkin": last.isoformat() if last else None,
        "checkin_due": due_date is None or as_of >= due_date,
        "next_checkin": due_date.isoformat() if due_date else None,
        "pending_inbox": pending,
        "staleness_cutoff": cutoff.isoformat(),
        "stale_entries": sorted(stale, key=lambda item: item["id"]),
        "needs_metrics": sorted(flagged),
        "duplicate_candidates": duplicate_candidates(entities),
        "schema_errors": schema_errors,
        "link_errors": link_errors,
        "link_warnings": link_warnings,
        "index_current": index_current,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path, help="career-data repo root")
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.date.today())
    parser.add_argument("--json", action="store_true", help="print machine-readable report")
    args = parser.parse_args(argv)
    try:
        report = status(args.repo, args.as_of)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Check-in due: {'yes' if report['checkin_due'] else 'no'} "
              f"(last: {report['last_checkin'] or 'none'}, "
              f"next: {report['next_checkin'] or 'now'})")
        print(f"Inbox candidates: {report['pending_inbox']}")
        print(f"Stale entries: {len(report['stale_entries'])}; "
              f"needs-metrics: {len(report['needs_metrics'])}; "
              f"possible duplicates: {len(report['duplicate_candidates'])}")
        print(f"Schema/link errors: {len(report['schema_errors']) + len(report['link_errors'])}; "
              f"index current: {'yes' if report['index_current'] else 'no'}")
        for key in ("stale_entries", "needs_metrics", "duplicate_candidates",
                    "schema_errors", "link_errors", "link_warnings"):
            for item in report[key]:
                print(f"{key}: {item}")
    return 1 if report["schema_errors"] or report["link_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
