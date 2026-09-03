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
