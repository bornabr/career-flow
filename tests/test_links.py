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


def test_link_target_must_match_declared_type(vmod, data_repo):
    project = VALID_PROJECT.replace("links:\n  skills: [skill-python]", "links:\n  skills: []")
    story = """id: story-x
type: story
title: X
summary: s
status: active
visibility: private
last_verified: 2026-08-08
links:
  experience: proj-alpha
"""
    write_entity(data_repo, "projects", "proj-alpha.md", project)
    write_entity(data_repo, "stories", "story-x.md", story)
    errors, _ = vmod.check_links(_load(vmod, data_repo))
    assert any("links.experience" in e and "project" in e for e in errors)


def test_skill_links_require_string_ids(vmod):
    entity = {"id": "proj-a", "type": "project", "title": "A", "summary": "s",
              "status": "active", "visibility": "private",
              "last_verified": "2026-08-08", "start": "2026-01",
              "links": {"skills": [123]}}
    errors = vmod.check_schema(entity)
    assert any("links.skills[0]" in e for e in errors)
