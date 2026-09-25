#!/usr/bin/env python3
"""Check a resume PDF's text, section order, required terms, and embedded links.

Usage: check_resume.py PDF [--section HEADING]... [--keyword TERM]... [--url URL]... [--json PATH]
Exit codes: 0 pass, 1 content check failed, 2 PDF/tool/input error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def extract_text(pdf: Path) -> str:
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        raise ValueError(f"PDF does not exist: {pdf}")
    try:
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True)
        result = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", str(pdf), "-"],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"required Poppler tool not installed: {exc.filename}") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"PDF could not be parsed: {exc.stderr.strip()}") from exc
    if not re.search(r"(?m)^Pages:\s*[1-9]\d*\s*$", info.stdout):
        raise ValueError("PDF has no readable page count")
    if not result.stdout.strip():
        raise ValueError("PDF contains no extractable text")
    return result.stdout


def extract_urls(pdf: Path) -> set[str]:
    try:
        result = subprocess.run(["pdfinfo", "-url", str(pdf)], capture_output=True,
                                text=True, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"required Poppler tool not installed: {exc.filename}") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"PDF links could not be inspected: {exc.stderr.strip()}") from exc
    return {match.group(1) for line in result.stdout.splitlines()
            if (match := re.search(r"\b(https?://\S+)\s*$", line))}


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def check_text(text: str, sections: list[str], keywords: list[str]) -> dict:
    lines = [normalize(line) for line in text.splitlines()]
    positions: list[int] = []
    missing_sections: list[str] = []
    for section in sections:
        heading = normalize(section)
        if not heading:
            missing_sections.append(section)
            continue
        try:
            positions.append(lines.index(heading))
        except ValueError:
            missing_sections.append(section)
    order_ok = positions == sorted(positions) and len(positions) == len(set(positions))
    normalized_text = normalize(text)
    missing_keywords = [term for term in keywords if normalize(term) not in normalized_text]
    return {
        "pass": not missing_sections and order_ok and not missing_keywords,
        "sections_checked": len(sections),
        "keywords_checked": len(keywords),
        "missing_sections": missing_sections,
        "section_order_ok": order_ok,
        "missing_keywords": missing_keywords,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--section", action="append", default=[], help="expected visible heading, in order")
    parser.add_argument("--keyword", action="append", default=[], help="required posting term")
    parser.add_argument("--url", action="append", default=[], help="expected clickable PDF destination")
    parser.add_argument("--json", type=Path, help="write a machine-readable check report")
    args = parser.parse_args(argv)
    try:
        report = check_text(extract_text(args.pdf), args.section, args.keyword)
        missing_urls = [url for url in args.url if url not in extract_urls(args.pdf)]
        report["urls_checked"] = len(args.url)
        report["missing_urls"] = missing_urls
        report["pass"] = report["pass"] and not missing_urls
        code = 0 if report["pass"] else 1
    except (ValueError, RuntimeError) as exc:
        report = {"pass": False, "error": str(exc)}
        code = 2
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
