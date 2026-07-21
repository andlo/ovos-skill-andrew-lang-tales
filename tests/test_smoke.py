"""Smoke tests + real bundled index.json loading (382 stories) + the
load-time language gate in initialize()."""
from unittest.mock import MagicMock

import pytest
from conftest import AndrewLangTales, StoryFetchError


def test_imports_cleanly():
    assert AndrewLangTales is not None
    assert issubclass(StoryFetchError, Exception)


def test_is_an_ovos_skill():
    from ovos_workshop.skills import OVOSSkill
    assert issubclass(AndrewLangTales, OVOSSkill)


def test_load_index_uses_bundled_en_us(skill):
    index = skill._load_index()
    assert len(index) > 300
    assert "Cinderella, Or The Little Glass Slipper" in index
    entry = index["Cinderella, Or The Little Glass Slipper"]
    assert entry["book"] == "Blue Fairy Book"
    assert entry["author"] == "Andrew Lang"


def test_load_index_falls_back_to_en_us_for_unsupported_language(skill, monkeypatch):
    monkeypatch.setattr(type(skill), "lang", "xx-xx", raising=False)
    index = skill._load_index()
    # xx-xx has no locale/xx-xx/index.json, so this should silently fall
    # back to the bundled English index rather than returning {}
    assert len(index) > 300


def test_initialize_stays_inert_for_non_english_device(skill, monkeypatch):
    """The key behavior requested: don't just decline searches at
    runtime - never even load the index or register bus events for a
    device language this provider can't serve (it never translates)."""
    monkeypatch.setattr(type(skill), "lang", "da-dk", raising=False)
    skill._load_index = MagicMock()
    skill.add_event = MagicMock()

    skill.initialize()

    skill._load_index.assert_not_called()
    skill.add_event.assert_not_called()
    assert skill.index == {}


@pytest.mark.parametrize("lang", ["en-us", "en-gb", "en-au"])
def test_initialize_loads_normally_for_any_english_variant(skill, monkeypatch, lang):
    monkeypatch.setattr(type(skill), "lang", lang, raising=False)
    skill._load_index = MagicMock(return_value={"Cinderella": {}})
    skill.add_event = MagicMock()

    skill.initialize()

    skill._load_index.assert_called_once()
    assert skill.add_event.call_count == 2
    assert skill.index == {"Cinderella": {}}
