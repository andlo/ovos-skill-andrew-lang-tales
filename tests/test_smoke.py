"""Smoke tests + real bundled index.json loading (382 stories)."""
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
