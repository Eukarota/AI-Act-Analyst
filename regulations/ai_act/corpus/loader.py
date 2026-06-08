"""
AiActCorpusLoader: implements the CorpusLoader Protocol.

Combines fetch (or local snapshot) + parse + chunk into a stream of
(text, Citation, retrieval_scope) triples for the indexer.

corpus_version is content-derived: a short hash of the plain text plus the
language. Re-fetching identical text yields an identical version, so
re-indexing is a no-op when nothing has changed (idempotency requirement
from CLAUDE.md section 12.4).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from backend.agent.state import Citation
from backend.rag.chunking import RawSection, split_into_chunks
from regulations.ai_act.corpus.fetcher import (
    EURLEX_HTML_URL_FMT,
    FetchedCorpus,
    fetch_consolidated,
    load_local_snapshot,
)
from regulations.ai_act.corpus.parser import (
    ParsedSection,
    SectionKind,
    parse_consolidated_text,
)
from regulations.ai_act.corpus.scope import scope_for_citation

CELEX_ID = "32024R1689"


@dataclass
class AiActChunkerConfig:
    """Chunker knobs satisfying the ChunkerConfig Protocol.

    Not frozen so the Protocol's plain (settable) attribute slots match the
    runtime shape. Treat instances as immutable in callers.
    """

    max_chars: int = 1800
    overlap_chars: int = 0
    index_recitals_separately: bool = True


class AiActCorpusLoader:
    """
    CorpusLoader implementation.

    Construct with a directory under which the raw snapshot lives; the loader
    will fetch on first use or read from disk when offline.
    """

    def __init__(
        self,
        *,
        cache_dir: Path | None = None,
        language: str = "EN",
        prefer_local: bool = False,
        fetched: FetchedCorpus | None = None,
    ) -> None:
        self.language = language
        self.cache_dir = cache_dir or _default_cache_dir()
        self.prefer_local = prefer_local
        self._fetched: FetchedCorpus | None = fetched
        self._parsed: list[ParsedSection] | None = None
        self._version: str | None = None

    @classmethod
    def from_text(cls, text: str, *, language: str = "EN") -> AiActCorpusLoader:
        """Construct from in-memory text (test convenience)."""
        loader = cls(language=language)
        loader._fetched = FetchedCorpus(
            plain_text=text,
            source_url=EURLEX_HTML_URL_FMT.format(lang=language),
            language=language,
            raw_html_path=Path("/dev/null"),
            plain_text_path=Path("/dev/null"),
        )
        return loader

    def _ensure_fetched(self) -> FetchedCorpus:
        if self._fetched is not None:
            return self._fetched
        if self.prefer_local:
            self._fetched = load_local_snapshot(language=self.language, cache_dir=self.cache_dir)
        else:
            try:
                self._fetched = fetch_consolidated(language=self.language, cache_dir=self.cache_dir)
            except Exception:
                # Fall back to local snapshot if present.
                self._fetched = load_local_snapshot(
                    language=self.language, cache_dir=self.cache_dir
                )
        return self._fetched

    def _ensure_parsed(self) -> list[ParsedSection]:
        if self._parsed is None:
            fetched = self._ensure_fetched()
            self._parsed = parse_consolidated_text(fetched.plain_text)
        return self._parsed

    def corpus_version(self) -> str:
        if self._version is None:
            fetched = self._ensure_fetched()
            digest = hashlib.sha256(fetched.plain_text.encode("utf-8")).hexdigest()[:12]
            self._version = f"ai_act-{self.language.lower()}-{digest}"
        return self._version

    def iter_chunks(self) -> Iterable[tuple[str, Citation]]:
        # Concrete return for the Protocol: yields (text, citation). The
        # scope-aware variant is iter_chunks_with_scope().
        for text, citation, _scope in self.iter_chunks_with_scope():
            yield text, citation

    def iter_chunks_with_scope(
        self,
        *,
        chunker: AiActChunkerConfig | None = None,
    ) -> Iterator[tuple[str, Citation, str | None]]:
        cfg = chunker or AiActChunkerConfig()
        version = self.corpus_version()
        fetched = self._ensure_fetched()
        url = fetched.source_url
        for section in self._ensure_parsed():
            base_citation = Citation(
                celex_id=CELEX_ID,
                article=section.article,
                paragraph=section.paragraph,
                annex_ref=section.annex_ref,
                recital_ref=section.recital_ref,
                lang=self.language.lower(),
                url=url,
                corpus_version=version,
            )
            scope = scope_for_citation(base_citation)
            raw = RawSection(text=section.text, citation=base_citation)
            for piece in split_into_chunks(
                raw, max_chars=cfg.max_chars, overlap_chars=cfg.overlap_chars
            ):
                yield piece.text, piece.citation, scope

    def recital_to_article_map(self) -> dict[str, list[str]]:
        """
        Map recital_ref -> list of article numbers it interprets.

        Phase 2 stub: returns an empty map. The full mapping (built from a
        cross-reference pass over the text) lands in Phase 5 when recital
        co-retrieval is needed for the LLM context. Defined here so callers
        can rely on the method existing.
        """
        return {}

    def kinds_count(self) -> dict[SectionKind, int]:
        """Debug helper: parsed section counts by kind."""
        counts: dict[SectionKind, int] = {}
        for s in self._ensure_parsed():
            counts[s.kind] = counts.get(s.kind, 0) + 1
        return counts


def _default_cache_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "corpus" / "raw"
