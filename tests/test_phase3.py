import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import passive_capture as passive  # noqa: E402
import phase3_status as phase3  # noqa: E402
import validate as validator  # noqa: E402


@pytest.fixture
def repo(tmp_path):
    target = tmp_path / "career-data"
    shutil.copytree(ROOT / "templates" / "data-repo", target)
    return target


def configure_passive(repo, *, enabled=True, sources="github", repos="[]", projects="[]"):
    path = repo / "config.yaml"
    content = path.read_text()
    content = content.replace("enabled: false", f"enabled: {'true' if enabled else 'false'}")
    content = content.replace("sources: [github, claude_sessions]", f"sources: [{sources}]")
    content = content.replace("github_repos: []", f"github_repos: {repos}")
    content = content.replace("session_projects: []", f"session_projects: {projects}")
    path.write_text(content)


def test_status_reports_due_stale_and_flags_without_writing(repo):
    (repo / "data" / "skills" / "skill-python.md").write_text("""---
id: skill-python
type: skill
title: Python
summary: Primary language
status: active
visibility: private
last_verified: 2025-12-01
flags: [needs-metrics]
---
# Narrative
Used Python.

## Raw notes
Python.
""")
    (repo / "data" / "inbox.md").write_text("# Inbox\n\n- [ ] 2026-09-01 github: review\n")
    (repo / "data" / "INDEX.md").write_text("old index\n")
    before = {p: p.read_bytes() for p in (repo / "data").rglob("*.md")}
    result = phase3.status(repo, dt.date(2026, 10, 2))
    assert result["checkin_due"] is True
    assert result["last_checkin"] is None
    assert result["pending_inbox"] == 1
    assert result["stale_entries"] == [{"id": "skill-python", "last_verified": "2025-12-01"}]
    assert result["needs_metrics"] == ["skill-python"]
    assert result["index_current"] is False
    assert before == {p: p.read_bytes() for p in (repo / "data").rglob("*.md")}


def test_status_respects_checkin_interval_and_surfaces_invalid_entity(repo):
    (repo / "data" / "checkins" / "2026-09-25.md").write_text("# Approved check-in\n")
    current = phase3.status(repo, dt.date(2026, 10, 2))
    assert current["checkin_due"] is False
    assert current["next_checkin"] == "2026-10-09"
    (repo / "data" / "skills" / "skill-bad.md").write_text("""---
id: skill-bad
type: skill
summary: Incomplete
status: active
visibility: private
last_verified: 2026-10-01
---
# Narrative
Incomplete.

## Raw notes
Original.
""")
    report = phase3.status(repo, dt.date(2026, 10, 2))
    assert any("missing required field 'title'" in error for error in report["schema_errors"])
    assert report["index_current"] is False


def test_status_surfaces_invalid_calendar_date(repo):
    (repo / "data" / "skills" / "skill-bad.md").write_text("""---
id: skill-bad
type: skill
title: Bad date
summary: Date needs repair
status: active
visibility: private
last_verified: "2026-02-30"
---
# Narrative
Incomplete.

## Raw notes
Original.
""")
    report = phase3.status(repo, dt.date(2026, 10, 2))
    assert any("last_verified must be a valid" in error for error in report["schema_errors"])
    path = repo / "data" / "skills" / "skill-bad.md"
    path.write_text(path.read_text().replace('"2026-02-30"', "2026-02-30"))
    report = phase3.status(repo, dt.date(2026, 10, 2))
    assert any("invalid YAML in frontmatter" in error for error in report["schema_errors"])


def test_duplicate_titles_are_review_candidates_not_merges():
    entities = {
        "skill-ml": {"id": "skill-ml", "type": "skill", "title": "Machine Learning"},
        "skill-ml-alt": {"id": "skill-ml-alt", "type": "skill", "title": "Machine-Learning"},
    }
    assert phase3.duplicate_candidates(entities) == [
        {"first": "skill-ml", "second": "skill-ml-alt", "title_similarity": 1.0}
    ]


def test_passive_capture_is_disabled_and_requires_allowlist(repo, monkeypatch):
    monkeypatch.setattr(passive, "_github_query", lambda *_: pytest.fail("should not query"))
    assert passive.scan_github(repo, dt.date(2026, 10, 2)) == 0
    monkeypatch.setattr(passive, "_user_texts", lambda *_: pytest.fail("should not read transcript"))
    assert passive.capture_session({"hook_event_name": "SessionEnd", "cwd": str(repo),
                                    "transcript_path": "/private/example.jsonl"}, repo) == 0
    assert not (repo / "data" / "passive-state.json").exists()
    configure_passive(repo, repos="[]")
    with pytest.raises(ValueError, match="github_repos"):
        passive.scan_github(repo, dt.date(2026, 10, 2))
    assert not (repo / "data" / "passive-state.json").exists()


