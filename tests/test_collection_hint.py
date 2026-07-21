"""Tests for fuzzy collection_hint / content_type matching. 'lang' is a
short, generic-looking alias - verified via match_one against realistic
other collection names before trusting it (see README)."""
import pytest


@pytest.mark.parametrize("hint", ["andrew lang", "lang", "the fairy books", "Lang", "LANG"])
def test_matches_known_aliases(skill, hint):
    assert skill._matches_collection_hint(hint) is True


@pytest.mark.parametrize("hint", ["grimm", "andersen", "the ovos blog", "arxiv", "language"])
def test_does_not_match_other_collections(skill, hint):
    assert skill._matches_collection_hint(hint) is False


def test_none_hint_matches_everyone(skill):
    assert skill._matches_collection_hint(None) is True


@pytest.mark.parametrize("content_type", ["story", "tale", "STORY", None, ""])
def test_matches_expected_content_types(skill, content_type):
    assert skill._matches_content_type(content_type) is True


@pytest.mark.parametrize("content_type", ["article", "poem", "news", "paper"])
def test_does_not_match_other_content_types(skill, content_type):
    assert skill._matches_content_type(content_type) is False
