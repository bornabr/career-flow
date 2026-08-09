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
