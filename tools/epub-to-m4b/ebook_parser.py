"""Parses EPUB files into ordered chapters of narratable plain text."""
from __future__ import annotations

import dataclasses
import re
import warnings
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from ebooklib import epub, ITEM_COVER, ITEM_DOCUMENT, ITEM_IMAGE

# EPUB content documents are XHTML; bs4's HTML parser handles them fine but
# warns about it on every file. We know, and mean to do it — silence it.
warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)


@dataclasses.dataclass
class Chapter:
    index: int
    title: str
    text: str

    @property
    def char_count(self) -> int:
        return len(self.text)


@dataclasses.dataclass
class Book:
    title: str
    author: str
    description: str
    cover_bytes: Optional[bytes]
    cover_media_type: Optional[str]
    chapters: list


_WS_RE = re.compile(r'[ \t\f\v]+')
_BLANKLINES_RE = re.compile(r'\n{3,}')


def _clean_text(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, 'lxml')
    for tag in soup(['script', 'style', 'sup']):
        # <sup> usually holds footnote markers, which read badly aloud.
        tag.decompose()
    for br in soup.find_all('br'):
        br.replace_with('\n')
    for block in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'li']):
        block.append('\n\n')

    text = soup.get_text()
    text = text.replace('\u00a0', ' ')
    text = text.replace('[PAUSE]', '\n\n')
    text = _WS_RE.sub(' ', text)
    text = _BLANKLINES_RE.sub('\n\n', text)
    lines = [ln.strip() for ln in text.split('\n')]
    text = '\n'.join(ln for ln in lines if ln)
    return text.strip()


def _chapter_title(soup: BeautifulSoup, fallback: str) -> str:
    for tag_name in ('h1', 'h2', 'h3'):
        tag = soup.find(tag_name)
        if tag and tag.get_text(strip=True):
            return tag.get_text(strip=True)
    title_tag = soup.find('title')
    if title_tag and title_tag.get_text(strip=True):
        return title_tag.get_text(strip=True)
    return fallback


def _find_cover(book: 'epub.EpubBook'):
    for item in book.get_items_of_type(ITEM_COVER):
        return item.get_content(), item.media_type

    meta_cover = book.get_metadata('OPF', 'cover')
    cover_id = meta_cover[0][1].get('content') if meta_cover else None
    if cover_id:
        item = book.get_item_with_id(cover_id)
        if item is not None:
            return item.get_content(), item.media_type

    for item in book.get_items_of_type(ITEM_IMAGE):
        if 'cover' in (item.get_name() or '').lower():
            return item.get_content(), item.media_type

    return None, None


def _meta(book: 'epub.EpubBook', namespace: str, name: str, default: str = '') -> str:
    values = book.get_metadata(namespace, name)
    if values:
        return values[0][0] or default
    return default


def parse_epub(epub_path: Path) -> Book:
    book = epub.read_epub(str(epub_path), options={'ignore_ncx': True})

    title = _meta(book, 'DC', 'title', epub_path.stem)
    author = _meta(book, 'DC', 'creator', 'Unknown Author')
    description = _meta(book, 'DC', 'description', '')
    cover_bytes, cover_media_type = _find_cover(book)

    chapters = []
    for item_id, _linear in book.spine:
        item = book.get_item_with_id(item_id)
        if item is None or item.get_type() != ITEM_DOCUMENT:
            continue
        raw = item.get_content().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(raw, 'lxml')
        chapter_title = _chapter_title(soup, fallback=f'Chapter {len(chapters) + 1}')
        text = _clean_text(raw)
        if not text:
            continue
        chapters.append(Chapter(index=len(chapters) + 1, title=chapter_title, text=text))

    return Book(
        title=title,
        author=author,
        description=description,
        cover_bytes=cover_bytes,
        cover_media_type=cover_media_type,
        chapters=chapters,
    )
