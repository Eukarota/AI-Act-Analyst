"""
Per-chunk corpus diff.

CLAUDE.md section 12.4: a corpus re-index must "produce a diff report
(which articles changed). A new corpus_version auto-triggers an eval re-run."

The diff is computed over the canonical chunk key (celex_id + article +
paragraph + annex_ref + recital_ref) plus the SHA-256 of the text. That
gives three categories per chunk:

  added       new key vs. the previous snapshot
  removed     key present in the previous snapshot but missing now
  changed     same key, different text hash

Unchanged chunks are counted but not enumerated. The output is grouped by
article so a compliance reviewer can scan the diff against a published
amendment table (Digital Omnibus etc.) without parsing JSON.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from backend.agent.state import Citation


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _chunk_key(citation: Citation) -> str:
    return "|".join(
        (
            citation.celex_id,
            citation.article or "",
            citation.paragraph or "",
            citation.annex_ref or "",
            citation.recital_ref or "",
        )
    )


def _article_bucket(citation: Citation) -> str:
    if citation.article:
        return f"Art. {citation.article}"
    if citation.annex_ref:
        return f"Annex {citation.annex_ref}"
    if citation.recital_ref:
        return f"Recital {citation.recital_ref}"
    return "other"


@dataclass(frozen=True)
class ChunkRecord:
    """One row of the per-chunk diff snapshot."""

    key: str
    text_hash: str
    article: str | None
    paragraph: str | None
    annex_ref: str | None
    recital_ref: str | None
    article_bucket: str

    @classmethod
    def from_triple(cls, text: str, citation: Citation) -> ChunkRecord:
        return cls(
            key=_chunk_key(citation),
            text_hash=_text_hash(text),
            article=citation.article,
            paragraph=citation.paragraph,
            annex_ref=citation.annex_ref,
            recital_ref=citation.recital_ref,
            article_bucket=_article_bucket(citation),
        )


@dataclass(frozen=True)
class CorpusDiff:
    """Result of comparing two snapshots."""

    previous_version: str | None
    new_version: str
    added_keys: tuple[str, ...] = ()
    removed_keys: tuple[str, ...] = ()
    changed_keys: tuple[str, ...] = ()
    unchanged_count: int = 0
    per_article_changes: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (self.added_keys or self.removed_keys or self.changed_keys)

    @property
    def changed_article_buckets(self) -> tuple[str, ...]:
        return tuple(sorted(self.per_article_changes.keys()))

    def counts(self) -> dict[str, int]:
        return {
            "added": len(self.added_keys),
            "removed": len(self.removed_keys),
            "changed": len(self.changed_keys),
            "unchanged": self.unchanged_count,
        }


def build_snapshot(triples: Iterable[tuple[str, Citation, str | None]]) -> dict[str, ChunkRecord]:
    """Build a key -> ChunkRecord index for one indexing pass."""
    snapshot: dict[str, ChunkRecord] = {}
    for text, citation, _scope in triples:
        record = ChunkRecord.from_triple(text, citation)
        snapshot[record.key] = record
    return snapshot


def diff_snapshots(
    *,
    previous_version: str | None,
    new_version: str,
    previous: dict[str, ChunkRecord],
    new: dict[str, ChunkRecord],
) -> CorpusDiff:
    """Compute the per-chunk diff between two snapshots."""
    added: list[str] = []
    removed: list[str] = []
    changed: list[str] = []
    per_article: dict[str, dict[str, int]] = {}
    unchanged = 0

    for key, record in new.items():
        bucket = record.article_bucket
        if key not in previous:
            added.append(key)
            per_article.setdefault(bucket, {"added": 0, "removed": 0, "changed": 0})["added"] += 1
        elif previous[key].text_hash != record.text_hash:
            changed.append(key)
            per_article.setdefault(bucket, {"added": 0, "removed": 0, "changed": 0})["changed"] += 1
        else:
            unchanged += 1

    for key, record in previous.items():
        if key not in new:
            removed.append(key)
            bucket = record.article_bucket
            per_article.setdefault(bucket, {"added": 0, "removed": 0, "changed": 0})["removed"] += 1

    return CorpusDiff(
        previous_version=previous_version,
        new_version=new_version,
        added_keys=tuple(sorted(added)),
        removed_keys=tuple(sorted(removed)),
        changed_keys=tuple(sorted(changed)),
        unchanged_count=unchanged,
        per_article_changes={k: dict(v) for k, v in sorted(per_article.items())},
    )


def write_snapshot(path: Path, snapshot: dict[str, ChunkRecord]) -> None:
    """Persist a snapshot as JSON so the next index pass can diff against it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {key: asdict(record) for key, record in snapshot.items()}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_snapshot(path: Path) -> dict[str, ChunkRecord]:
    """Load a persisted snapshot. Returns an empty dict when missing."""
    if not path.exists():
        return {}
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    out: dict[str, ChunkRecord] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        stored_key = value.get("key")
        out[key] = ChunkRecord(
            key=stored_key if isinstance(stored_key, str) else key,
            text_hash=str(value.get("text_hash", "")),
            article=value.get("article"),
            paragraph=value.get("paragraph"),
            annex_ref=value.get("annex_ref"),
            recital_ref=value.get("recital_ref"),
            article_bucket=value.get("article_bucket", "other"),
        )
    return out


def render_markdown(diff: CorpusDiff) -> str:
    """Compliance-reader-friendly summary."""
    lines = ["# Corpus diff", ""]
    lines.append(f"- Previous version: `{diff.previous_version or 'none'}`")
    lines.append(f"- New version: `{diff.new_version}`")
    counts = diff.counts()
    lines.append(
        f"- Counts: added={counts['added']}, removed={counts['removed']}, "
        f"changed={counts['changed']}, unchanged={counts['unchanged']}"
    )
    lines.append("")
    if diff.is_empty:
        lines.append("No chunk-level changes. Re-index was a no-op.")
        return "\n".join(lines) + "\n"

    lines.append("## Per-article changes")
    lines.append("")
    lines.append("| section | added | removed | changed |")
    lines.append("| --- | ---: | ---: | ---: |")
    for bucket, row in diff.per_article_changes.items():
        lines.append(
            f"| {bucket} | {row.get('added', 0)} | "
            f"{row.get('removed', 0)} | {row.get('changed', 0)} |"
        )
    return "\n".join(lines) + "\n"
