"""
Fetcher for the consolidated AI Act text.

Source: the EU Publications Office cellar (publications.europa.eu). The
EUR-Lex HTML endpoint sits behind an AWS WAF JS challenge and refuses
non-browser clients (returns HTTP 202 with a challenge page and 0 bytes of
text). The cellar exposes the same Official Journal XHTML directly, without
the WAF, keyed by a stable cellar UUID + a per-language manifestation slot.

We pull the XHTML, strip presentation, normalize whitespace (including the
non-breaking spaces the OJ converter emits between "Article" and the number),
and write a plain-text snapshot under regulations/ai_act/corpus/raw/ keyed by
language. The result is suitable input for parser.parse_consolidated_text.

The fetcher fails loud. A WAF challenge body, a truncated response, or any
status outside 2xx raises CorpusFetchError; we never silently write a
zero-byte snapshot, because the downstream indexer would then happily produce
an empty corpus and the agent would cite nothing but defaults.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# Stable cellar UUID for Regulation (EU) 2024/1689, OJ L of 12 July 2024.
_CELLAR_UUID = "dc8116a1-3fe6-11ef-865a-01aa75ed71a1"

# Manifestation slots per language (the .NNNN.NN segment after the UUID).
# These are the OJ rendition keys; mapping observed at 2026-06-16 against the
# Publications Office cellar. New languages are added here.
_CELLAR_LANG_SLOT: dict[str, str] = {
    "EN": "0006.03",
    "FR": "0009.03",
}

_CELLAR_URL_FMT = "https://publications.europa.eu/resource/cellar/{uuid}.{slot}/DOC_1"

# Kept as a stable "where the text comes from" string surfaced in citations.
EURLEX_HTML_URL_FMT = (
    "https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELEX:32024R1689"
)

# Bodies smaller than this are treated as failed fetches (the consolidated
# AI Act is ~560 KB EN / ~660 KB FR; anything in single-digit KB is either a
# WAF challenge page or an error stub).
_MIN_PLAIN_TEXT_BYTES = 100_000


class CorpusFetchError(RuntimeError):
    """Raised when the consolidated text cannot be retrieved or looks invalid."""


@dataclass(frozen=True)
class FetchedCorpus:
    plain_text: str
    source_url: str
    language: str
    raw_html_path: Path
    plain_text_path: Path


def _normalize(text: str) -> str:
    # OJ XHTML uses non-breaking spaces between "Article" and the number, and
    # in many other places (between digits in section refs, after paragraph
    # numbers, etc.). Normalize them so the regex parser sees a plain ASCII
    # space.
    text = text.replace("\xa0", " ")
    # Collapse repeated blank lines but preserve paragraph breaks.
    lines = [ln.rstrip() for ln in text.splitlines()]
    cleaned: list[str] = []
    blank = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
            if blank <= 1:
                cleaned.append("")
        else:
            blank = 0
            cleaned.append(stripped)
    # Collapse multiple spaces but only within lines.
    cleaned = [re.sub(r" {2,}", " ", ln) for ln in cleaned]
    return "\n".join(cleaned).strip()


def _strip_xhtml(xhtml: str) -> str:
    # The cellar serves OJ acts as XHTML; pass it through lxml's XML parser to
    # avoid the bs4 XMLParsedAsHTMLWarning and to keep namespacing sane.
    soup = BeautifulSoup(xhtml, "lxml-xml")
    for selector in ("script", "style"):
        for node in soup.select(selector):
            node.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "li", "tr", "h1", "h2", "h3", "h4"]):
        block.insert_after("\n")
    return _normalize(soup.get_text(separator="\n"))


def _looks_like_waf_challenge(body: str) -> bool:
    head = body[:4096].lower()
    return any(
        token in head
        for token in (
            "awswafintegration",
            "awswafcookiedomainlist",
            "challenge-container",
            "challenge.js",
        )
    )


def fetch_consolidated(
    *,
    language: str = "EN",
    cache_dir: Path,
    timeout_seconds: float = 60.0,
) -> FetchedCorpus:
    lang = language.upper()
    if lang not in _CELLAR_LANG_SLOT:
        raise CorpusFetchError(
            f"no cellar slot configured for language {language!r}; "
            f"add it to _CELLAR_LANG_SLOT in fetcher.py"
        )
    cache_dir.mkdir(parents=True, exist_ok=True)
    url = _CELLAR_URL_FMT.format(uuid=_CELLAR_UUID, slot=_CELLAR_LANG_SLOT[lang])
    citation_url = EURLEX_HTML_URL_FMT.format(lang=lang)
    raw_path = cache_dir / f"32024R1689.{lang.lower()}.html"
    text_path = cache_dir / f"32024R1689.{lang.lower()}.txt"

    headers = {
        # The cellar accepts a plain UA; we use a browser-like string anyway
        # because some intermediate caches refuse non-browser callers.
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
        ),
        "Accept": "application/xhtml+xml,text/html,*/*;q=0.5",
        "Accept-Language": f"{lang.lower()},en;q=0.5",
    }
    with httpx.Client(
        timeout=timeout_seconds,
        follow_redirects=True,
        headers=headers,
    ) as client:
        response = client.get(url)
    if response.status_code != 200:
        raise CorpusFetchError(
            f"cellar returned HTTP {response.status_code} for {url!r} "
            f"(body={len(response.content)} bytes); refusing to write a partial snapshot"
        )
    xhtml = response.text
    if _looks_like_waf_challenge(xhtml):
        raise CorpusFetchError(
            "cellar response looks like a WAF challenge page; "
            "the consolidated text was not retrieved"
        )

    raw_path.write_text(xhtml, encoding="utf-8")
    plain = _strip_xhtml(xhtml)
    if len(plain.encode("utf-8")) < _MIN_PLAIN_TEXT_BYTES:
        raise CorpusFetchError(
            f"stripped text is too short ({len(plain)} chars) to be the AI Act; "
            f"refusing to overwrite a known-good snapshot. URL={url!r}"
        )
    text_path.write_text(plain, encoding="utf-8")

    return FetchedCorpus(
        plain_text=plain,
        source_url=citation_url,
        language=lang,
        raw_html_path=raw_path,
        plain_text_path=text_path,
    )


def load_local_snapshot(*, language: str, cache_dir: Path) -> FetchedCorpus:
    """Load a previously-fetched snapshot, or a manually-placed text file."""
    lang = language.upper()
    text_path = cache_dir / f"32024R1689.{lang.lower()}.txt"
    raw_path = cache_dir / f"32024R1689.{lang.lower()}.html"
    if not text_path.exists():
        raise CorpusFetchError(
            f"local AI Act snapshot not found at {text_path}; "
            f"run scripts/index_corpus.py without --source local first"
        )
    plain = text_path.read_text(encoding="utf-8")
    if len(plain.encode("utf-8")) < _MIN_PLAIN_TEXT_BYTES:
        raise CorpusFetchError(
            f"local snapshot at {text_path} is too short ({len(plain)} chars) "
            f"to be the consolidated AI Act; delete it and re-fetch"
        )
    return FetchedCorpus(
        plain_text=plain,
        source_url=EURLEX_HTML_URL_FMT.format(lang=lang),
        language=lang,
        raw_html_path=raw_path,
        plain_text_path=text_path,
    )
