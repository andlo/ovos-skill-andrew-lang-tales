# <img src='story-512.png' card_color='#40DBB0' width='50' height='50' style='vertical-align:bottom'/> Andrew Lang Tales (provider)

A *provider* skill for [ovos-common-reading-pipeline-plugin](https://github.com/andlo/ovos-common-reading-pipeline-plugin),
delivering Andrew Lang's twelve "Coloured" Fairy Books.

_"These fairy tales are the oldest stories in the world."_
— Andrew Lang, preface to The Green Fairy Book

[![Tests](https://github.com/andlo/ovos-skill-andrew-lang-tales/actions/workflows/test.yml/badge.svg)](https://github.com/andlo/ovos-skill-andrew-lang-tales/actions/workflows/test.yml)
[![PyPI version](https://img.shields.io/pypi/v/ovos-skill-andrew-lang-tales.svg)](https://pypi.org/project/ovos-skill-andrew-lang-tales/)

> **This skill has no standalone voice interface.** It registers no
> intents and never speaks. It only answers
> [ovos.common_reading.* bus messages](https://github.com/andlo/ovos-common-reading-pipeline-plugin#the-ovoscommon_reading-bus-protocol),
> so you also need **ovos-common-reading-pipeline-plugin** installed and
> added to your pipeline config for it to be useful at all.

## Install
```bash
pip install ovos-skill-andrew-lang-tales ovos-common-reading-pipeline-plugin
```

## Story index

Unlike the other providers here, the story index (title, book, author,
Project Gutenberg anchor per story) is **bundled with this package**
(`locale/en-us/index.json`), not scraped live - browsing/matching needs
no internet at all. Only fetching a specific story's actual text (once
chosen) needs a live request to Project Gutenberg.

**382 stories** across 11 of Andrew Lang's 12 "Coloured" Fairy Books
(the 12th, the *Olive Fairy Book*, uses an incompatible page-based
anchor scheme on Gutenberg and isn't included - tracked as a known gap,
see `scripts/build_lang_index.py`'s docstring).

The index was built once via `scripts/build_lang_index.py`, which:
- Fetches Andrew Lang's master index (Gutenberg ebook #30580)
- Repairs anchors for books Gutenberg has since re-published with a
  different scheme (Red and Brown Fairy Books)
- Validates every entry actually extracts real text before including it

## Collection hints

Responds to `collection_hint` values like "andrew lang", "lang", "the
fairy books", matched fuzzily (see `COLLECTION_ALIASES` in
`__init__.py`). "lang" alone is short enough to be worth double-checking
for false positives - verified via `match_one` against "grimm",
"andersen", "arxiv", "language", etc.

## Content type

Identifies as `content_type: "story"` or `"tale"`. A search with a
`content_type` hint for anything else (e.g. "article", "paper") gets no
response from this provider.

## Credits

Content sourced from [Project Gutenberg](https://www.gutenberg.org/).
Scraping/extraction logic ported from
[ovos-skill-worldtales](https://github.com/andlo/ovos-skill-worldtales)
(archived - this provider supersedes it).

## Category
**Entertainment**

## Tags
#stories #fairytales #gutenberg #provider
