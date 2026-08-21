"""Optional OCR fallback for picture-book pages where the words are drawn
directly into the illustration image rather than present as real text in
the EPUB's HTML.

Needs both the `pytesseract` + `Pillow` Python packages (requirements.txt)
AND the Tesseract OCR engine installed as a separate system program — pip
can't install Tesseract itself. See README.md for the install link.
"""
from __future__ import annotations

import io
import os


def _configure_tesseract_cmd() -> None:
    """Point pytesseract at a specific tesseract.exe if TESSERACT_CMD is
    set — useful on Windows when the installer didn't add it to PATH."""
    tess_cmd = os.environ.get('TESSERACT_CMD')
    if tess_cmd:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = tess_cmd


def is_available() -> bool:
    try:
        import pytesseract

        _configure_tesseract_cmd()
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_images(image_bytes_list) -> str:
    """OCR a list of raw image byte strings, in order, and join the results."""
    import pytesseract
    from PIL import Image

    _configure_tesseract_cmd()

    texts = []
    for raw in image_bytes_list:
        try:
            img = Image.open(io.BytesIO(raw))
            text = pytesseract.image_to_string(img).strip()
        except Exception:
            continue
        if text:
            texts.append(text)
    return '\n\n'.join(texts)
