# epub-to-m4b

Turns an EPUB you've written into a single, chaptered `.m4b` audiobook you
can sell direct-to-consumer from your own site — no ACX/Audible exclusivity,
no distributor cut. Since you wrote the book, you already own full audio
rights; this just produces the file.

It reads the EPUB's spine (so chapter order matches the book), synthesizes
narration chapter-by-chapter with a text-to-speech engine of your choice,
and muxes everything into an M4B with embedded chapter markers, cover art,
and title/author/narrator metadata — the same format Apple Books, most
audiobook apps, and BookFunnel expect.

## 1. Install

```bash
cd tools/epub-to-m4b
pip install -r requirements.txt
```

You do **not** need to install `ffmpeg` separately — `imageio-ffmpeg` in
requirements.txt bundles a working binary automatically. If you already
have `ffmpeg` on your PATH, that one is used instead.

## 2. Pick a narration backend

| Backend | Quality | Cost (rough) | Setup |
|---|---|---|---|
| `openai` (default) | Very good | ~$0.015 / 1,000 chars | `export OPENAI_API_KEY=sk-...` |
| `elevenlabs` | Best, most natural | ~$0.18 / 1,000 chars (Pro-tier effective rate) | `export ELEVENLABS_API_KEY=...` |
| `inworld` | Very good, near ElevenLabs on quality | ~$0.01–$0.015 / 1,000 chars, pay-as-you-go, no subscription | `export INWORLD_API_KEY=...` |
| `local` | Robotic (espeak-based) | Free | `pip install pyttsx3` + a system TTS engine |

For anything you're actually going to sell, use `openai`, `elevenlabs`, or
`inworld`. `local` is only good for a quick QC pass or testing the pipeline
for free.

Pricing shifts often for all of these — the numbers above are a ballpark
from when this was written, not a quote. Check each provider's current
pricing page before committing to a full book.

Copy `.env.example` to `.env`, fill in the key(s) you need, and export it
into your shell before running the tool.

## 3. Preview before you spend anything

```bash
python epub_to_m4b.py my-book.epub --list-chapters
```

This parses the EPUB, prints every chapter it detected with a character
count, and a rough cost estimate per backend — no audio is generated and no
API is called. Use it to sanity-check that chapter detection looks right
(titles, count, no obviously-wrong front/back matter) before committing to
a full run.

## 4. Convert

```bash
python epub_to_m4b.py my-book.epub \
  --backend openai \
  --voice alloy \
  --narrator "Jane Doe" \
  -o my-book.m4b
```

This writes `my-book.m4b` plus a working directory (default
`.epub_to_m4b_build/<book title>/`) holding the per-chapter audio and a
`manifest.json` cache.

Useful flags:

- `--voice` — voice name/id for the chosen backend (e.g. OpenAI:
  `alloy`, `verse`, `ash`, ...; ElevenLabs: `rachel`, `adam`, `bella`,
  `antoni`, or any voice ID; Inworld: any voice name from Inworld's
  ListVoices endpoint, e.g. `Sarah`).
- `--cover path/to/cover.jpg` — use a specific cover instead of the one
  embedded in the EPUB.
- `--bitrate 64k` — AAC bitrate. 64k mono is standard for spoken word and
  keeps file size reasonable; drop to `32k` for smaller files, go higher
  only if you notice audible artifacts.
- `--max-chars 3000` — how much text goes into a single TTS request.
  Lower it if a backend rejects long inputs.
- `--resume` — re-run after an interruption or a fixed chapter without
  re-synthesizing (and re-paying for) chapters that haven't changed.
- `--only "3,7"` — synthesize just chapters 3 and 7 (e.g. to fix a
  mispronunciation), then re-run with `--resume` (no `--only`) to rebuild
  the full file using the cache.

## How it works

1. **Parse** — `ebook_parser.py` reads the EPUB spine in order, strips
   HTML/CSS down to clean narratable text per chapter, and pulls out
   title/author/description/cover from the EPUB's own metadata.
2. **Chunk** — `textutil.py` splits any chapter longer than `--max-chars`
   on sentence boundaries, so no request gets cut mid-sentence and no TTS
   provider's input-length limit gets hit.
3. **Narrate** — `tts_backends.py` sends each chunk to the chosen TTS
   engine and normalizes the result to a consistent mono WAV.
4. **Assemble** — `audio_build.py` shells out to `ffmpeg` to encode each
   chapter to AAC, concatenate them in order, compute chapter timestamps,
   and mux in chapter markers, cover art, and metadata as a single `.m4b`.

## Selling it direct-to-consumer

A few practical notes since this is going straight to your own site rather
than through Audible/ACX:

- **Delivery**: M4B plays natively in Apple Books, most Android audiobook
  apps (via Smart AudioBook Player, etc.), and VLC. For DTC delivery, a
  signed/expiring download link (most storefronts below handle this for
  you) beats a plain public URL.
- **Storefronts that take digital downloads with no dev work**: Payhip,
  Gumroad, SendOwl, or BookFunnel (BookFunnel is audiobook-friendly and
  handles delivery + basic DRM-lite watermarking). Shopify also supports
  digital products if your site is already on Shopify.
- **File size**: at 64k mono AAC, expect roughly 28 MB/hour of audio —
  check your storefront's upload size limit before choosing a bitrate.
- **QC before publishing**: listen to the first and last couple of minutes
  of each chapter (mispronunciations are the most common issue with TTS
  narration — fix the source text or use `--voice`/SSML-style phonetic
  spelling tricks, then `--only` + `--resume` to patch just that chapter).
- You still own full audio rights to your own book, so nothing here
  requires ACX/Audible enrollment — this pipeline is independent of that
  distribution channel entirely.

## Adding another TTS provider

Subclass `TTSBackend` in `tts_backends.py`, implement
`synthesize(self, text, out_path, voice)`, and register it in the
`_BACKENDS` dict at the bottom of that file. Everything else (chunking,
caching, encoding, chapter markers) is provider-agnostic.
