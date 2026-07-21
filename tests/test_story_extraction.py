"""Tests for get_story_paragraphs() against a saved HTML fragment shaped
like a real Project Gutenberg book page - deliberately not hitting the
live site in CI."""
import requests
import pytest
from bs4 import BeautifulSoup

from conftest import StoryFetchError

BOOK_HTML = """
<html><body>
<a href="#link2H_4_0006"> An Earlier Tale </a>
<a id="link2H_4_0007">
<!--  H2 anchor --> </a>
<div style="height: 4em;"><br/></div>
<h2>CINDERELLA, OR THE LITTLE GLASS SLIPPER</h2>
<p>Once there was a gentleman who married a proud woman.</p>
<p>She had two daughters of her own humour.</p>
<a id="link2H_4_0008">
<!--  H2 anchor --> </a>
<h2>THE NEXT STORY</h2>
<p>This text belongs to the next story and must not be included.</p>
</body></html>
"""

MISSING_ANCHOR_HTML = "<html><body><p>no anchors here</p></body></html>"

# Regression fixture for a real bug: 'A Voyage to Lilliput' contains its own
# nested sub-chapter anchors (link2HCH0001, ...) *inside* the story, before
# any <p> text - a naive "stop at the next <a id='link...'>" rule breaks
# immediately and returns zero paragraphs. We must only stop at anchors that
# belong to *other stories* per self.index, not any 'link'-prefixed anchor.
NESTED_ANCHOR_HTML = """
<html><body>
<a id="link2H_4_0032"><!--  H2 anchor --> </a>
<h2>A VOYAGE TO LILLIPUT</h2>
<a id="link2HCH0001"><!--  H2 anchor --> </a>
<h2>CHAPTER I</h2>
<p>My father had a small estate in Nottinghamshire.</p>
<a id="link2HCH0002"><!--  H2 anchor --> </a>
<h2>CHAPTER II</h2>
<p>The emperor came out of his palace on horseback.</p>
<a id="link2H_4_0033"><!--  H2 anchor --> </a>
<h2>THE NEXT STORY</h2>
<p>This text belongs to the next story and must not be included.</p>
</body></html>
"""


def test_get_story_paragraphs(skill, monkeypatch):
    monkeypatch.setattr(skill, "_get_book_soup", lambda url: BeautifulSoup(BOOK_HTML, "html.parser"))
    url = "http://example.test/book.htm"
    # get_story_paragraphs finds the *next* story's boundary via self.index,
    # so both stories sharing this book file need to be registered there -
    # mirrors how the real bundled index.json is structured.
    skill.index = {
        "Cinderella, Or The Little Glass Slipper": {"url": url, "anchor": "link2H_4_0007", "book": "Blue Fairy Book"},
        "The Next Story": {"url": url, "anchor": "link2H_4_0008", "book": "Blue Fairy Book"},
    }
    entry = skill.index["Cinderella, Or The Little Glass Slipper"]
    paragraphs = skill.get_story_paragraphs(entry)
    assert paragraphs == [
        "Once there was a gentleman who married a proud woman.",
        "She had two daughters of her own humour.",
    ]


def test_get_story_paragraphs_missing_anchor_raises(skill, monkeypatch):
    monkeypatch.setattr(skill, "_get_book_soup", lambda url: BeautifulSoup(MISSING_ANCHOR_HTML, "html.parser"))
    entry = {"url": "http://example.test/book.htm", "anchor": "link2H_4_9999", "book": "Blue Fairy Book"}
    with pytest.raises(StoryFetchError):
        skill.get_story_paragraphs(entry)


def test_get_book_soup_caches_and_wraps_request_exception(skill, monkeypatch):
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(StoryFetchError):
        skill._get_book_soup("http://example.test/down.htm")
    assert len(calls) == 1


def test_get_story_paragraphs_ignores_nested_sub_chapter_anchors(skill, monkeypatch):
    monkeypatch.setattr(skill, "_get_book_soup", lambda url: BeautifulSoup(NESTED_ANCHOR_HTML, "html.parser"))
    url = "http://example.test/book.htm"
    skill.index = {
        "A Voyage To Lilliput": {"url": url, "anchor": "link2H_4_0032", "book": "Blue Fairy Book"},
        "The Next Story": {"url": url, "anchor": "link2H_4_0033", "book": "Blue Fairy Book"},
    }
    entry = skill.index["A Voyage To Lilliput"]
    paragraphs = skill.get_story_paragraphs(entry)
    assert paragraphs == [
        "My father had a small estate in Nottinghamshire.",
        "The emperor came out of his palace on horseback.",
    ]
