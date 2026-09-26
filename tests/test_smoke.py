"""Smoke tests + real bundled index.json loading (382 stories) + loading
on every device language."""
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


@pytest.mark.parametrize("lang", ["en-gb", "fr-fr", "de-de", "xx-xx"])
def test_load_index_is_english_whatever_the_device_language(skill, monkeypatch, lang):
    monkeypatch.setattr(type(skill), "lang", lang, raising=False)
    index = skill._load_index()
    assert len(index) > 300
    assert "Cinderella, Or The Little Glass Slipper" in index


@pytest.mark.parametrize("lang", ["en-us", "en-gb", "fr-fr", "de-de", "da-dk"])
def test_initialize_loads_on_any_device_language(skill, monkeypatch, lang):
    """A HiveMind hub runs one ovos-core for users in several languages,
    so the device's own language cannot decide whether this provider is
    there at all - it always loads, and each search's language decides
    whether it answers (see test_request_language.py)."""
    monkeypatch.setattr(type(skill), "lang", lang, raising=False)
    skill._load_index = MagicMock(return_value={"Cinderella": {}})
    skill.add_event = MagicMock()

    skill.initialize()

    skill._load_index.assert_called_once()
    assert skill.add_event.call_count == 3
    assert skill.index == {"Cinderella": {}}
    logged = " ".join(str(c) for c in skill.log.info.call_args_list)
    assert "English" in logged and "en-*" in logged
