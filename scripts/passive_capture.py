#!/usr/bin/env python3
"""Opt-in, review-only career candidate capture from GitHub or Claude sessions.

No source is scanned unless capture.passive.enabled and the source-specific allowlist
are set in the private data repo's config.yaml. Candidates go only to data/inbox.md.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None
try:
    import msvcrt
except ImportError:
    msvcrt = None


def _list_value(raw: str) -> list[str]:
    raw = raw.strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        raise ValueError("passive list settings must use [item, item] syntax")
    return [part.strip().strip("\"'") for part in raw[1:-1].split(",") if part.strip()]


def passive_settings(repo: Path) -> dict:
    """Parse only the small, security-relevant YAML subset; fail closed otherwise.

    This intentionally uses the stdlib so a short SessionEnd hook needs no package
    installation. The supported config syntax is documented in the scaffold.
    """
    path = repo / "config.yaml"
    if not path.is_file():
        raise ValueError("career-data config.yaml not found")
    section = None
    values: dict[str, object] = {}
    for original in path.read_text().splitlines():
        line = original.split(" #", 1)[0].rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0:
            section = "capture" if stripped == "capture:" else None
        elif indent == 2 and section == "capture":
            section = "passive" if stripped == "passive:" else "capture"
        elif indent == 4 and section == "passive":
            match = re.fullmatch(r"([a-z_]+):\s*(.*)", stripped)
            if not match:
                raise ValueError("unsupported capture.passive config syntax")
            key, raw = match.groups()
            if key == "enabled":
                if raw not in ("true", "false"):
                    raise ValueError("capture.passive.enabled must be true or false")
                values[key] = raw == "true"
            elif key in ("sources", "github_repos", "session_projects"):
                values[key] = _list_value(raw)
            elif key == "github_lookback_days":
                if not raw.isdecimal() or int(raw) < 1:
                    raise ValueError("github_lookback_days must be positive")
                values[key] = int(raw)
    return {
        "enabled": values.get("enabled") is True,
        "sources": values.get("sources", []),
        "github_repos": values.get("github_repos", []),
        "session_projects": values.get("session_projects", []),
        "github_lookback_days": values.get("github_lookback_days", 14),
    }


def _state_path(repo: Path) -> Path:
    return repo / "data" / "passive-state.json"


def _read_state(repo: Path) -> dict:
    path = _state_path(repo)
    if not path.exists():
        return {"github_last_scan": {}, "session_ids": []}
    state = json.loads(path.read_text())
    if not isinstance(state, dict) or not isinstance(state.get("github_last_scan"), dict) \
            or not isinstance(state.get("session_ids"), list):
        raise ValueError("data/passive-state.json is malformed")
    return state


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(content)
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()


@contextlib.contextmanager
def _capture_lock(repo: Path):
    if fcntl is None and msvcrt is None:
        raise ValueError("passive capture needs OS file locking")
    digest = hashlib.sha256(str(repo.resolve()).encode()).hexdigest()[:20]
    path = Path(tempfile.gettempdir()) / f"career-flow-{digest}.lock"
    with path.open("a+b") as handle:
        if fcntl is not None:
            fcntl.flock(handle, fcntl.LOCK_EX)
        else:
            if path.stat().st_size == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle, fcntl.LOCK_UN)
            else:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _record(repo: Path, candidates: list[tuple[str, str]], state: dict) -> int:
    inbox = repo / "data" / "inbox.md"
    if not inbox.is_file():
        raise ValueError("data/inbox.md not found")
    with _capture_lock(repo):
        content = inbox.read_text()
        added = 0
        for marker, line in candidates:
            if marker in content:
                continue
            content += ("" if content.endswith("\n") else "\n") + line + "\n"
            added += 1
        if added:
            _atomic_write(inbox, content)
        latest = _read_state(repo)
        for name, date_value in state["github_last_scan"].items():
            if date_value >= latest["github_last_scan"].get(name, ""):
                latest["github_last_scan"][name] = date_value
        latest["session_ids"] = list(dict.fromkeys(
            latest["session_ids"] + state["session_ids"]))[-1000:]
        _atomic_write(_state_path(repo), json.dumps(latest, indent=2, sort_keys=True) + "\n")
        return added


def _safe_title(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()[:160]
    return value.replace("[", "(").replace("]", ")").replace("<", "(").replace(">", ")")


def _github_query(repo_name: str, since: dt.date) -> dict:
    query = f"repo:{repo_name} is:pr is:merged author:@me merged:>={since.isoformat()}"
    try:
        result = subprocess.run(
            ["gh", "api", "-X", "GET", "search/issues", "-f", f"q={query}", "-f", "per_page=100"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise ValueError("GitHub scan needs an authenticated gh CLI and a responsive connection") from exc
    if result.returncode:
        raise ValueError(f"GitHub query failed for {repo_name}; check gh auth and repository access")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("GitHub returned invalid JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("GitHub search response is malformed")
    if type(payload.get("total_count")) is not int:
        raise ValueError("GitHub search response has no valid result count")
    if payload["total_count"] > len(payload["items"]):
        raise ValueError(f"GitHub search for {repo_name} exceeded one page; narrow the scan window")
    return payload


def scan_github(repo: Path, as_of: dt.date | None = None) -> int:
    settings = passive_settings(repo)
    if not settings["enabled"] or "github" not in settings["sources"]:
        return 0
    repos = settings["github_repos"]
    if not repos:
        raise ValueError("set capture.passive.github_repos explicitly before GitHub scanning")
    for name in repos:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
            raise ValueError(f"invalid allowlisted GitHub repository: {name}")
    as_of = as_of or dt.date.today()
    state = _read_state(repo)
    candidates = []
    updates = {}
    for name in repos:
        raw_last = state["github_last_scan"].get(name)
        since = dt.date.fromisoformat(raw_last) if raw_last else as_of - dt.timedelta(
            days=settings["github_lookback_days"])
        payload = _github_query(name, since)
        for item in payload["items"]:
            if not isinstance(item, dict):
                continue
            url = item.get("html_url", "")
            if not isinstance(url, str) or not re.fullmatch(
                    rf"https://github\.com/{re.escape(name)}/pull/[0-9]+", url):
                continue
            title = _safe_title(str(item.get("title", "")))
            if not title:
                continue
            closed = str(item.get("closed_at", ""))[:10]
            try:
                merged_date = dt.date.fromisoformat(closed)
            except ValueError:
                continue
            if merged_date > as_of:
                continue
            marker = f"career-flow-pr:{url}"
            line = (f"- [ ] {merged_date.isoformat()} github {name}: {title} "
                    f"[PR]({url}) <!-- {marker} -->")
            candidates.append((marker, line))
        updates[name] = as_of.isoformat()
    state["github_last_scan"].update(updates)
    return _record(repo, candidates, state)


TOPICS = {
    "delivery": r"\b(shipped|deployed|launched|released|delivered)\b",
    "research": r"\b(research|published|paper|experiment|model)\b",
    "leadership": r"\b(led|mentored|coordinated|owned)\b",
    "reliability": r"\b(fixed|debugged|incident|migration|monitoring)\b",
}


def _user_texts(transcript: Path) -> list[str]:
    if not transcript.is_file() or transcript.suffix != ".jsonl":
        return []
    with transcript.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(max(0, size - 1_000_000))
        data = stream.read().decode("utf-8", errors="replace")
    lines = data.splitlines()[1:] if size > 1_000_000 else data.splitlines()
    texts = []
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "user":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content", "")
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            texts.extend(part.get("text", "") for part in content
                         if isinstance(part, dict) and part.get("type") == "text")
    return texts


def _data_repo_from_pointer() -> Path | None:
    override = os.environ.get("CAREER_FLOW_CONFIG")
    path = Path(override) if override else Path.home() / ".config" / "career-flow" / "config"
    if not path.is_file():
        return None
    for line in path.read_text().splitlines():
        if line.startswith("data_repo:"):
            value = line.partition(":")[2].strip().strip("\"'")
            return Path(value).expanduser() if value else None
    return None


def _allowed_session_project(workdir: Path, entries: list[str]) -> bool:
    for item in entries:
        configured = Path(item).expanduser()
        if not configured.is_absolute():
            continue
        root = configured.resolve()
        if root in (Path("/"), Path.home().resolve()):
            continue  # broad roots are not meaningful consent to scan sessions
        if workdir == root or workdir.is_relative_to(root):
            return True
    return False


def capture_session(payload: dict, repo: Path) -> int:
    settings = passive_settings(repo)
    if not settings["enabled"] or "claude_sessions" not in settings["sources"]:
        return 0
    if not isinstance(payload, dict):
        return 0
    if payload.get("hook_event_name") != "SessionEnd":
        return 0
    workdir = payload.get("cwd")
    allowed = settings["session_projects"]
    if not isinstance(workdir, str) or not allowed:
        return 0
    current = Path(workdir).resolve()
    if not _allowed_session_project(current, allowed):
        return 0
    raw_path = payload.get("transcript_path")
    if not isinstance(raw_path, str):
        return 0
    transcript = Path(raw_path)
    texts = _user_texts(transcript)
    topics = sorted(name for name, pattern in TOPICS.items()
                    if any(re.search(pattern, text, re.IGNORECASE) for text in texts))
    if not topics:
        return 0
    raw_id = str(payload.get("session_id", ""))
    session_id = re.sub(r"[^A-Za-z0-9_-]", "", raw_id)[:80]
    if not session_id:
        session_id = hashlib.sha256(str(transcript).encode()).hexdigest()[:16]
    state = _read_state(repo)
    if session_id in state["session_ids"]:
        return 0
    state["session_ids"] = (state["session_ids"] + [session_id])[-1000:]
    marker = f"career-flow-session:{session_id}"
    line = (f"- [ ] {dt.date.today().isoformat()} claude-session {current.name}: "
            f"Review session {session_id} for possible {', '.join(topics)} work; "
            f"no transcript text copied. <!-- {marker} -->")
    return _record(repo, [(marker, line)], state)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    github = sub.add_parser("github", help="scan explicitly allowlisted merged PRs")
    github.add_argument("repo", type=Path, help="career-data repo root")
    github.add_argument("--as-of", type=dt.date.fromisoformat, default=None)
    sub.add_parser("session-hook", help="read a Claude SessionEnd JSON payload from stdin")
    args = parser.parse_args(argv)
    try:
        if args.command == "github":
            added = scan_github(args.repo, args.as_of)
        else:
            repo = _data_repo_from_pointer()
            if repo is None:
                return 0
            added = capture_session(json.load(sys.stdin), repo)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"career-flow passive capture: {exc}", file=sys.stderr)
        return 2
    if args.command == "github":
        print(f"Added {added} review candidate(s) to data/inbox.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
