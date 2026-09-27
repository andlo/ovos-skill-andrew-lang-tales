"""Tests for extract_book() against HTML fragments shaped like a real
Project Gutenberg book page - deliberately not hitting the live site in
CI. test_text_cleanup.py runs it on cut-down real pages."""
import pytest

from conftest import extract_book

BOOK_HTML = b"""
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

MISSING_ANCHOR_HTML = b"<html><body><p>no anchors here</p></body></html>"

# Regression fixture for a real bug: 'A Voyage to Lilliput' contains its own
# nested sub-chapter anchors (link2HCH0001, ...) *inside* the story, before
# any <p> text - a naive "stop at the next <a id='link...'>" rule breaks
# immediately and returns zero paragraphs. We must only stop at anchors that
# belong to *other stories* per self.index, not any 'link'-prefixed anchor -
# and its chapter headings are <h2>s that do not end it either.
NESTED_ANCHOR_HTML = b"""
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


def test_extract_book():
    stories, errors = extract_book(BOOK_HTML, ["link2H_4_0007", "link2H_4_0008"])
    assert errors == {}
    assert stories["link2H_4_0007"] == [
        "Once there was a gentleman who married a proud woman.",
        "She had two daughters of her own humour.",
    ]
    assert stories["link2H_4_0008"] == [
        "This text belongs to the next story and must not be included.",
    ]


def test_extract_book_missing_anchor_is_an_error_for_that_story_only():
    stories, errors = extract_book(MISSING_ANCHOR_HTML, ["link2H_4_9999"])
    assert stories == {}
    assert "link2H_4_9999" in errors["link2H_4_9999"]


def test_extract_book_ignores_nested_sub_chapter_anchors():
    stories, errors = extract_book(NESTED_ANCHOR_HTML, ["link2H_4_0032", "link2H_4_0033"])
    assert stories["link2H_4_0032"] == [
        "My father had a small estate in Nottinghamshire.",
        "The emperor came out of his palace on horseback.",
    ]


def test_a_story_without_text_is_an_error():
    html = b'<a id="a1"></a><h2>ONE</h2><p>(1) Grimm.</p><a id="a2"></a><h2>TWO</h2><p>Once upon a time there was a king.</p>'
    stories, errors = extract_book(html, ["a1", "a2"])
    assert "a1" in errors
    assert stories == {"a2": ["Once upon a time there was a king."]}


@pytest.mark.parametrize("encoding_declared", [True, False])
def test_the_page_is_read_as_utf8_whatever_it_declares(encoding_declared):
    """Gutenberg sends 'Content-Type: text/html' without a charset, and
    several of these pages have no <meta charset> either."""
    head = b'<meta charset="utf-8">' if encoding_declared else b""
    html = head + '<a id="a1"></a><h2>T</h2><p>Mährchen, fées, “quotes”.</p>'.encode("utf-8")
    stories, _ = extract_book(html, ["a1"])
    assert stories["a1"] == ["Mährchen, fées, “quotes”."]
