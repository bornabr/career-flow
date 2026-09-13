from conftest import VALID_PROJECT, VALID_SKILL, write_entity


def test_parse_frontmatter_valid(vmod):
    fm, err = vmod.parse_frontmatter("---\nid: x\ntitle: T\n---\nbody")
    assert err is None
    assert fm == {"id": "x", "title": "T"}


def test_parse_frontmatter_missing(vmod):
    fm, err = vmod.parse_frontmatter("no frontmatter here")
    assert fm is None
    assert "frontmatter" in err


def test_load_valid_entity(vmod, data_repo):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)
    write_entity(data_repo, "skills", "skill-python.md", VALID_SKILL)
    entities, errors = vmod.load_entities(data_repo / "data")
    assert errors == []
    assert set(entities) == {"proj-alpha", "skill-python"}
    assert entities["proj-alpha"]["title"] == "Alpha"


def test_filename_must_match_id(vmod, data_repo):
    write_entity(data_repo, "projects", "proj-wrongname.md", VALID_PROJECT)
    _, errors = vmod.load_entities(data_repo / "data")
    assert any("filename" in e for e in errors)


def test_wrong_prefix_for_directory(vmod, data_repo):
    bad = VALID_PROJECT.replace("id: proj-alpha", "id: exp-alpha")
    write_entity(data_repo, "projects", "exp-alpha.md", bad)
    _, errors = vmod.load_entities(data_repo / "data")
    assert any("prefix" in e for e in errors)


def test_missing_required_field(vmod):
    entity = {"id": "proj-a", "type": "project", "title": "A",
              "status": "active", "visibility": "private",
              "last_verified": "2026-08-08", "start": "2026-01"}
    errors = vmod.check_schema(entity)          # summary missing
    assert any("summary" in e for e in errors)


def test_bad_enum_values(vmod):
    entity = {"id": "skill-x", "type": "skill", "title": "X", "summary": "s",
              "status": "открыт", "visibility": "everyone",
              "last_verified": "2026-08-08"}
    errors = vmod.check_schema(entity)
    assert any("status" in e for e in errors)
    assert any("visibility" in e for e in errors)


def test_bad_dates(vmod):
    entity = {"id": "proj-a", "type": "project", "title": "A", "summary": "s",
              "status": "active", "visibility": "private",
              "last_verified": "yesterday", "start": "January 2026"}
    errors = vmod.check_schema(entity)
    assert any("last_verified" in e for e in errors)
    assert any("start" in e for e in errors)


def test_story_requires_experience_or_project_link(vmod):
    entity = {"id": "story-x", "type": "story", "title": "X", "summary": "s",
              "status": "active", "visibility": "private",
              "last_verified": "2026-08-08", "links": {"skills": []}}
    errors = vmod.check_schema(entity)
    assert any("story" in e and "link" in e for e in errors)


def test_duplicate_ids(vmod, data_repo):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)
    dup = VALID_PROJECT.replace("proj-alpha", "proj-beta") \
                       .replace("id: proj-beta", "id: proj-alpha")
    write_entity(data_repo, "projects", "proj-beta.md", dup)
    _, errors = vmod.load_entities(data_repo / "data")
    assert any("duplicate" in e for e in errors)


def test_summary_must_be_one_line(vmod):
    entity = {"id": "proj-a", "type": "project", "title": "A",
              "summary": "first line\nsecond line", "status": "active",
              "visibility": "private", "last_verified": "2026-08-08",
              "start": "2026-01"}
    errors = vmod.check_schema(entity)
    assert any("summary must be one line" in e for e in errors)


def test_body_requires_narrative_and_raw_notes(vmod):
    errors = vmod.check_body("---\nid: proj-a\n---\n", "proj-a")
    assert any("# Narrative" in e for e in errors)
    assert any("## Raw notes" in e for e in errors)


def test_body_sections_must_be_non_empty(vmod):
    text = "---\nid: proj-a\n---\n# Narrative\n\n## Raw notes\n"
    errors = vmod.check_body(text, "proj-a")
    assert any("Narrative must not be empty" in e for e in errors)
    assert any("Raw notes must not be empty" in e for e in errors)
