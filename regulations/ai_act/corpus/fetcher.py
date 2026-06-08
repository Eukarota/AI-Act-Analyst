"""
EUR-Lex fetcher for the consolidated AI Act text.

Pulls CELEX:32024R1689 from the EUR-Lex HTML endpoint, strips tags, and
writes a plain-text snapshot under regulations/ai_act/corpus/raw/ keyed by
the language code. Returns the plain text plus the source URL.

The fetcher is conservative: a single HTTP GET with a polite User-Agent,
configurable timeout, and no retries beyond the standard httpx defaults. If
the network is unavailable, the index_corpus.py script falls back to the
local snapshot path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

EURLEX_HTML_URL_FMT = (
    "https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELEX:32024R1689"
)


@dataclass(frozen=True)
class FetchedCorpus:
    plain_text: str
    source_url: str
    language: str
    raw_html_path: Path
    plain_text_path: Path


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for selector in ("script", "style", "nav", "header", "footer"):
        for node in soup.select(selector):
            node.decompose()
    # Replace <br> with newline so paragraph structure survives.
    for br in soup.find_all("br"):
        br.replace_with("\n")
    # Promote block elements with explicit newlines.
    for block in soup.find_all(["p", "div", "li", "tr", "h1", "h2", "h3", "h4"]):
        block.insert_after("\n")
    text = soup.get_text(separator="\n")
    # Normalize whitespace.
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
    return "\n".join(cleaned).strip()


def fetch_consolidated(
    *,
    language: str = "EN",
    cache_dir: Path,
    timeout_seconds: float = 30.0,
) -> FetchedCorpus:
    cache_dir.mkdir(parents=True, exist_ok=True)
    url = EURLEX_HTML_URL_FMT.format(lang=language)
    raw_path = cache_dir / f"32024R1689.{language.lower()}.html"
    text_path = cache_dir / f"32024R1689.{language.lower()}.txt"

    headers = {
        "User-Agent": "Boussole/0.1 (compliance assessment; +sovereign AI Act build)",
        "Accept-Language": f"{language.lower()},en;q=0.5",
    }
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        html = response.text

    raw_path.write_text(html, encoding="utf-8")
    plain = _strip_html(html)
    text_path.write_text(plain, encoding="utf-8")

    return FetchedCorpus(
        plain_text=plain,
        source_url=url,
        language=language,
        raw_html_path=raw_path,
        plain_text_path=text_path,
    )


def load_local_snapshot(*, language: str, cache_dir: Path) -> FetchedCorpus:
    """Load a previously-fetched snapshot, or a manually-placed text file."""
    text_path = cache_dir / f"32024R1689.{language.lower()}.txt"
    raw_path = cache_dir / f"32024R1689.{language.lower()}.html"
    if not text_path.exists():
        raise FileNotFoundError(
            f"local AI Act snapshot not found at {text_path}; run index_corpus.py without --source local first"
        )
    return FetchedCorpus(
        plain_text=text_path.read_text(encoding="utf-8"),
        source_url=EURLEX_HTML_URL_FMT.format(lang=language),
        language=language,
        raw_html_path=raw_path,
        plain_text_path=text_path,
    )
