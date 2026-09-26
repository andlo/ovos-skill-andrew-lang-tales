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

> **English only, no translation.** Unlike `ovos-skill-andersen-tales`/
> `ovos-skill-grimm-tales` (real per-language sources) or
> `ovos-skill-ovosblog`/`ovos-skill-arxiv-papers` (machine-translated),
> this provider has **no non-English content and does not attempt to
> translate** - the stories themselves are long, literary prose, where
> per-request machine translation is both expensive and a much bigger
> quality risk than translating a short blog post or paper abstract (see
> [ovos-common-reading-pipeline-plugin#5](https://github.com/andlo/ovos-common-reading-pipeline-plugin/issues/5)
> for the reasoning). **It answers searches made in English (`en-*`)
> and stays silent for every other language**, and only loads
> where English is configured - the device language or `secondary_langs` (see "Languages" below).

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

## Fetching and what gets read

Reading a story fetches its book from Project Gutenberg once, extracts
the text of every story in that book, and keeps it on disk under the
skill's cache directory (`<XDG cache>/mycroft/skills/<skill_id>/`, one
small JSON file per story). Another story from the same book, or the
same story after a restart, needs no request. After 30 days a
story is checked again with `If-Modified-Since`, which downloads nothing
when the book has not changed; a change to the extractor (`CACHE_FORMAT`)
fetches the books again. When a fetch fails, that book is not asked for
again for five minutes, and an older copy is read meanwhile if there is
one. When the cache directory cannot be written, the last book fetched
is kept in memory instead. Requests say who is asking:
`ovos-skill-andrew-lang-tales/<version> (+https://github.com/andlo/ovos-skill-andrew-lang-tales)`.

What is read is the tale: paragraphs with the page's line wraps joined,
and the rhymes line by line (they are `<pre>` blocks and used to be
skipped). Footnotes and their numbers, the editor's note on where a tale
came from ("Grimm.", "[From Ungarische Mährchen.]"), bare section
numbers and Gutenberg's licence are left out. A story also ends where a
tale the index does not have begins, instead of running on into it.

## Languages

**English only.** Andrew Lang's Fairy Books are sourced from Project
Gutenberg in English; no other language editions exist for this
collection, and this provider makes no attempt to machine-translate (see
the note above).

The provider loads only where English is one of the languages the
installation is configured for: the device's own `lang`, or one of
`secondary_langs` in `mycroft.conf`. A single device in another
language never loads it. A HiveMind hub whose users speak English lists
it there, even when the hub's own language is something else:

```json
{
  "lang": "da-DK",
  "secondary_langs": ["en-US"]
}
```

Once loaded, it decides **per search** whether to answer:
a search made in English gets an answer, any other language gets none.
The language of a search is the pipeline plugin's `lang` field, else the
language of the session the search came from, else (an older plugin
sends neither) the device's own language. That matters on a HiveMind
hub, where one ovos-core serves many users at once, each session in its
own language: a French session must not get English stories, and an
English session must still get them on a hub whose own language is
French. A `ping` that names a language (the same way) only gets a pong
when that is English. Fetching a story is never gated on language - it
is addressed to this provider directly.

## Title matching

Titles match regardless of case, accents, punctuation, a leading
article and a leading "Story Of" / "History Of" / "Tale Of", so "the six
swans" finds *The Six Swans* and "the three bears" finds *The Story Of
The Three Bears* at full confidence. For "X, Or Y" titles each half
counts too, slightly below the whole title: "cinderella" finds
*Cinderella, Or The Little Glass Slipper* and "puss in boots" *The
Master Cat; Or, Puss In Boots*. A search that names no title at all
("tell me a story") gets one random story at confidence 0.9, or 1.0
when it named this collection.

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
