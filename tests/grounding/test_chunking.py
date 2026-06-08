"""Chunker tests."""

from __future__ import annotations

from backend.agent.state import Citation
from backend.rag.chunking import RawSection, split_into_chunks


def _cite() -> Citation:
    return Citation(celex_id="TEST", article="1", corpus_version="test-v1")


def test_short_section_returns_single_chunk() -> None:
    section = RawSection(text="hello world", citation=_cite())
    chunks = split_into_chunks(section, max_chars=100)
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
    assert chunks[0].citation == _cite()


def test_paragraph_boundary_is_preferred() -> None:
    text = "Paragraph one.\n\n" + "x" * 50 + "\n\n" + "Paragraph three."
    section = RawSection(text=text, citation=_cite())
    chunks = split_into_chunks(section, max_chars=60)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.citation == _cite()


def test_oversize_paragraph_is_hard_split_sentence_aware() -> None:
    long_sentence = ("This is one long sentence. " * 30).strip()
    section = RawSection(text=long_sentence, citation=_cite())
    chunks = split_into_chunks(section, max_chars=120)
    for chunk in chunks:
        assert len(chunk.text) <= 130
    assert sum(len(c.text) for c in chunks) >= len(long_sentence) - 30


def test_empty_section_yields_no_chunks() -> None:
    section = RawSection(text="   \n\n   ", citation=_cite())
    assert split_into_chunks(section, max_chars=100) == []
