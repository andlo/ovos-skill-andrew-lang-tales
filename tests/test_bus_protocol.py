"""Tests for the ovos.common_reading.* bus protocol handlers."""
from unittest.mock import MagicMock

import pytest
from conftest import AndrewLangTales, COMMON_READING_SEARCH_RESPONSE, COMMON_READING_FETCH_CONTENT_RESPONSE, StoryFetchError


def make_message(data=None):
    m = MagicMock()
    m.data = data or {}
    m.reply = MagicMock(side_effect=lambda mtype, d: MagicMock(msg_type=mtype, data=d))
    return m


def _sample_index():
    return {
        "Cinderella, Or The Little Glass Slipper": {
            "url": "http://x/503", "anchor": "link2H_4_0007",
            "book": "Blue Fairy Book", "author": "Andrew Lang"},
        "The Six Swans": {
            "url": "http://x/640", "anchor": "link2H_4_0010",
            "book": "Yellow Fairy Book", "author": "Andrew Lang"},
    }


def test_handle_search_matches_by_phrase(skill):
    skill.index = _sample_index()

    skill.handle_search(make_message({"phrase": "cinderella"}))

    sent = skill.bus.emit.call_args[0][0]
    assert sent.msg_type == COMMON_READING_SEARCH_RESPONSE
    assert sent.data["title"] == "Cinderella, Or The Little Glass Slipper"
    assert sent.data["content_id"] == "Cinderella, Or The Little Glass Slipper"
    assert sent.data["author"] == "Andrew Lang"
    assert sent.data["collection"] == "Blue Fairy Book"
    assert sent.data["source"] == "Project Gutenberg"


def test_handle_search_stays_silent_on_empty_index(skill):
    skill.index = {}
    skill.handle_search(make_message({"phrase": "anything"}))
    skill.bus.emit.assert_not_called()


def test_handle_search_stays_silent_for_non_english_device(skill, monkeypatch):
    """English-only content, no translation - a non-English device gets
    silence, not a mismatched-language response (see README)."""
    monkeypatch.setattr(AndrewLangTales, "lang", "da-dk", raising=False)
    skill.index = _sample_index()
    skill.handle_search(make_message({"phrase": "cinderella"}))
    skill.bus.emit.assert_not_called()


def test_handle_search_stays_silent_for_non_english_even_with_collection_hint(skill, monkeypatch):
    monkeypatch.setattr(AndrewLangTales, "lang", "de-de", raising=False)
    skill.index = _sample_index()
    skill.handle_search(make_message({"phrase": None, "collection_hint": "andrew lang"}))
    skill.bus.emit.assert_not_called()


@pytest.mark.parametrize("lang", ["en-us", "en-gb", "en-au"])
def test_handle_search_responds_for_any_english_variant(skill, monkeypatch, lang):
    monkeypatch.setattr(AndrewLangTales, "lang", lang, raising=False)
    skill.index = _sample_index()
    skill.handle_search(make_message({"phrase": "cinderella"}))
    skill.bus.emit.assert_called_once()


def test_handle_search_stays_silent_when_collection_hint_does_not_match(skill):
    skill.index = _sample_index()
    skill.handle_search(make_message({"phrase": "cinderella", "collection_hint": "grimm"}))
    skill.bus.emit.assert_not_called()


def test_handle_search_responds_when_collection_hint_matches(skill):
    skill.index = _sample_index()
    skill.handle_search(make_message({"phrase": "cinderella", "collection_hint": "andrew lang"}))
    skill.bus.emit.assert_called_once()


def test_handle_search_surprise_me_with_matching_hint_and_no_phrase(skill):
    skill.index = _sample_index()
    skill.handle_search(make_message({"phrase": None, "collection_hint": "lang"}))
    skill.bus.emit.assert_called_once()
    data = skill.bus.emit.call_args[0][0].data
    assert data["title"] in skill.index


def test_handle_search_no_phrase_no_hint_stays_silent(skill):
    skill.index = _sample_index()
    skill.handle_search(make_message({"phrase": None, "collection_hint": None}))
    skill.bus.emit.assert_not_called()


def test_handle_search_stays_silent_for_mismatched_content_type(skill):
    skill.index = _sample_index()
    skill.handle_search(make_message({"phrase": "cinderella", "content_type": "article"}))
    skill.bus.emit.assert_not_called()


def test_handle_search_responds_for_matching_content_type(skill):
    skill.index = _sample_index()
    for content_type in ["story", "tale", "STORY"]:
        skill.bus.emit.reset_mock()
        skill.handle_search(make_message({"phrase": "cinderella", "content_type": content_type}))
        skill.bus.emit.assert_called_once()


def test_handle_fetch_content_success(skill):
    skill.index = _sample_index()
    skill.get_story_paragraphs = MagicMock(return_value=["Once upon a time.", "The end."])

    skill.handle_fetch_content(make_message({"content_id": "Cinderella, Or The Little Glass Slipper"}))

    sent = skill.bus.emit.call_args[0][0]
    assert sent.msg_type == COMMON_READING_FETCH_CONTENT_RESPONSE
    assert sent.data["paragraphs"] == ["Once upon a time.", "The end."]


def test_handle_fetch_content_unknown_id_returns_empty(skill):
    skill.index = {}
    skill.handle_fetch_content(make_message({"content_id": "Nonexistent"}))
    sent = skill.bus.emit.call_args[0][0]
    assert sent.data["paragraphs"] == []


def test_handle_fetch_content_fetch_error_returns_empty(skill):
    skill.index = _sample_index()
    skill.get_story_paragraphs = MagicMock(side_effect=StoryFetchError("boom"))

    skill.handle_fetch_content(make_message({"content_id": "Cinderella, Or The Little Glass Slipper"}))

    sent = skill.bus.emit.call_args[0][0]
    assert sent.data["paragraphs"] == []
