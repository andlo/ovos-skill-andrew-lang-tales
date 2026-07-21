#!/usr/bin/env python3
"""Build locale/en-us/index.json from Andrew Lang's Fairy Books master
index (Project Gutenberg ebook #30580, produced by David Widger).

This is a one-time/occasional *build-time* script, not something the skill
runs live - per Project Gutenberg's robot access policy, we fetch this page
once here, not on every user request. See:
https://www.gutenberg.org/policy/robot_access.html

Usage:
    python3 scripts/build_lang_index.py
"""
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

INDEX_URL = "https://www.gutenberg.org/files/30580/30580-h/30580-h.htm"
OUT_PATH = Path(__file__).resolve().parents[1] / "locale" / "en-us" / "index.json"

BOOK_NAMES = [
    "Blue Fairy Book", "Red Fairy Book", "Yellow Fairy Book",
    "Violet Fairy Book", "Crimson Fairy Book", "Orange Fairy Book",
    "Brown Fairy Book", "Lilac Fairy Book", "Pink Fairy Book",
    "Grey Fairy Book", "Green Fairy Book", "Olive Fairy Book",
]

# Olive Fairy Book (Gutenberg id 27826) uses a different, page-number-based
# anchor scheme (#Page_1, #Page_9, ...) instead of the #2H_4_NNNN per-story
# anchors every other book uses - excluded from v1, tracked as a follow-up.
EXCLUDED_BOOK_IDS = {"27826"}

HREF_RE = re.compile(
    r"gutenberg\.org/files/(\d+)/\d+-h/(\d+-h\.htm)#([\w.]+)"
)


def fetch_index_html():
    r = requests.get(INDEX_URL, timeout=30)
    r.raise_for_status()
    return r.text


def parse(html):
    soup = BeautifulSoup(html, "html.parser")

    marker = soup.find(string=re.compile("ALPHABETICAL LISTING"))
    if marker:
        for el in list(marker.find_all_next()):
            el.decompose()
        marker.extract()

    entries = {}
    book_idx = -1
    seen_books = set()

    for el in soup.find_all("a"):
        text = " ".join(el.get_text(strip=True).split())
        href = el.get("href", "")
        m = HREF_RE.search(href)
        if not m:
            continue
        book_id, filename, anchor = m.groups()
        if book_id in EXCLUDED_BOOK_IDS:
            continue
        url = f"https://www.gutenberg.org/files/{book_id}/{book_id}-h/{filename}"

        if book_id not in seen_books:
            seen_books.add(book_id)
            book_idx += 1
        book_name = BOOK_NAMES[book_idx] if book_idx < len(BOOK_NAMES) else f"book_{book_id}"

        if not text or (text.isupper() and len(text) > 20):
            continue
        if text.lower() in (name.lower() for name in BOOK_NAMES):
            continue  # front-matter link (book's own title), not a story

        entries[text] = {"url": url, "anchor": f"link{anchor}", "book": book_name, "author": "Andrew Lang"}

    return entries


def repair_and_validate(entries):
    """David Widger's master index (from 2009/2019) points to '#2H_4_NNNN'
    anchors, but some of the individual book files have since been
    re-published on Gutenberg with a different internal anchor scheme
    (e.g. '#chap01') - the old anchors no longer resolve for those books.

    For any book where the master index's anchors don't resolve, fall back
    to that book's own table-of-contents links ('<a href="#chapNN">TITLE</a>')
    to rebuild a correct title -> anchor mapping. Anything that still can't
    be resolved after that is dropped, rather than shipping a broken link.
    """
    from collections import defaultdict

    by_url = defaultdict(list)
    for title, e in entries.items():
        by_url[e["url"]].append(title)

    soup_cache = {}

    def get_soup(url):
        if url not in soup_cache:
            r = requests.get(url, timeout=30)
            r.encoding = r.apparent_encoding
            soup_cache[url] = BeautifulSoup(r.text, "html.parser")
        return soup_cache[url]

    def resolves(soup, anchor):
        return soup.find(id=anchor) is not None or soup.find(attrs={"name": anchor}) is not None

    repaired = 0
    dropped = []

    for url, titles in by_url.items():
        soup = get_soup(url)
        if resolves(soup, entries[titles[0]]["anchor"]):
            continue  # this book's anchors are fine, nothing to do

        print(f"  anchors stale for {url} - repairing via the book's own contents table")
        toc = {}
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("#"):
                continue
            text = " ".join(a.get_text(strip=True).split()).lower()
            if text:
                toc[text] = href[1:]

        for title in titles:
            match = toc.get(title.lower())
            if match and resolves(soup, match):
                entries[title]["anchor"] = match
                repaired += 1
            else:
                dropped.append(title)

    for title in dropped:
        del entries[title]

    return repaired, dropped


def validate_extraction(entries, soup_cache=None):
    """Final sanity pass: actually extract each story's paragraphs using
    the same logic as WorldTales.get_story_paragraphs() in __init__.py, and
    drop any entry that doesn't yield real text. Keeps this build script as
    the single source of truth for 'is this story actually usable'."""
    soup_cache = soup_cache if soup_cache is not None else {}

    def get_soup(url):
        if url not in soup_cache:
            r = requests.get(url, timeout=30)
            r.encoding = r.apparent_encoding
            soup_cache[url] = BeautifulSoup(r.text, "html.parser")
        return soup_cache[url]

    dropped = []
    for title, entry in list(entries.items()):
        soup = get_soup(entry["url"])
        anchor = entry["anchor"]
        anchor_tag = soup.find(id=anchor) or soup.find(attrs={"name": anchor})
        if anchor_tag is None:
            dropped.append(title)
            continue
        other_anchors = {
            e["anchor"] for e in entries.values()
            if e["url"] == entry["url"] and e["anchor"] != anchor
        }
        found_text = False
        for el in anchor_tag.find_all_next():
            if el.name == "a":
                el_anchor = el.get("id") or el.get("name") or ""
                if el_anchor in other_anchors:
                    break
            if el.name == "p" and el.get_text(strip=True):
                found_text = True
                break
        if not found_text:
            dropped.append(title)

    for title in dropped:
        del entries[title]

    return dropped


def main():
    print(f"Fetching {INDEX_URL} ...")
    html = fetch_index_html()
    entries = parse(html)
    print(f"Parsed {len(entries)} stories from the master index")

    repaired, dropped = repair_and_validate(entries)
    print(f"Repaired {repaired} stale anchors via book contents tables")
    if dropped:
        print(f"Dropped {len(dropped)} stories whose anchor could not be resolved: {dropped}")

    extraction_dropped = validate_extraction(entries)
    if extraction_dropped:
        print(f"Dropped {len(extraction_dropped)} stories with no extractable text: {extraction_dropped}")

    print(f"Final story count: {len(entries)}")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    sys.exit(main())
