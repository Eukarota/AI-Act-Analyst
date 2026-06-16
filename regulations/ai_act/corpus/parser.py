"""
Parser for the consolidated AI Act text.

Input: plain text (after HTML strip). Output: ParsedSections carrying
identification for each chunk -- recital number, article number plus optional
paragraph, or annex roman numeral plus optional point.

Designed for the EUR-Lex consolidated rendering of Regulation (EU) 2024/1689
(CELEX:32024R1689). Tolerant of cosmetic variation (line wrapping, run-on
paragraphs); brittle parts are isolated in regular expressions that are unit
tested.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import StrEnum

# Recitals are introduced by "Whereas:" / "considérant ce qui suit:" and each
# starts with a number in parentheses on its own logical line.
_RECITAL_HEAD_RE = re.compile(r"(?m)^\s*\((\d+)\)\s*")

# Article paragraph numbering: "1.", "2.", ..., possibly with sub-points "(a)".
# The OJ converter sometimes emits a single non-breaking space after the dot,
# normalized to ASCII before we hit this regex.
_ARTICLE_PARA_RE = re.compile(r"(?m)^\s*(\d{1,2})\.\s+")


@dataclass(frozen=True)
class _LanguageGrammar:
    article_head: re.Pattern[str]
    annex_head: re.Pattern[str]
    # FR uses "Article premier" for Article 1; we normalize it to "1" here so
    # the rest of the pipeline keeps the same article identifiers as EN.
    article_one_alias: str | None
    article_one_canonical: str


_EN = _LanguageGrammar(
    article_head=re.compile(r"(?m)^\s*Article\s+(\d+[a-z]?)\s*$"),
    annex_head=re.compile(r"(?m)^\s*ANNEX\s+([IVXLCM]+)\s*$"),
    article_one_alias=None,
    article_one_canonical="1",
)

_FR = _LanguageGrammar(
    # FR matches the same "Article N" form for N >= 2, plus "Article premier"
    # for N = 1. We capture the literal "premier" and rewrite to "1" below.
    article_head=re.compile(r"(?m)^\s*Article\s+(\d+[a-z]?|premier)\s*$"),
    annex_head=re.compile(r"(?m)^\s*ANNEXE\s+([IVXLCM]+)\s*$"),
    article_one_alias="premier",
    article_one_canonical="1",
)

_GRAMMARS: dict[str, _LanguageGrammar] = {"EN": _EN, "FR": _FR}


class SectionKind(StrEnum):
    RECITAL = "recital"
    ARTICLE = "article"
    ARTICLE_PARAGRAPH = "article_paragraph"
    ANNEX = "annex"
    ANNEX_POINT = "annex_point"


@dataclass(frozen=True)
class ParsedSection:
    kind: SectionKind
    text: str
    article: str | None = None
    paragraph: str | None = None
    annex_ref: str | None = None
    recital_ref: str | None = None
    title: str | None = None


def parse_consolidated_text(text: str, *, language: str = "EN") -> list[ParsedSection]:
    """
    Parse the full consolidated text into sections.

    Order of operations matters: we slice the document into top-level regions
    (preamble + recitals, enacting terms / articles, annexes) and only then
    parse each region with its own grammar. Article paragraphs ("1.", "2.")
    inside annexes are not articles; segregating regions first prevents that
    class of false positive.
    """
    grammar = _GRAMMARS.get(language.upper())
    if grammar is None:
        raise ValueError(f"unsupported parser language: {language!r}")

    enacting_start = _find_enacting_start(text, grammar)
    if enacting_start is None:
        return list(_parse_recitals(text))

    preamble = text[:enacting_start]
    after = text[enacting_start:]

    annex_match = grammar.annex_head.search(after)
    if annex_match:
        articles_region = after[: annex_match.start()]
        annexes_region = after[annex_match.start() :]
    else:
        articles_region = after
        annexes_region = ""

    sections: list[ParsedSection] = []
    sections.extend(_parse_recitals(preamble))
    sections.extend(_parse_articles(articles_region, grammar))
    sections.extend(_parse_annexes(annexes_region, grammar))
    return sections


def _canonical_article(raw: str, grammar: _LanguageGrammar) -> str:
    if grammar.article_one_alias is not None and raw == grammar.article_one_alias:
        return grammar.article_one_canonical
    return raw


def _find_enacting_start(text: str, grammar: _LanguageGrammar) -> int | None:
    """Return the index of the first 'Article 1' heading, or None if absent."""
    for match in grammar.article_head.finditer(text):
        if _canonical_article(match.group(1), grammar) == "1":
            return match.start()
    return None


def _parse_recitals(preamble: str) -> Iterator[ParsedSection]:
    matches = list(_RECITAL_HEAD_RE.finditer(preamble))
    for i, match in enumerate(matches):
        number = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(preamble)
        body = preamble[start:end].strip()
        if not body:
            continue
        yield ParsedSection(
            kind=SectionKind.RECITAL,
            text=body,
            recital_ref=number,
        )


def _parse_articles(region: str, grammar: _LanguageGrammar) -> Iterator[ParsedSection]:
    matches = list(grammar.article_head.finditer(region))
    for i, match in enumerate(matches):
        article = _canonical_article(match.group(1), grammar)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(region)
        block = region[start:end].strip()
        if not block:
            continue

        title, body = _split_title_and_body(block)
        para_matches = list(_ARTICLE_PARA_RE.finditer(body))
        if not para_matches:
            yield ParsedSection(
                kind=SectionKind.ARTICLE,
                text=body,
                article=article,
                title=title,
            )
            continue

        for j, pm in enumerate(para_matches):
            number = pm.group(1)
            p_start = pm.end()
            p_end = para_matches[j + 1].start() if j + 1 < len(para_matches) else len(body)
            para_text = body[p_start:p_end].strip()
            if not para_text:
                continue
            yield ParsedSection(
                kind=SectionKind.ARTICLE_PARAGRAPH,
                text=para_text,
                article=article,
                paragraph=number,
                title=title,
            )

        prefix = body[: para_matches[0].start()].strip()
        if prefix:
            yield ParsedSection(
                kind=SectionKind.ARTICLE,
                text=prefix,
                article=article,
                title=title,
            )


def _parse_annexes(region: str, grammar: _LanguageGrammar) -> Iterator[ParsedSection]:
    matches = list(grammar.annex_head.finditer(region))
    for i, match in enumerate(matches):
        roman = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(region)
        body = region[start:end].strip()
        if not body:
            continue
        title, rest = _split_title_and_body(body)
        # Annex points like "1.", "2." are common in Annex III. We chunk them
        # if present, otherwise emit the whole annex as one section.
        point_matches = list(_ARTICLE_PARA_RE.finditer(rest))
        if not point_matches:
            yield ParsedSection(
                kind=SectionKind.ANNEX,
                text=rest if rest else body,
                annex_ref=roman,
                title=title,
            )
            continue

        for j, pm in enumerate(point_matches):
            number = pm.group(1)
            p_start = pm.end()
            p_end = point_matches[j + 1].start() if j + 1 < len(point_matches) else len(rest)
            point_text = rest[p_start:p_end].strip()
            if not point_text:
                continue
            yield ParsedSection(
                kind=SectionKind.ANNEX_POINT,
                text=point_text,
                annex_ref=roman,
                paragraph=number,
                title=title,
            )


def _split_title_and_body(block: str) -> tuple[str | None, str]:
    """
    A leading short non-numbered line is treated as the section title.

    Heuristic: first line, under 120 chars, not starting with a digit. The
    rest is the body. Robust enough for the AI Act's structure.
    """
    if not block:
        return None, block
    lines = block.splitlines()
    if not lines:
        return None, block
    head = lines[0].strip()
    if 0 < len(head) <= 120 and not head[:1].isdigit():
        return head, "\n".join(lines[1:]).strip()
    return None, block


def find_recitals(sections: Iterable[ParsedSection]) -> dict[str, str]:
    """Convenience: build a recital_ref -> text map."""
    return {
        s.recital_ref: s.text for s in sections if s.kind == SectionKind.RECITAL and s.recital_ref
    }
