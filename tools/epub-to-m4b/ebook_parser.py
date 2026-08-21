"""Parses EPUB files into ordered chapters of narratable plain text."""
from __future__ import annotations

import dataclasses
import re
import warnings
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from ebooklib import epub, ITEM_COVER, ITEM_DOCUMENT, ITEM_IMAGE

import ocr

# EPUB content documents are XHTML; bs4's HTML parser handles them fine but
# warns about it on every file. We know, and mean to do it — silence it.
warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)

@dataclasses.dataclass
class Chapter:
    index: int
    title: str
    text: str
    from_ocr: bool = False

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
    # (chapter_index, chapter_title) pairs with an image OCR couldn't
    # contribute anything from — either unavailable, or ran and found
    # nothing (e.g. stylized lettering, or a purely decorative image).
    ocr_skipped: list = dataclasses.field(default_factory=list)


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


def _collect_chapter_images(book: 'epub.EpubBook', soup: BeautifulSoup, base_href: str) -> list:
    """Resolve every <img>/<image> reference in this chapter's HTML to raw
    image bytes, in document order — used as OCR input for picture-book
    pages where the words are drawn into the artwork."""
    hrefs = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            hrefs.append(src)
    for image in soup.find_all('image'):
        # SVG-wrapped full-page images are common in fixed-layout EPUBs.
        href = image.get('xlink:href') or image.get('href')
        if href:
            hrefs.append(href)

    image_bytes = []
    for href in hrefs:
        resolved = unquote(urljoin(base_href, href))
        item = book.get_item_with_href(resolved)
        if item is not None:
            image_bytes.append(item.get_content())
    return image_bytes


def parse_epub(epub_path: Path, use_ocr: bool = True) -> Book:
    book = epub.read_epub(str(epub_path), options={'ignore_ncx': True})

    title = _meta(book, 'DC', 'title', epub_path.stem)
    author = _meta(book, 'DC', 'creator', 'Unknown Author')
    description = _meta(book, 'DC', 'description', '')
    cover_bytes, cover_media_type = _find_cover(book)

    ocr_available = None  # lazily checked at most once
    chapters = []
    ocr_skipped = []

    for item_id, linear in book.spine:
        if str(linear).lower() == 'no':
            # Non-reading-order pages (cover wrapper, ads, etc.) — skip
            # them rather than narrating/OCR-ing a page nobody's meant to read.
            continue
        item = book.get_item_with_id(item_id)
        if item is None or item.get_type() != ITEM_DOCUMENT:
            continue
        raw = item.get_content().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(raw, 'lxml')
        chapter_title = _chapter_title(soup, fallback=f'Chapter {len(chapters) + 1}')
        text = _clean_text(raw)
        from_ocr = False

        if use_ocr:
            images = _collect_chapter_images(book, soup, item.get_name())
            if images:
                # Always OCR pages with images, even ones that already have
                # some real text — comics/graphic novels commonly have a
                # short real caption *and* dialogue drawn into the artwork
                # on the same page, so "already has text" doesn't mean
                # "nothing more to gain from OCR."
                if ocr_available is None:
                    ocr_available = ocr.is_available()
                if ocr_available:
                    ocr_text = ocr.ocr_images(images)
                    if ocr_text:
                        text = f'{text}\n\n{ocr_text}'.strip() if text else ocr_text
                        from_ocr = True
                    else:
                        ocr_skipped.append((len(chapters) + 1, chapter_title))
                else:
                    ocr_skipped.append((len(chapters) + 1, chapter_title))

        if not text:
            continue
        chapters.append(Chapter(index=len(chapters) + 1, title=chapter_title, text=text, from_ocr=from_ocr))

    return Book(
        title=title,
        author=author,
        description=description,
        cover_bytes=cover_bytes,
        cover_media_type=cover_media_type,
        chapters=chapters,
        ocr_skipped=ocr_skipped,
    )
