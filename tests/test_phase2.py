import datetime as dt
import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ats = load_module("check_resume", "scripts/check_resume.py")
followups = load_module("due_followups", "scripts/due_followups.py")


def test_ats_text_checks_section_order_and_required_terms():
    text = "Alex Example\nSummary\nPython engineer\nExperience\nData quality\nSkills\nPython\n"
    assert ats.check_text(text, ["Summary", "Experience", "Skills"], ["Python", "Data quality"])["pass"]
    general = ats.check_text(text, ["Summary", "Experience", "Skills"], [])
    assert general["pass"] and general["keywords_checked"] == 0
    assert general["sections_checked"] == 3
    report = ats.check_text(text, ["Experience", "Summary", "Education"], ["Python", "Kubernetes"])
    assert report["section_order_ok"] is False
    assert report["missing_sections"] == ["Education"]
    assert report["missing_keywords"] == ["Kubernetes"]


def test_due_followups_only_active_unfinished_and_due(tmp_path):
    applications = tmp_path / "data" / "applications"
    applications.mkdir(parents=True)
    (applications / "app-one.md").write_text("""---
id: app-one
company: Acme
role: Engineer
status: active
follow_ups:
  - {date: 2026-09-20, note: First nudge, done: false}
  - {date: 2026-09-21, note: Already done, done: true}
  - {date: 2026-10-01, note: Later, done: false}
---
""")
    (applications / "app-two.md").write_text("""---
id: app-two
company: Other
role: Engineer
status: archived
follow_ups:
  - {date: 2026-09-01, note: Old, done: false}
---
""")
    items = followups.due_items(tmp_path, dt.date(2026, 9, 25))
    assert items == [(dt.date(2026, 9, 20), "app-one", "Acme", "Engineer", "First nudge")]


def test_application_fields_are_validated(vmod):
    base = {
        "id": "app-acme", "type": "application", "title": "Engineer @ Acme",
        "summary": "Applied for engineering role", "company": "Acme", "role": "Engineer",
        "date": "2026-09-25", "status": "active", "visibility": "private",
        "last_verified": "2026-09-25",
        "resume_variant": "outputs/resumes/acme-engineer-2026-09-25/resume.pdf",
        "contacts": ["Jane — recruiter"],
        "follow_ups": [{"date": "2026-10-01", "note": "Polite nudge", "done": False}],
    }
    assert vmod.check_schema(base) == []
    bad = {**base, "resume_variant": "../outside.pdf", "contacts": [""],
           "follow_ups": [{"date": "2026-02-30", "note": "", "done": "no"}]}
    errors = "\n".join(vmod.check_schema(bad))
    assert "resume_variant" in errors
    assert "contacts[0]" in errors
    assert "follow_ups[0].date" in errors
    assert "follow_ups[0].note" in errors
    assert "follow_ups[0].done" in errors
    invalid_application_date = {**base, "date": "2026-02-30"}
    assert any("application date" in error for error in vmod.check_schema(invalid_application_date))


def test_phase2_skills_have_discoverable_frontmatter_and_resources():
    for name in ("resume", "cover-letter", "interview-prep", "outreach"):
        path = ROOT / "skills" / name / "SKILL.md"
        text = path.read_text()
        assert text.startswith("---\n")
        frontmatter = yaml.safe_load(text[4:text.find("\n---", 4)])
        assert frontmatter["name"] == name
        assert frontmatter["description"]
    assert (ROOT / "templates" / "resume" / "layout.typ").is_file()
    assert (ROOT / "scripts" / "check_resume.py").is_file()
    assert (ROOT / "scripts" / "due_followups.py").is_file()


def test_publication_links_are_validated(vmod):
    entity = {
        "id": "pub-example", "type": "publication", "title": "Example Paper",
        "summary": "Example result", "venue": "Example Conference", "date": "2024",
        "status": "completed", "visibility": "private", "last_verified": "2026-09-25",
        "url": "https://example.com/paper", "code_url": "https://github.com/example/code",
    }
    assert vmod.check_schema(entity) == []
    bad = {**entity, "url": "example.com/paper", "code_url": "../code"}
    errors = "\n".join(vmod.check_schema(bad))
    assert "url must be an HTTP(S) URL" in errors
    assert "code_url must be an HTTP(S) URL" in errors


@pytest.mark.skipif(not (shutil.which("typst") and shutil.which("pdftotext") and shutil.which("pdfinfo")),
                    reason="Typst and Poppler are required for the PDF smoke test")
def test_synthetic_resume_compiles_and_passes_general_and_tailored_checks(tmp_path):
    pdf = tmp_path / "example.pdf"
    subprocess.run(["typst", "compile", str(ROOT / "templates/resume/example.typ"), str(pdf)], check=True)
    text = ats.extract_text(pdf)
    assert ats.check_text(text, ["Summary", "Skills", "Experience", "Projects", "Education", "Publications"],
                          ["Python", "Data quality"])["pass"]
    general = ats.check_text(text, ["Summary", "Skills", "Experience", "Projects", "Education", "Publications"], [])
    assert general["pass"] and general["keywords_checked"] == 0
    assert "2018 - 2022" in text
    assert {"https://example.com/paper", "https://github.com/example/example-paper"} <= ats.extract_urls(pdf)


@pytest.mark.skipif(not shutil.which("typst"), reason="Typst is required for the template guard test")
def test_resume_template_rejects_single_bullet_experience(tmp_path):
    shutil.copy(ROOT / "templates/resume/layout.typ", tmp_path / "layout.typ")
    source = tmp_path / "single-bullet.typ"
    source.write_text('''#import "layout.typ": resume
#resume(
  (name: "Alex Example", headline: "", contact: ()),
  experience: (
    (title: "Engineer", org: "Example Company", dates: "2024 - 2025",
     bullets: ([Only one bullet.],)),
  ),
)
''')
    result = subprocess.run(["typst", "compile", str(source), str(tmp_path / "invalid.pdf")],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "at least two supported bullets" in result.stderr
