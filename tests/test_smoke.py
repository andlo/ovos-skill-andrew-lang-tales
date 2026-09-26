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
