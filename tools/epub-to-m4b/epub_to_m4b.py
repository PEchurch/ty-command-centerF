#!/usr/bin/env python3
"""
epub_to_m4b.py — Convert an EPUB manuscript into a single chaptered M4B
audiobook, ready to sell direct-to-consumer from your own website
(Payhip, Gumroad, Shopify digital downloads, a signed download link, etc).

Quick start:
    pip install -r requirements.txt
    export OPENAI_API_KEY=sk-...
    python epub_to_m4b.py my-book.epub --backend openai --voice alloy

Preview chapters and get a cost estimate before spending anything:
    python epub_to_m4b.py my-book.epub --list-chapters

See README.md for backend options, chunking/resume behavior, and
selling tips.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import audio_build as ab
from ebook_parser import Book, parse_epub
from textutil import split_into_chunks
from tts_backends import get_backend

# Rough published price per 1,000 characters, USD. Providers change pricing
# often — treat this only as a ballpark before you commit to a full run.
_COST_PER_1K_CHARS = {
    'openai': 0.015,
    'elevenlabs': 0.18,
    'local': 0.0,
}


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode('utf-8')).hexdigest()[:12]


def cmd_list_chapters(book: Book) -> None:
    total_chars = sum(ch.char_count for ch in book.chapters)
    print(f'{book.title} — {book.author}')
    print(f'{len(book.chapters)} chapters, {total_chars:,} characters total\n')
    for ch in book.chapters:
        print(f'  [{ch.index:>3}] {ch.title[:60]:<60} {ch.char_count:>7,} chars')
    print()
    for backend, rate in _COST_PER_1K_CHARS.items():
        est = total_chars / 1000 * rate
        print(f'  est. cost @ {backend:<11} ${est:,.2f}')


def synthesize_book(
    book: Book,
    backend_name: str,
    voice: str,
    workdir: Path,
    max_chars: int,
    sample_rate: int,
    only_indices,
    resume: bool,
):
    backend = get_backend(backend_name)
    ffmpeg = ab.find_ffmpeg()
    workdir.mkdir(parents=True, exist_ok=True)
    manifest_path = workdir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    chapter_files = []
    for ch in book.chapters:
        if only_indices and ch.index not in only_indices:
            continue

        chapter_dir = workdir / f'chapter_{ch.index:03d}'
        chapter_dir.mkdir(exist_ok=True)
        out_path = chapter_dir / 'chapter.wav'
        text_hash = _sha1(ch.text)

        if resume and manifest.get(str(ch.index)) == text_hash and out_path.exists():
            print(f'  [{ch.index:>3}] {ch.title} — cached, skipping')
        else:
            print(f'  [{ch.index:>3}] {ch.title} — synthesizing ({ch.char_count:,} chars)...')
            chunks = split_into_chunks(ch.text, max_chars=max_chars)
            part_paths = []
            for i, chunk in enumerate(chunks):
                raw_path = chapter_dir / f'part_{i:03d}.raw'
                backend.synthesize(chunk, raw_path, voice)
                wav_path = chapter_dir / f'part_{i:03d}.wav'
                ab.normalize_to_wav(ffmpeg, raw_path, wav_path, sample_rate)
                raw_path.unlink(missing_ok=True)
                part_paths.append(wav_path)

            if len(part_paths) == 1:
                part_paths[0].replace(out_path)
            else:
                ab.concat_audio(ffmpeg, part_paths, chapter_dir / 'concat_list.txt', out_path)

            manifest[str(ch.index)] = text_hash
            manifest_path.write_text(json.dumps(manifest, indent=2))

        chapter_files.append((ch.title, out_path))

    return chapter_files


def build_audiobook(
    book: Book,
    chapter_files,
    output_path: Path,
    workdir: Path,
    bitrate: str,
    sample_rate: int,
    channels: int,
    cover_override,
    narrator: str,
) -> None:
    ffmpeg = ab.find_ffmpeg()
    encoded_dir = workdir / 'encoded'
    encoded_dir.mkdir(exist_ok=True)

    encoded_parts = []
    durations_ms = []
    for i, (title, src) in enumerate(chapter_files, start=1):
        dst = encoded_dir / f'{i:03d}.m4a'
        print(f'  encoding {title} -> {dst.name}')
        ab.encode_to_m4a(ffmpeg, src, dst, bitrate, sample_rate, channels)
        encoded_parts.append(dst)
        durations_ms.append(ab.get_duration_ms(ffmpeg, dst))

    combined_path = workdir / 'combined.m4a'
    print('  concatenating chapters...')
    ab.concat_audio(ffmpeg, encoded_parts, workdir / 'concat_list.txt', combined_path)

    chapter_marks = []
    cursor = 0
    for (title, _src), dur in zip(chapter_files, durations_ms):
        chapter_marks.append((title, cursor, cursor + dur))
        cursor += dur

    metadata_path = workdir / 'chapters.ffmeta'
    ab.write_chapters_metadata(metadata_path, book.title, book.author, chapter_marks)

    cover_path = None
    if cover_override:
        cover_path = cover_override
    elif book.cover_bytes:
        ext = '.png' if book.cover_media_type and 'png' in book.cover_media_type else '.jpg'
        cover_path = workdir / f'cover{ext}'
        cover_path.write_bytes(book.cover_bytes)

    extra_tags = {'title': book.title, 'artist': book.author, 'album_artist': book.author}
    if narrator:
        extra_tags['composer'] = narrator  # most M4B players surface 'composer' as the narrator
    if book.description:
        extra_tags['description'] = book.description

    print(f'  muxing final audiobook -> {output_path}')
    ab.mux_final_m4b(ffmpeg, combined_path, metadata_path, cover_path, output_path, extra_tags)

    total_seconds = cursor / 1000
    print(f'\nDone: {output_path} ({total_seconds / 60:.1f} min, {len(chapter_files)} chapters)')


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Convert an EPUB into a sellable M4B audiobook.')
    p.add_argument('epub', type=Path, help='Path to the source .epub file')
    p.add_argument('-o', '--output', type=Path, default=None, help='Output .m4b path (default: <epub name>.m4b)')
    p.add_argument('--backend', choices=['openai', 'elevenlabs', 'local'], default='openai', help='TTS engine to narrate with')
    p.add_argument('--voice', default='', help='Voice name/id for the chosen backend')
    p.add_argument('--narrator', default='', help='Narrator name to tag into the file metadata')
    p.add_argument('--cover', type=Path, default=None, help='Override cover image (jpg/png); default is the cover embedded in the EPUB')
    p.add_argument('--bitrate', default='64k', help='AAC audio bitrate (default: 64k, standard for spoken word)')
    p.add_argument('--sample-rate', type=int, default=44100)
    p.add_argument('--channels', type=int, default=1, help='1 = mono (recommended for audiobooks), 2 = stereo')
    p.add_argument('--max-chars', type=int, default=3000, help='Max characters per TTS request chunk')
    p.add_argument('--workdir', type=Path, default=None, help='Directory for intermediate files (default: .epub_to_m4b_build/<book title>)')
    p.add_argument('--resume', action='store_true', help='Reuse already-synthesized chapter audio from a previous run')
    p.add_argument('--only', default='', help='Comma-separated chapter indices to (re)synthesize, e.g. "3,7,8"')
    p.add_argument('--list-chapters', action='store_true', help='Print detected chapters, char counts, and a cost estimate, then exit')
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    if not args.epub.exists():
        print(f'error: {args.epub} not found', file=sys.stderr)
        return 1

    print(f'Parsing {args.epub}...')
    book = parse_epub(args.epub)

    if not book.chapters:
        print('error: no narratable chapters were found in this EPUB', file=sys.stderr)
        return 1

    if args.list_chapters:
        cmd_list_chapters(book)
        return 0

    output_path = args.output or args.epub.with_suffix('.m4b')
    workdir = args.workdir or Path('.epub_to_m4b_build') / book.title.replace('/', '-')
    only_indices = {int(x) for x in args.only.split(',') if x.strip()} if args.only else None

    print(f'{book.title} by {book.author} — {len(book.chapters)} chapters')
    print(f'Backend: {args.backend}   Voice: {args.voice or "(default)"}   Workdir: {workdir}\n')

    try:
        chapter_files = synthesize_book(
            book, args.backend, args.voice, workdir, args.max_chars, args.sample_rate, only_indices, args.resume,
        )

        if only_indices:
            print('\n--only was set; stopping after synthesizing the selected chapters (no final M4B built).')
            print('Re-run without --only, with --resume, to build the full audiobook using the cached chapters.')
            return 0

        build_audiobook(
            book, chapter_files, output_path, workdir,
            args.bitrate, args.sample_rate, args.channels, args.cover, args.narrator,
        )
    except (RuntimeError, ValueError) as exc:
        print(f'\nerror: {exc}', file=sys.stderr)
        print(f'(partial progress, if any, is cached in {workdir} — fix the issue above and re-run with --resume)', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
