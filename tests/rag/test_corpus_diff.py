"""Unit tests for the per-chunk corpus diff."""

from __future__ import annotations

from backend.agent.state import Citation
from backend.rag.corpus_diff import (
    build_snapshot,
    diff_snapshots,
    render_markdown,
)


def _cite(article: str, paragraph: str | None = None) -> Citation:
    return Citation(
        celex_id="32024R1689",
        article=article,
        paragraph=paragraph,
        lang="en",
        corpus_version="v1",
    )


def test_identical_corpus_produces_empty_diff() -> None:
    triples = [
        ("Article 5 text.", _cite("5"), "art_5_prohibited"),
        ("Article 9 text.", _cite("9"), "high_risk_obligations"),
    ]
    snapshot = build_snapshot(triples)
    diff = diff_snapshots(
        previous_version="v1",
        new_version="v1",
        previous=snapshot,
        new=snapshot,
    )
    assert diff.is_empty
    assert diff.counts() == {"added": 0, "removed": 0, "changed": 0, "unchanged": 2}


def test_added_chunk_appears_with_article_bucket() -> None:
    previous = build_snapshot([("old", _cite("5"), None)])
    new = build_snapshot(
        [
            ("old", _cite("5"), None),
            ("new", _cite("9"), None),
        ]
    )
    diff = diff_snapshots(previous_version="v1", new_version="v2", previous=previous, new=new)
    assert diff.counts()["added"] == 1
    assert "Art. 9" in diff.per_article_changes
    assert diff.per_article_changes["Art. 9"]["added"] == 1


def test_text_change_classifies_as_changed_not_added() -> None:
    previous = build_snapshot([("v1 text", _cite("5"), None)])
    new = build_snapshot([("v2 text", _cite("5"), None)])
    diff = diff_snapshots(previous_version="v1", new_version="v2", previous=previous, new=new)
    assert diff.counts() == {"added": 0, "removed": 0, "changed": 1, "unchanged": 0}
    assert diff.per_article_changes["Art. 5"]["changed"] == 1


def test_removed_chunk_recorded() -> None:
    previous = build_snapshot([("a", _cite("5"), None), ("b", _cite("9"), None)])
    new = build_snapshot([("a", _cite("5"), None)])
    diff = diff_snapshots(previous_version="v1", new_version="v2", previous=previous, new=new)
    assert diff.counts()["removed"] == 1
    assert diff.per_article_changes["Art. 9"]["removed"] == 1


def test_markdown_summarises_per_article_changes() -> None:
    previous = build_snapshot([("a", _cite("5"), None)])
    new = build_snapshot([("a-new", _cite("5"), None), ("b", _cite("9"), None)])
    diff = diff_snapshots(previous_version="v1", new_version="v2", previous=previous, new=new)
    rendered = render_markdown(diff)
    assert "Per-article changes" in rendered
    assert "Art. 5" in rendered
    assert "Art. 9" in rendered
