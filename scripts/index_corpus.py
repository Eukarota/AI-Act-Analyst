"""
index_corpus.py: load a regulation corpus and index it into a vector store.

Usage:
    python scripts/index_corpus.py --regulation ai_act
    python scripts/index_corpus.py --regulation ai_act --source local
    python scripts/index_corpus.py --regulation ai_act --target memory --dry-run

Defaults:
    --source fetch        (fetch consolidated text from EUR-Lex)
    --target pgvector     (requires docker compose up postgres)
    --language EN
    --dry-run False

Idempotency (CLAUDE.md section 12.4):
    corpus_version is content-derived. Re-running with unchanged source
    produces an empty diff and the indexer is a no-op. A diff report is
    written to regulations/<name>/corpus/diff/<version>.txt when chunks have
    changed (added/removed/edited).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.in_memory_store import InMemoryVectorStore
from backend.adapters.pgvector_store import PgVectorStore
from backend.agent.state import Citation
from backend.ports.embedder import Embedder
from backend.rag.corpus_diff import (
    build_snapshot,
    diff_snapshots,
    read_snapshot,
    render_markdown,
    write_snapshot,
)
from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader

REPO_ROOT = Path(__file__).resolve().parents[1]

# The consolidated AI Act has ~180 recitals, ~113 articles (broken into ~500
# numbered paragraphs), and 13 annexes (~100 sub-points). Anything below this
# floor is a parser or fetch failure, not a real corpus, and must not be
# written to the vector store under a fresh corpus_version.
_MIN_CHUNKS = 500


@dataclass
class IndexReport:
    regulation: str
    corpus_version: str
    chunks: int
    target: str
    diff: dict[str, int]
    output_path: Path

    def as_dict(self) -> dict[str, object]:
        return {
            "regulation": self.regulation,
            "corpus_version": self.corpus_version,
            "chunks": self.chunks,
            "target": self.target,
            "diff": self.diff,
        }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index a regulation corpus.")
    parser.add_argument("--regulation", required=True, choices=["ai_act"])
    parser.add_argument("--source", default="fetch", choices=["fetch", "local"])
    parser.add_argument("--target", default="pgvector", choices=["pgvector", "memory"])
    parser.add_argument("--language", default="EN")
    parser.add_argument(
        "--dsn",
        default="postgresql://boussole:boussole@localhost:5432/boussole",
        help="Postgres DSN (used when --target pgvector).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and chunk but do not upsert.")
    parser.add_argument(
        "--use-fake-embedder",
        action="store_true",
        help="Use the deterministic FakeEmbedder (Phase 2 default until Phase 3 wires vLLM).",
    )
    return parser.parse_args()


async def main() -> int:
    args = _parse_args()

    if args.regulation != "ai_act":
        print(f"unsupported regulation: {args.regulation}", file=sys.stderr)
        return 2

    loader = AiActCorpusLoader(
        language=args.language,
        prefer_local=(args.source == "local"),
    )
    chunker_cfg = AiActChunkerConfig()

    triples = list(loader.iter_chunks_with_scope(chunker=chunker_cfg))
    version = loader.corpus_version()
    print(f"[index_corpus] regulation=ai_act version={version} chunks={len(triples)}")

    if len(triples) < _MIN_CHUNKS:
        print(
            f"[index_corpus] FATAL: only {len(triples)} chunks produced (expected "
            f">= {_MIN_CHUNKS}). The fetch or parse step produced a partial corpus; "
            f"refusing to index. Check regulations/ai_act/corpus/raw/ and re-run.",
            file=sys.stderr,
        )
        return 3

    embedder: Embedder
    if args.use_fake_embedder or args.target == "memory":
        embedder = FakeEmbedder()
    else:
        # Real path: multilingual-e5-large (1.1 GB) is downloaded on first run
        # via sentence-transformers and cached under ~/.cache/huggingface.
        # Embedding ~500-1000 AI Act chunks takes 1-2 minutes on CPU.
        from backend.adapters.e5_embedder import MultilingualE5LargeEmbedder

        embedder = MultilingualE5LargeEmbedder()

    diff = await _emit_diff(version, triples)

    if args.dry_run:
        report = IndexReport(
            regulation="ai_act",
            corpus_version=version,
            chunks=len(triples),
            target="dry-run",
            diff=diff,
            output_path=Path("/dev/null"),
        )
        _write_version_file("ai_act", version)
        print(json.dumps(report.as_dict(), indent=2))
        return 0

    vectors = await embedder.embed_documents([t[0] for t in triples])
    upsert_rows: list[tuple[str, list[float], Citation, str | None]] = [
        (text, vector, citation, scope)
        for (text, citation, scope), vector in zip(triples, vectors, strict=True)
    ]

    if args.target == "memory":
        store = InMemoryVectorStore(corpus_version=version)
        await store.upsert(upsert_rows)
        target = "memory"
    else:
        pg = PgVectorStore(dsn=args.dsn, dimension=embedder.dimension, regulation="ai_act")
        await pg.connect()
        try:
            await pg.ensure_schema()
            await pg.replace_corpus(version, upsert_rows)
        finally:
            await pg.close()
        target = "pgvector"

    _write_version_file("ai_act", version)

    report = IndexReport(
        regulation="ai_act",
        corpus_version=version,
        chunks=len(triples),
        target=target,
        diff=diff,
        output_path=REPO_ROOT / "regulations" / "ai_act" / "corpus" / "VERSION",
    )
    print(json.dumps(report.as_dict(), indent=2))
    return 0


async def _emit_diff(
    version: str, triples: list[tuple[str, Citation, str | None]]
) -> dict[str, int]:
    """
    Compute the per-chunk diff vs the previous snapshot and persist both.

    Reads the previous snapshot from regulations/ai_act/corpus/diff/<prev>.snapshot.json
    (when present), writes the new snapshot, and emits diff JSON + Markdown
    grouped by Article / Annex / Recital for compliance review.
    """
    version_path = REPO_ROOT / "regulations" / "ai_act" / "corpus" / "VERSION"
    diff_dir = REPO_ROOT / "regulations" / "ai_act" / "corpus" / "diff"
    diff_dir.mkdir(parents=True, exist_ok=True)

    previous = version_path.read_text(encoding="utf-8").strip() if version_path.exists() else None
    previous_snapshot_path = (
        diff_dir / f"{previous}.snapshot.json" if previous else diff_dir / "__none__.snapshot.json"
    )
    new_snapshot_path = diff_dir / f"{version}.snapshot.json"

    new_snapshot = build_snapshot(triples)
    previous_snapshot = read_snapshot(previous_snapshot_path)

    diff = diff_snapshots(
        previous_version=previous,
        new_version=version,
        previous=previous_snapshot,
        new=new_snapshot,
    )

    write_snapshot(new_snapshot_path, new_snapshot)
    (diff_dir / f"{version}.json").write_text(
        json.dumps(
            {
                "previous_version": diff.previous_version,
                "new_version": diff.new_version,
                "counts": diff.counts(),
                "added_keys": list(diff.added_keys),
                "removed_keys": list(diff.removed_keys),
                "changed_keys": list(diff.changed_keys),
                "per_article_changes": diff.per_article_changes,
                "changed_article_buckets": list(diff.changed_article_buckets),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (diff_dir / f"{version}.md").write_text(render_markdown(diff), encoding="utf-8")
    return diff.counts()


def _write_version_file(regulation: str, version: str) -> None:
    path = REPO_ROOT / "regulations" / regulation / "corpus" / "VERSION"
    path.write_text(version + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