def test_github_scan_adds_only_allowlisted_pr_once(repo, monkeypatch):
    configure_passive(repo, repos="[example/work]")
    calls = []

    def fake_query(name, since):
        calls.append((name, since))
        return {"total_count": 2, "items": [
            {"html_url": "https://github.com/example/work/pull/12",
             "title": "Shipped monitoring", "closed_at": "2026-10-01T12:00:00Z"},
            {"html_url": "https://github.com/other/work/pull/99",
             "title": "Not allowlisted", "closed_at": "2026-10-01T12:00:00Z"},
        ]}

    monkeypatch.setattr(passive, "_github_query", fake_query)
    assert passive.scan_github(repo, dt.date(2026, 10, 2)) == 1
    assert passive.scan_github(repo, dt.date(2026, 10, 2)) == 0
    inbox = (repo / "data" / "inbox.md").read_text()
    assert inbox.count("Shipped monitoring") == 1
    assert "Not allowlisted" not in inbox
    assert calls[0] == ("example/work", dt.date(2026, 9, 18))
    assert calls[1] == ("example/work", dt.date(2026, 10, 2))


def test_stale_passive_state_updates_preserve_other_source_checkpoints(repo):
    first = {"github_last_scan": {"example/one": "2026-10-02"}, "session_ids": []}
    second = {"github_last_scan": {}, "session_ids": ["session-two"]}
    older = {"github_last_scan": {"example/one": "2026-09-01"}, "session_ids": []}
    assert passive._record(repo, [], first) == 0
    assert passive._record(repo, [], second) == 0
    assert passive._record(repo, [], older) == 0
    state = json.loads((repo / "data" / "passive-state.json").read_text())
    assert state["github_last_scan"] == {"example/one": "2026-10-02"}
    assert state["session_ids"] == ["session-two"]


def test_session_hook_requires_project_allowlist_and_copies_no_transcript(repo, tmp_path):
    project = tmp_path / "allowed-project"
    project.mkdir()
    other = tmp_path / "other-project"
    other.mkdir()
    configure_passive(repo, sources="claude_sessions", projects=f"['{project}']")
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"type": "user", "message": {
        "content": "We shipped monitoring for confidential customer Acme."}}) + "\n")
    payload = {"hook_event_name": "SessionEnd", "session_id": "abc-123",
               "cwd": str(other), "transcript_path": str(transcript)}
    assert passive.capture_session(payload, repo) == 0
    payload["cwd"] = str(project)
    assert passive.capture_session(payload, repo) == 1
    assert passive.capture_session(payload, repo) == 0
    inbox = (repo / "data" / "inbox.md").read_text()
    assert "possible delivery, reliability work" in inbox
    assert "confidential customer Acme" not in inbox
    assert inbox.count("career-flow-session:abc-123") == 1


def test_session_allowlist_rejects_broad_or_relative_roots(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    assert not passive._allowed_session_project(project, ["/"])
    assert not passive._allowed_session_project(project, ["project"])
    assert passive._allowed_session_project(project, [str(project)])


def test_session_reader_ignores_malformed_transcript_records(tmp_path):
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("null\n" + json.dumps({"type": "user", "message": "bad"}) +
                          "\n" + json.dumps({"type": "user", "message": {
                              "content": "I shipped an experiment."}}) + "\n")
    assert passive._user_texts(transcript) == ["I shipped an experiment."]


def test_session_hook_command_uses_pointer_without_yaml_dependency(repo, tmp_path):
    project = tmp_path / "work-project"
    project.mkdir()
    configure_passive(repo, sources="claude_sessions", projects=f"['{project}']")
    pointer = tmp_path / "career-flow-pointer"
    pointer.write_text(f"data_repo: {repo}\n")
    transcript = tmp_path / "claude.jsonl"
    transcript.write_text(json.dumps({"type": "user", "message": {
        "content": [{"type": "text", "text": "I deployed a monitoring model."}]}}) + "\n")
    payload = {"hook_event_name": "SessionEnd", "session_id": "cli-1",
               "cwd": str(project), "transcript_path": str(transcript)}
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "passive_capture.py"), "session-hook"],
        input=json.dumps(payload), capture_output=True, text=True,
        env={**os.environ, "CAREER_FLOW_CONFIG": str(pointer)}, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "career-flow-session:cli-1" in (repo / "data" / "inbox.md").read_text()


def test_phase3_skills_and_hook_are_discoverable():
    for name in ("checkin", "maintain"):
        path = ROOT / "skills" / name / "SKILL.md"
        text = path.read_text()
        assert text.startswith("---\n")
        fm = yaml.safe_load(text[4:text.find("\n---", 4)])
        assert fm["name"] == name and fm["description"]
    hook = json.loads((ROOT / "hooks" / "hooks.json").read_text())
    command = hook["hooks"]["SessionEnd"][0]["hooks"][0]
    assert command["command"] == "python3"
    assert "passive_capture.py" in command["args"][0]
