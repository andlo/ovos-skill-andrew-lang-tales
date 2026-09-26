"""What a story reads like once extracted, on real pages from
gutenberg.org cut down to a few paragraphs (tests/fixtures/). Each test
names what the old extractor did with the same page."""
import pytest

from conftest import extract_book, fixture_page, is_source_note


def story(page, anchor, anchors):
    stories, errors = extract_book(fixture_page(page), anchors)
    assert anchor in stories, errors
    return stories[anchor]


BLUE = ["link2H_4_0007", "link2H_4_0008", "link2H_4_0010", "link2H_4_0011"]


def cinderella():
    return story("blue-fairy-book.html", "link2H_4_0007", BLUE)


def rumpelstiltzkin():
    return story("blue-fairy-book.html", "link2H_4_0010", BLUE)


def test_the_pages_line_wraps_are_joined():
    """Was 'the proudest\\n      and most haughty woman': the reading
    plugin splits sentences on '. ', and missed every one that ended at
    the end of a line of HTML."""
    first = cinderella()[0]
    assert "\n" not in first and "  " not in first
    assert first.startswith("Once there was a gentleman who married, for his second wife, "
                            "the proudest and most haughty woman that was ever seen. She had,")
    assert len(first.split(". ")) == 3


def test_a_footnote_and_its_number_are_not_read():
    """Cinderella used to end '...two great lords of the Court.(1)', then
    a paragraph of its own: '(1) Charles Perrault.'"""
    paragraphs = cinderella()
    assert paragraphs[-1].endswith("matched them with two great lords of the Court.")
    assert not any("Perrault" in p or "(1)" in p for p in paragraphs)


def test_a_rhyme_is_read_line_by_line():
    """Rhymes are <pre> blocks, and only <p> used to be read: the name
    that ends Rumpelstiltzkin was never heard."""
    assert "“To-morrow I brew, to-day I bake,\nAnd then the child away I’ll take;\n" \
           "For little deems my royal dame\nThat Rumpelstiltzkin is my name!”" in rumpelstiltzkin()


def test_a_story_ends_where_the_next_one_starts():
    paragraphs = rumpelstiltzkin()
    assert paragraphs[-1].endswith("with both hands and tore himself in two.")
    assert not any("merchant" in p for p in paragraphs)


def test_footnote_numbers_in_sup_tags_are_not_read():
    """The Brown Fairy Book: 'named Saman-lalposh,<sup>[2]</sup> had three'."""
    first = story("brown-fairy-book.html", "chap01", ["chap01", "chap26"])[0]
    assert first.startswith("Once upon a time a great king of the East, named Saman-lalposh, "
                            "had three brave and clever sons—Tahmasp, Qamas, and Almas-ruh-baksh. One day")


def test_a_story_ends_at_the_books_footnotes():
    paragraphs = story("brown-fairy-book.html", "chap01", ["chap01", "chap26"])
    assert paragraphs[-1] == "Finished, finished, finished!"


def test_a_story_does_not_run_on_into_a_tale_the_index_leaves_out():
    """'Which was the Foolishest?' went on into 'Asmund and Signy' and four
    more tales after it - 90 000 characters for an 8 000 character story."""
    paragraphs = story("brown-fairy-book.html", "chap26", ["chap01", "chap26"])
    assert paragraphs[-1] == ("So the women quarrelled just as much as they did before, "
                              "and no one ever knew whose husband was the most foolish.")
    assert not any("Asmund" in p or "Neuislandische" in p for p in paragraphs)


def test_a_tale_titled_in_a_paragraph_ends_the_story_before_it():
    """The Yellow Fairy Book puts nine tales inside 'The Dragon And His
    Grandmother' (115 000 characters), titled in plain paragraphs or
    <pre>s rather than headings."""
    anchors = ["link2H_4_0009", "link2H_4_0010"]
    dragon = story("yellow-fairy-book.html", "link2H_4_0009", anchors)
    assert dragon[-1].endswith("whipped as much money as they wanted, and lived happily to their lives end.")
    six_men = story("yellow-fairy-book.html", "link2H_4_0010", anchors)
    assert six_men[-1].endswith("shared it among themselves, and lived contentedly till the end of their days.")
    assert not any("WIZARD" in p or "Hunter" in p or "(14)" in p for p in dragon + six_men)


def test_a_footnote_inside_a_sentence_is_not_read():
    """'the korigans[FN#3: The spiteful fairies.] who dwell'."""
    paragraphs = story("lilac-fairy-book.html", "link2H_4_0033", ["link2H_4_0033", "link2H_4_0034"])
    assert "I am sure, that the korigans who dwell in the White Corn country" in paragraphs[0]


def test_the_last_story_of_a_book_stops_before_the_licence():
    paragraphs = story("lilac-fairy-book.html", "link2H_4_0034", ["link2H_4_0033", "link2H_4_0034"])
    assert paragraphs[-1].startswith("There was once a king and queen who had a little boy")
    assert not any("Gutenberg" in p or "Mabinogion" in p for p in paragraphs)


def test_prose_in_a_pre_block_is_read_as_prose():
    """The Grey Fairy Book has ten lines of prose in a <pre>: its line
    breaks are the transcriber's, not verse."""
    paragraphs = story("grey-fairy-book.html", "link2H_4_0022", ["link2H_4_0022", "link2H_4_0023"])
    assert paragraphs[1].startswith("‘Not knowing what I did I staggered towards the sabre which was "
                                    "lying near me, with the intention")
    assert paragraphs[2].startswith("The whole company were listening to the story with breathless attention,")
    assert not any("\n" in p for p in paragraphs)


def test_a_source_note_is_not_read_but_a_shout_in_capitals_is():
    paragraphs = story("green-fairy-book.html", "link2H_4_0024", ["link2H_4_0024", "link2H_4_0025"])
    assert "‘SOMEBODY HAS BEEN AT MY PORRIDGE!’" in paragraphs
    assert paragraphs[-1].endswith("But the Three Bears never saw anything more of her.")


@pytest.mark.parametrize("note", [
    "Grimm.", "Southey.", "Charles Deulin.", "Spanish Tradition.", "A Pushto Story.",
    "End of The Grey Fairy Book.", "Le Prince Muguet et la Princesse Zaza.",
    "L’Oiseau Bleu. Par Mme. d’Aulnoy.", "[From Ungarische Mährchen.]", "(Japanische Marchen.)",
    "From Z. Topelius.", "From ‘West Highland Tales.’", "By the Comte de Caylus.",
    "Adapted from the Portuguese.", "‘Legendary Fictions of the Irish Celts,’ by Patrick Kennedy.",
])
def test_source_notes(note):
    assert is_source_note(note)


@pytest.mark.parametrize("ending", [
    # real last paragraphs of stories in the index
    "And so they were.", "And very likely he did!", "The Emperor said, ‘Good-morning!’",
    "And no one thought of the Snow-man.", "You see that is the way of the world.",
    "Finished, finished, finished!", "A mouse has run,\nMy story’s done.",
    "Here our Danish author ends. This is what people call sentiment, and I hope you enjoy it!",
    "From that day on they lived happily together.",
])
def test_story_endings_are_not_source_notes(ending):
    assert not is_source_note(ending)
