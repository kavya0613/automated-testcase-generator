import pytest
from tcgen.preprocess import clean_text, load_stories, parse_story_template, validate_story, vague_terms


def test_parse_structured_story():
    p = parse_story_template("As a registered user, I want to log in using my email so that I can access my account.")
    assert p["structured"] and p["actor"] == "registered user"
    assert p["goal"].startswith("log in") and p["benefit"].startswith("I can access")


def test_parse_unstructured_story():
    assert not parse_story_template("User should login.")["structured"]


def test_clean_and_validate():
    assert clean_text("  a \n\n b\u2019s  ") == "a b's"
    with pytest.raises(ValueError):
        validate_story("short")


def test_vague_terms():
    assert "etc" in vague_terms("Make it fast, etc.")


def test_load_stories_json_and_txt():
    assert load_stories("a.json", '[{"user_story": "As a user, I want x so that y"}]')
    assert len(load_stories("a.txt", "story one here\n\nstory two here")) == 2
