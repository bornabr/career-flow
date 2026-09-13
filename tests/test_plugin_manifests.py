import json
from pathlib import Path


PLUGIN = Path(__file__).resolve().parent.parent


def load_json(relative_path):
    return json.loads((PLUGIN / relative_path).read_text())


def test_claude_and_codex_manifests_share_identity_and_version():
    claude = load_json(".claude-plugin/plugin.json")
    codex = load_json(".codex-plugin/plugin.json")
    assert claude["name"] == codex["name"] == "career-flow"
    assert claude["version"] == codex["version"]
    assert codex["skills"] == "./skills/"


def test_host_marketplaces_expose_career_flow():
    claude = load_json(".claude-plugin/marketplace.json")
    codex = load_json(".agents/plugins/marketplace.json")
    assert claude["name"] == codex["name"] == "career-flow-marketplace"
    assert claude["plugins"][0]["name"] == "career-flow"
    assert codex["plugins"][0]["name"] == "career-flow"
    assert codex["plugins"][0]["source"]["path"] == "./"
    assert codex["plugins"][0]["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }
