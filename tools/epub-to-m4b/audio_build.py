"""ffmpeg-backed helpers: normalizing, encoding, concatenation, chapter
markers, cover art, and metadata tagging for the final M4B."""
from __future__ import annotations

import subprocess
from pathlib import Path


def find_ffmpeg() -> str:
    import shutil

    exe = shutil.which('ffmpeg')
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    raise RuntimeError(
        'ffmpeg was not found on PATH. Install it (e.g. `brew install ffmpeg` / '
        '`apt install ffmpeg`) or run `pip install imageio-ffmpeg` for a bundled binary.'
    )


def _run(cmd: list) -> None:
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(
            f'Command failed ({result.returncode}): {" ".join(str(c) for c in cmd)}\n'
            f'{result.stderr.decode(errors="ignore")}'
        )


def normalize_to_wav(ffmpeg: str, src: Path, dst: Path, sample_rate: int) -> None:
    """Decode any TTS output into a consistent mono WAV so chunks concatenate cleanly."""
    _run([
        ffmpeg, '-y', '-loglevel', 'error',
        '-i', str(src),
        '-ar', str(sample_rate), '-ac', '1',
        str(dst),
    ])


def encode_to_m4a(ffmpeg: str, src: Path, dst: Path, bitrate: str, sample_rate: int, channels: int) -> None:
    _run([
        ffmpeg, '-y', '-loglevel', 'error',
        '-i', str(src),
        '-vn',
        '-c:a', 'aac', '-b:a', bitrate, '-ar', str(sample_rate), '-ac', str(channels),
        str(dst),
    ])


def get_duration_ms(ffmpeg: str, path: Path) -> int:
    result = subprocess.run([ffmpeg, '-i', str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderr = result.stderr.decode(errors='ignore')
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith('Duration:'):
            timestamp = line.split(',')[0].replace('Duration:', '').strip()
            hh, mm, ss = timestamp.split(':')
            seconds = int(hh) * 3600 + int(mm) * 60 + float(ss)
            return int(seconds * 1000)
    raise RuntimeError(f'Could not determine duration of {path}')


def concat_audio(ffmpeg: str, parts: list, list_file: Path, dst: Path) -> None:
    list_file.write_text(
        '\n'.join(f"file '{p.resolve().as_posix()}'" for p in parts),
        encoding='utf-8',
    )
    _run([
        ffmpeg, '-y', '-loglevel', 'error',
        '-f', 'concat', '-safe', '0', '-i', str(list_file),
        '-c', 'copy',
        str(dst),
    ])


def _ffmeta_escape(value: str) -> str:
    return (
        value.replace('\\', '\\\\')
        .replace('=', '\\=')
        .replace(';', '\\;')
        .replace('#', '\\#')
        .replace('\n', '\\\n')
    )


def write_chapters_metadata(meta_path: Path, title: str, author: str, chapters: list) -> None:
    """`chapters` is a list of (title, start_ms, end_ms) tuples."""
    lines = [
        ';FFMETADATA1',
        f'title={_ffmeta_escape(title)}',
        f'artist={_ffmeta_escape(author)}',
        f'album={_ffmeta_escape(title)}',
        'genre=Audiobook',
    ]
    for chap_title, start_ms, end_ms in chapters:
        lines += [
            '',
            '[CHAPTER]',
            'TIMEBASE=1/1000',
            f'START={start_ms}',
            f'END={end_ms}',
            f'title={_ffmeta_escape(chap_title)}',
        ]
    meta_path.write_text('\n'.join(lines), encoding='utf-8')


def mux_final_m4b(
    ffmpeg: str,
    audio_path: Path,
    metadata_path: Path,
    cover_path,
    output_path: Path,
    extra_tags: dict,
) -> None:
    tmp_with_chapters = output_path.with_suffix('.chapters.m4a')
    _run([
        ffmpeg, '-y', '-loglevel', 'error',
        '-i', str(audio_path),
        '-i', str(metadata_path),
        '-map_metadata', '1',
        '-c', 'copy',
        str(tmp_with_chapters),
    ])

    cmd = [ffmpeg, '-y', '-loglevel', 'error', '-i', str(tmp_with_chapters)]
    if cover_path:
        cmd += [
            '-i', str(cover_path), '-map', '0', '-map', '1',
            '-c', 'copy', '-disposition:v:0', 'attached_pic',
            '-metadata:s:v', 'title=Cover', '-metadata:s:v', 'comment=Cover (front)',
        ]
    else:
        cmd += ['-map', '0', '-c', 'copy']
    for key, value in extra_tags.items():
        cmd += ['-metadata', f'{key}={value}']
    cmd += ['-f', 'mp4', str(output_path)]
    _run(cmd)
    tmp_with_chapters.unlink(missing_ok=True)
