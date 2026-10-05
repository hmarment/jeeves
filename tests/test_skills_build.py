import json

import pytest

from jeeves.skills_build import build, render


def test_render_substitutes_tokens():
    assert render("db {{DAILY_PLAN}} x", {"daily_plan": "abc"}) == "db abc x"


def test_render_rejects_missing_or_empty_values():
    with pytest.raises(KeyError, match="daily_plan"):
        render("{{DAILY_PLAN}}", {"daily_plan": ""})


def test_build_writes_rendered_skills(tmp_path):
    source = tmp_path / "skills"
    (source / "start-day").mkdir(parents=True)
    (source / "start-day" / "SKILL.md").write_text("---\nname: start-day\n---\n{{A}}")
    config = tmp_path / "notion.json"
    config.write_text(json.dumps({"a": "value"}))
    written = build(source, config, tmp_path / "dist")
    assert written == [tmp_path / "dist" / "start-day" / "SKILL.md"]
    assert written[0].read_text().endswith("value")
