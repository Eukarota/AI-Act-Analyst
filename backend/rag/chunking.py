"""
Generic chunking utilities.

Per CLAUDE.md section 12.2: chunks must carry citation metadata, and
sub-paragraph granularity is the right unit for legal text. Per-regulation
modules call into these helpers; this file knows nothing about specific
regulations.

The split_into_chunks() helper keeps text under a max_chars limit while
respecting paragraph boundaries. It is not "semantic" chunking; legal text
already has natural seams (paragraphs, sub-paragraphs, points) and we lean
on them.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise

from backend.agent.state import Citation, RetrievedPassage


@dataclass(frozen=True)
class RawSection:
    """A section emitted by a regulation parser before chunking."""

    text: str
    citation: Citation


def split_into_chunks(
    section: RawSection,
    *,
    max_chars: int,
    overlap_chars: int = 0,
) -> list[RawSection]:
    """
    Split a section into chunks under max_chars, preserving the citation.

    Tries paragraph boundaries first, then sentence-like boundaries, then a
    hard slice as a last resort. Overlap is taken from the trailing characters
    of the previous chunk; useful for boundary-sensitive retrieval.
    """
    text = section.text.strip()
    if len(text) <= max_chars:
        return [section] if text else []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for paragraph in paragraphs:
        if len(buf) + len(paragraph) + 2 <= max_chars:
            buf = f"{buf}\n\n{paragraph}" if buf else paragraph
        else:
            if buf:
                chunks.append(buf)
            if len(paragraph) > max_chars:
                chunks.extend(_hard_split(paragraph, max_chars=max_chars))
                buf = ""
            else:
                buf = paragraph
    if buf:
        chunks.append(buf)

    if overlap_chars > 0 and len(chunks) > 1:
        with_overlap: list[str] = [chunks[0]]
        for previous, current in pairwise(chunks):
            tail = previous[-overlap_chars:]
            with_overlap.append(f"{tail}\n{current}")
        chunks = with_overlap

    return [RawSection(text=chunk, citation=section.citation) for chunk in chunks if chunk.strip()]


def _hard_split(text: str, *, max_chars: int) -> list[str]:
    """Last-resort split for an oversized paragraph. Sentence-ish first."""
    sentences = _sentence_split(text)
    out: list[str] = []
    buf = ""
    for sentence in sentences:
        if len(buf) + len(sentence) + 1 <= max_chars:
            buf = f"{buf} {sentence}" if buf else sentence
        else:
            if buf:
                out.append(buf)
            if len(sentence) > max_chars:
                out.extend(sentence[i : i + max_chars] for i in range(0, len(sentence), max_chars))
                buf = ""
            else:
                buf = sentence
    if buf:
        out.append(buf)
    return out


def _sentence_split(text: str) -> list[str]:
    """Cheap sentence segmentation that does not need an NLP dep."""
    out: list[str] = []
    buf = ""
    for char in text:
        buf += char
        if char in ".;!?" and len(buf) > 40:
            out.append(buf.strip())
            buf = ""
    if buf.strip():
        out.append(buf.strip())
    return out


def to_retrieved(
    sections: Iterable[RawSection],
    *,
    score: float = 0.0,
    retrieval_scope: str | None = None,
) -> list[RetrievedPassage]:
    """Helper: convert RawSections to RetrievedPassages (e.g. for fixtures)."""
    return [
        RetrievedPassage(
            text=s.text,
            citation=s.citation,
            score=score,
            retrieval_scope=retrieval_scope,
        )
        for s in sections
    ]
