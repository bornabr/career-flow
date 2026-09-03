from conftest import VALID_PROJECT, VALID_SKILL, write_entity

EXP = """id: exp-acme
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
"""

OLD_PROJECT = VALID_PROJECT.replace("proj-alpha", "proj-old") \
                           .replace("start: 2026-01", "start: 2020-05")


def test_index_content_and_order(vmod, data_repo):
    write_entity(data_repo, "experiences", "exp-acme.md", EXP)
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)
    write_entity(data_repo, "projects", "proj-old.md", OLD_PROJECT)
    write_entity(data_repo, "skills", "skill-python.md", VALID_SKILL)
    entities, errors = vmod.load_entities(data_repo / "data")
    assert errors == []
    index = vmod.build_index(entities)
    assert index.startswith("# INDEX\n")
    assert "do not edit by hand" in index
    assert "- exp-acme — Senior Engineer (2022-03 –) — Led the platform team" in index
    assert "- skill-python — Python — Primary language" in index
    assert index.index("## Experiences") < index.index("## Projects") < index.index("## Skills")
    # newest project first
    assert index.index("proj-alpha") < index.index("proj-old")
    # empty sections omitted
    assert "## Stories" not in index


def test_index_deterministic(vmod, data_repo):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)
    write_entity(data_repo, "skills", "skill-python.md", VALID_SKILL)
    entities, _ = vmod.load_entities(data_repo / "data")
    assert vmod.build_index(entities) == vmod.build_index(entities)


def test_main_success_writes_index(vmod, data_repo, capsys):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)
    write_entity(data_repo, "skills", "skill-python.md", VALID_SKILL)
    rc = vmod.main([str(data_repo)])
    assert rc == 0
    assert (data_repo / "data" / "INDEX.md").exists()
    assert "OK" in capsys.readouterr().out


def test_main_errors_no_index(vmod, data_repo, capsys):
    write_entity(data_repo, "projects", "proj-alpha.md", VALID_PROJECT)  # broken link
    rc = vmod.main([str(data_repo)])
    assert rc == 1
    assert not (data_repo / "data" / "INDEX.md").exists()
    assert "ERROR:" in capsys.readouterr().out


def test_main_rejects_entity_without_required_body(vmod, data_repo, capsys):
    project = VALID_PROJECT.replace("links:\n  skills: [skill-python]\n", "")
    write_entity(data_repo, "projects", "proj-alpha.md", project, body="")
    rc = vmod.main([str(data_repo)])
    assert rc == 1
    output = capsys.readouterr().out
    assert "# Narrative" in output
    assert "## Raw notes" in output


def test_main_missing_data_dir(vmod, tmp_path):
    assert vmod.main([str(tmp_path)]) == 2
