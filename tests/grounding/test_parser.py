"""AI Act parser tests against the committed fixture excerpt."""

from __future__ import annotations

from pathlib import Path

from regulations.ai_act.corpus.parser import SectionKind, parse_consolidated_text

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "regulations"
    / "ai_act"
    / "corpus"
    / "fixture_excerpt.txt"
)


def _load_fixture() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def test_parser_extracts_recitals() -> None:
    sections = parse_consolidated_text(_load_fixture())
    recitals = [s for s in sections if s.kind == SectionKind.RECITAL]
    nums = {s.recital_ref for s in recitals}
    assert {"1", "2", "15"}.issubset(nums)


def test_parser_extracts_articles_with_paragraphs() -> None:
    sections = parse_consolidated_text(_load_fixture())
    article_paragraphs = [
        s for s in sections if s.kind == SectionKind.ARTICLE_PARAGRAPH and s.article == "5"
    ]
    assert any(s.paragraph == "1" for s in article_paragraphs)


def test_parser_extracts_annex_iii() -> None:
    sections = parse_consolidated_text(_load_fixture())
    annex = [s for s in sections if s.annex_ref == "III"]
    assert annex, "ANNEX III should be parsed"


def test_parser_separates_article_50_paragraphs() -> None:
    sections = parse_consolidated_text(_load_fixture())
    a50 = [s for s in sections if s.article == "50" and s.kind == SectionKind.ARTICLE_PARAGRAPH]
    paragraphs = {s.paragraph for s in a50}
    assert {"1", "2"}.issubset(paragraphs)
