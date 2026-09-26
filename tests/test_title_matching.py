"""Title matching against the real bundled index (382 stories): case,
accents, punctuation and a leading article do not matter, and the name
people actually use for an 'X, Or Y' title finds it."""
import pytest
from ovos_bus_client.message import Message

from conftest import normalize_title, title_aliases

CONFIRMATION_THRESHOLD = 0.8  # the pipeline plugin asks "is it that one?" below this


@pytest.fixture
def indexed(skill):
    skill.index = skill._load_index()
    return skill


@pytest.mark.parametrize("phrase", [
    "Cinderella, Or The Little Glass Slipper",
    "cinderella or the little glass slipper",
    "CINDERELLA, OR THE LITTLE GLASS SLIPPER",
])
def test_exact_title_in_any_case(indexed, phrase):
    title, score = indexed._best_title(phrase)
    assert title == "Cinderella, Or The Little Glass Slipper"
    assert score >= 0.95


@pytest.mark.parametrize("phrase", ["The Six Swans", "the six swans", "THE SIX SWANS", "six swans"])
def test_exact_title_scores_at_least_095(indexed, phrase):
    assert indexed._best_title(phrase) == ("The Six Swans", 1.0)


@pytest.mark.parametrize("phrase, expected", [
    # used to match 'Cannetella' at 0.60
    ("cinderella", "Cinderella, Or The Little Glass Slipper"),
    ("the little glass slipper", "Cinderella, Or The Little Glass Slipper"),
    ("puss in boots", "The Master Cat; Or, Puss In Boots"),
    ("king kojata", "King Kojata (From The Russian)"),
    ("the three bears", "The Story Of The Three Bears"),
    ("the emperor's new clothes", "Story Of The Emperor's New Clothes"),
    ("the goose girl", "The Goose-Girl"),
    ("bluebeard", "Blue Beard"),
    ("the tinderbox", "The Tinder-Box"),
])
def test_name_people_use_finds_the_title(indexed, phrase, expected):
    title, score = indexed._best_title(phrase)
    assert title == expected
    assert score >= 0.95


@pytest.mark.parametrize("phrase, expected", [
    ("hansel and gretel", "Hansel And Grettel"),
    ("rumpelstiltskin", "Rumpelstiltzkin"),
])
def test_close_spelling_still_confident(indexed, phrase, expected):
    title, score = indexed._best_title(phrase)
    assert title == expected
    assert score >= CONFIRMATION_THRESHOLD


def test_one_shared_word_is_not_enough_to_skip_the_confirmation(indexed):
    """'the frog prince' is not in this collection; 'The Strong Prince'
    shares most of its letters but only one of its two words."""
    _, score = indexed._best_title("the frog prince")
    assert score < CONFIRMATION_THRESHOLD


def test_search_response_keeps_the_index_title_as_content_id(indexed):
    indexed.handle_search(Message("ovos.common_reading.search", {"phrase": "cinderella"}))
    sent = indexed.bus.emit.call_args[0][0]
    assert sent.data["content_id"] == "Cinderella, Or The Little Glass Slipper"
    assert sent.data["title"] == "Cinderella, Or The Little Glass Slipper"
    assert sent.data["confidence"] >= 0.95


@pytest.mark.parametrize("text, expected", [
    ("The Goose-Girl", "goose girl"),
    ("the story of the three bears", "three bears"),
    ("A Fish Story", "fish story"),
    ("Tritill, Litill, And The Birds", "tritill litill and the birds"),
    ("Hansel & Grettel", "hansel and grettel"),
    ("Fée", "fee"),
    ("The", "the"),
])
def test_normalize_title(text, expected):
    assert normalize_title(text) == expected


def test_title_aliases_of_an_either_or_title():
    aliases = dict(title_aliases("Cinderella, Or The Little Glass Slipper"))
    assert aliases["cinderella or the little glass slipper"] == 1.0
    assert aliases["cinderella"] < 1.0
    assert aliases["little glass slipper"] < 1.0
