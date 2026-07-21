"""
skill OVOS Andrew Lang Tales
Copyright (C) 2026  Andreas Lorensen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

---

Provider skill for ovos-common-reading-pipeline-plugin: implements the
ovos.common_reading.* bus protocol and registers NO intents of its own.
See https://github.com/andlo/ovos-common-reading-pipeline-plugin for the
full protocol - this skill has no standalone voice interface, it needs
the pipeline plugin installed and configured to be useful.

The story INDEX (title/book/author/anchor per story) is bundled with
this package (see locale/en-us/index.json) rather than scraped live -
browsing/matching needs no internet at all. Internet is only needed when
actually fetching a specific story's text from Project Gutenberg.
"""

from ovos_workshop.skills import OVOSSkill
from ovos_utils.parse import match_one
from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements

import requests
from bs4 import BeautifulSoup
import json
import os
import random


class StoryFetchError(Exception):
    """Raised when a story could not be fetched or parsed from
    Project Gutenberg."""


COMMON_READING_SEARCH = "ovos.common_reading.search"
COMMON_READING_SEARCH_RESPONSE = "ovos.common_reading.search.response"
COMMON_READING_FETCH_CONTENT = "ovos.common_reading.fetch_content"  # + ".{this_skill_id}"
COMMON_READING_FETCH_CONTENT_RESPONSE = "ovos.common_reading.fetch_content.response"

COLLECTION_ALIASES = ["andrew lang", "lang", "the fairy books", "the coloured fairy books",
                       "lang's fairy books"]
COLLECTION_HINT_THRESHOLD = 0.85  # see ovos-common-reading-pipeline-plugin's README for why not lower
CONTENT_TYPES = ["story", "tale"]
SOURCE_NAME = "Project Gutenberg"

# Andrew Lang's Fairy Books are only sourced in English (see README) and
# this provider does NOT translate (unlike ovos-skill-ovosblog/
# ovos-skill-arxiv-papers) - a device set to any other language gets no
# response at all, decided once at load time (see initialize()).
SUPPORTED_LANGUAGES = {"en"}


