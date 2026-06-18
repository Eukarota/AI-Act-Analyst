"""
File ingest helpers for the intake endpoint.

Accepts a small set of common document formats and returns their plain text
so the frontend can pre-fill the system description textarea. The user keeps
authority: extracted text is shown in the form before any /assess call.

Supported formats:
- PDF (`application/pdf`)               via pypdf
- Plain text / Markdown                 decoded as UTF-8 (with fallback)
- Anything else                         rejected with HTTP 415

Defensive limits keep the endpoint safe to expose publicly:
- Max upload size: 5 MB
- Max characters returned: 20_000 (trimmed with notice)
- PDFs with more than 50 pages: rejected with HTTP 413
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

MAX_BYTES = 5 * 1024 * 1024
MAX_CHARS = 20_000
MAX_PDF_PAGES = 50


class FileTooLarge(ValueError):
    """Raised when the upload is over the size or page limit."""


class UnsupportedMediaType(ValueError):
    """Raised when the content type is neither PDF nor text."""


@dataclass(frozen=True)
class ExtractedText:
    text: str
    truncated: bool
    char_count: int
    page_count: int | None
    source_filename: str
    source_media_type: str


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_pdf(data: bytes) -> tuple[str, int]:
    # Local import keeps the backend importable even when the `report` extras
    # are not installed; pypdf only ships through the same extras group.
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    pages = reader.pages
    if len(pages) > MAX_PDF_PAGES:
        raise FileTooLarge(
            f"PDF has {len(pages)} pages; max accepted is {MAX_PDF_PAGES}."
        )
    chunks: list[str] = []
    for page in pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:  # pypdf can raise on malformed pages; skip them
            continue
    text = "\n\n".join(c.strip() for c in chunks if c and c.strip())
    return text, len(pages)


def extract(
    *,
    data: bytes,
    filename: str,
    content_type: str,
) -> ExtractedText:
    """Return the extracted plain text for a supported upload.

    Raises:
        FileTooLarge: upload exceeds MAX_BYTES or MAX_PDF_PAGES.
        UnsupportedMediaType: content type / extension not supported.
    """
    if len(data) > MAX_BYTES:
        raise FileTooLarge(
            f"upload is {len(data) // 1024} KB; max accepted is {MAX_BYTES // 1024} KB."
        )

    media_type = (content_type or "").lower().split(";", 1)[0].strip()
    is_pdf = media_type == "application/pdf" or filename.lower().endswith(".pdf")
    is_text = media_type.startswith("text/") or any(
        filename.lower().endswith(ext) for ext in (".txt", ".md", ".markdown")
    )

    if is_pdf:
        text, pages = _extract_pdf(data)
        page_count: int | None = pages
    elif is_text:
        text = _decode_text(data)
        page_count = None
    else:
        raise UnsupportedMediaType(
            f"content_type {media_type!r} not supported; accepted: application/pdf, text/*"
        )

    text = text.strip()
    truncated = False
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS].rstrip()
        truncated = True

    return ExtractedText(
        text=text,
        truncated=truncated,
        char_count=len(text),
        page_count=page_count,
        source_filename=filename,
        source_media_type=media_type or "application/octet-stream",
    )
