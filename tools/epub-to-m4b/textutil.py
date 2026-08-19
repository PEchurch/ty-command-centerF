"""Text chunking utilities for TTS input-length limits."""
from __future__ import annotations

import re

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')


def split_into_chunks(text: str, max_chars: int = 3000) -> list:
    """Split `text` into chunks no longer than `max_chars`, breaking on
    sentence boundaries where possible so TTS output doesn't cut off
    mid-sentence."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current = ''
    for paragraph in text.split('\n\n'):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        for sentence in _SENTENCE_SPLIT_RE.split(paragraph):
            candidate = f'{current} {sentence}'.strip() if current else sentence
            if len(candidate) > max_chars and current:
                chunks.append(current.strip())
                current = sentence
            else:
                current = candidate
            # A single sentence longer than max_chars still needs a hard split.
            while len(current) > max_chars:
                chunks.append(current[:max_chars].strip())
                current = current[max_chars:]
    if current.strip():
        chunks.append(current.strip())
    return chunks