class AndrewLangTales(OVOSSkill):

    @classproperty
    def runtime_requirements(self):
        # the story index is bundled (see locale/en-us/index.json) -
        # browsing/matching needs no internet. Internet is only needed
        # when actually fetching a specific story's text, handled
        # per-request with a graceful fallback (see handle_fetch_content).
        return RuntimeRequirements(
            internet_before_load=False,
            network_before_load=False,
            requires_internet=False,
            requires_network=False,
            no_internet_fallback=True,
            no_network_fallback=True,
        )

    def initialize(self):
        lang = self.lang.split("-")[0]
        if lang not in SUPPORTED_LANGUAGES:
            self.log.info(
                f"{self.skill_id}: device language '{self.lang}' is not "
                f"English, and this provider (Project Gutenberg / Andrew "
                f"Lang) has no non-English content and does not translate - "
                f"skill will stay inert (no bus events registered, index "
                f"not loaded)."
            )
            self.index = {}
            return
        # in-memory cache of already-fetched Gutenberg book pages
        # (BeautifulSoup), keyed by URL - several stories share the same
        # book file
        self._book_soup_cache = {}
        self.index = self._load_index()
        if not self.index:
            self.log.error("No bundled story index found for this language")
        self.add_event(COMMON_READING_SEARCH, self.handle_search)
        self.add_event(f"{COMMON_READING_FETCH_CONTENT}.{self.skill_id}", self.handle_fetch_content)

    def _index_path_for_lang(self, lang):
        return os.path.join(os.path.dirname(__file__), "locale", lang, "index.json")

    def _load_index(self):
        lang = self.lang
        path = self._index_path_for_lang(lang)
        if not os.path.isfile(path):
            # only en-us is bundled - this fallback is just for other
            # English variants (en-gb, en-au, ...). initialize() already
            # checked self.lang is in SUPPORTED_LANGUAGES before this is
            # ever called, so this only ever runs for English devices.
            self.log.warning(f"no bundled index for '{lang}', falling back to en-us")
            path = self._index_path_for_lang("en-us")
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            self.log.error(f"could not read bundled story index {path}: {e}")
            return {}

    def _get_book_soup(self, url):
        if url in self._book_soup_cache:
            return self._book_soup_cache[url]
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.text, "html.parser")
        except requests.RequestException as e:
            raise StoryFetchError(f"failed to fetch {url}: {e}") from e
        self._book_soup_cache[url] = soup
        return soup

    def get_story_paragraphs(self, entry):
        """Extract a single story's paragraphs from its Project Gutenberg
        book page. Different Gutenberg transcriptions use different anchor
        schemes ('<a id="link...">' before the <h2> title, '<a name="link...">'
        nested inside it, or plain '<a id="chapNN">'), and some stories
        (e.g. 'A Voyage to Lilliput') contain their own nested sub-chapter
        anchors - so rather than guessing a prefix, we stop collecting
        paragraphs at the next anchor that's a *different story in this
        same book* per our own index, whatever its id/name actually is."""
        soup = self._get_book_soup(entry["url"])
        anchor = entry["anchor"]
        anchor_tag = soup.find(id=anchor) or soup.find(attrs={"name": anchor})
        if anchor_tag is None:
            raise StoryFetchError(f"anchor {anchor} not found in {entry['url']}")

        other_anchors = {
            e["anchor"] for e in self.index.values()
            if e["url"] == entry["url"] and e["anchor"] != anchor
        }

        paragraphs = []
        for el in anchor_tag.find_all_next():
            if el.name == "a":
                el_anchor = el.get("id") or el.get("name") or ""
                if el_anchor in other_anchors:
                    break
            if el.name == "p":
                text = el.get_text(" ", strip=True)
                if text:
                    paragraphs.append(text)
        if not paragraphs:
            raise StoryFetchError(f"no story text found at {entry['url']}#{anchor}")
        return paragraphs

    def _matches_collection_hint(self, hint):
        if not hint:
            return True
        _, score = match_one(hint.lower(), COLLECTION_ALIASES)
        return score >= COLLECTION_HINT_THRESHOLD

    def _matches_content_type(self, content_type):
        if not content_type:
            return True
        return content_type.lower() in CONTENT_TYPES

    def handle_search(self, message):
        if not self.index:
            return
        collection_hint = message.data.get("collection_hint")
        if not self._matches_collection_hint(collection_hint):
            return
        content_type = message.data.get("content_type")
        if not self._matches_content_type(content_type):
            return

        phrase = message.data.get("phrase")
        if phrase:
            title, confidence = match_one(phrase, list(self.index.keys()))
        elif collection_hint:
            # 'a story from Andrew Lang' with no specific title named -
            # only a sensible response if the hint was actually for us
            title = random.choice(list(self.index.keys()))
            confidence = 1.0
        else:
            return

        entry = self.index[title]
        self.bus.emit(message.reply(COMMON_READING_SEARCH_RESPONSE, {
            "skill_id": self.skill_id,
            "content_id": title,
            "title": title,
            "author": entry.get("author") or "Andrew Lang",
            "collection": entry.get("book") or "",
            "source": SOURCE_NAME,
            "confidence": confidence,
        }))

    def handle_fetch_content(self, message):
        content_id = message.data.get("content_id")
        entry = self.index.get(content_id)
        if not entry:
            self.bus.emit(message.reply(COMMON_READING_FETCH_CONTENT_RESPONSE, {"paragraphs": []}))
            return
        try:
            paragraphs = self.get_story_paragraphs(entry)
        except StoryFetchError as e:
            self.log.error(f"Could not fetch story '{content_id}': {e}")
            self.bus.emit(message.reply(COMMON_READING_FETCH_CONTENT_RESPONSE, {"paragraphs": []}))
            return
        self.bus.emit(message.reply(COMMON_READING_FETCH_CONTENT_RESPONSE, {"paragraphs": paragraphs}))
