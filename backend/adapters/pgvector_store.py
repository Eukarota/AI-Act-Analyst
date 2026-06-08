"""
PgVectorStore: Postgres + pgvector + tsvector backing the hybrid retrieval.

Schema (created idempotently by ensure_schema):

  corpus_chunks(
    id BIGSERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    embedding vector(<dim>) NOT NULL,
    celex_id TEXT NOT NULL,
    article TEXT,
    paragraph TEXT,
    annex_ref TEXT,
    recital_ref TEXT,
    lang TEXT NOT NULL DEFAULT 'en',
    url TEXT,
    corpus_version TEXT NOT NULL,
    retrieval_scope TEXT,
    text_search tsvector GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED
  )
  corpus_versions(corpus_version TEXT PRIMARY KEY, regulation TEXT, indexed_at TIMESTAMPTZ, chunk_count INT)

Indexes: HNSW on embedding (cosine), GIN on text_search, btree on retrieval_scope and corpus_version.

Lives behind the 'integration' pytest marker; the unit suite uses
InMemoryVectorStore so tests run without Docker.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import asyncpg

from backend.agent.state import Citation, RetrievedPassage


class PgVectorStore:
    def __init__(
        self,
        dsn: str,
        *,
        dimension: int,
        regulation: str,
    ) -> None:
        self.dsn = dsn
        self.dimension = dimension
        self.regulation = regulation
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=8)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _pool_required(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("PgVectorStore.connect() must be called before use.")
        return self._pool

    async def ensure_schema(self) -> None:
        pool = self._pool_required()
        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS corpus_chunks (
                  id BIGSERIAL PRIMARY KEY,
                  text TEXT NOT NULL,
                  embedding vector({self.dimension}) NOT NULL,
                  celex_id TEXT NOT NULL,
                  article TEXT,
                  paragraph TEXT,
                  annex_ref TEXT,
                  recital_ref TEXT,
                  lang TEXT NOT NULL DEFAULT 'en',
                  url TEXT,
                  corpus_version TEXT NOT NULL,
                  regulation TEXT NOT NULL,
                  retrieval_scope TEXT,
                  text_search tsvector
                    GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED
                );
                """
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS corpus_chunks_embedding_idx "
                "ON corpus_chunks USING hnsw (embedding vector_cosine_ops);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS corpus_chunks_textsearch_idx "
                "ON corpus_chunks USING gin (text_search);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS corpus_chunks_scope_idx "
                "ON corpus_chunks (retrieval_scope);"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS corpus_chunks_corpus_idx "
                "ON corpus_chunks (regulation, corpus_version);"
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS corpus_versions (
                  corpus_version TEXT NOT NULL,
                  regulation TEXT NOT NULL,
                  indexed_at TIMESTAMPTZ DEFAULT now(),
                  chunk_count INT NOT NULL DEFAULT 0,
                  PRIMARY KEY (regulation, corpus_version)
                );
                """
            )

    @staticmethod
    def _vector_literal(vector: Sequence[float]) -> str:
        return "[" + ",".join(f"{x:.8f}" for x in vector) + "]"

    async def upsert(
        self,
        passages: Sequence[tuple[str, list[float], Citation, str | None]],
    ) -> None:
        if not passages:
            return
        pool = self._pool_required()
        rows = [
            (
                text,
                self._vector_literal(vector),
                citation.celex_id,
                citation.article,
                citation.paragraph,
                citation.annex_ref,
                citation.recital_ref,
                citation.lang,
                citation.url,
                citation.corpus_version,
                self.regulation,
                scope,
            )
            for text, vector, citation, scope in passages
        ]
        async with pool.acquire() as conn, conn.transaction():
            # Replace any rows for this (regulation, corpus_version) at the start of an
            # index run; callers should clear-then-upsert in one transaction for atomicity.
            await conn.executemany(
                """
                    INSERT INTO corpus_chunks(
                        text, embedding, celex_id, article, paragraph, annex_ref,
                        recital_ref, lang, url, corpus_version, regulation, retrieval_scope
                    )
                    VALUES ($1, $2::vector, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12);
                    """,
                rows,
            )

    async def replace_corpus(
        self,
        corpus_version: str,
        passages: Sequence[tuple[str, list[float], Citation, str | None]],
    ) -> None:
        """Atomic: drop existing rows for this (regulation, corpus_version) and re-insert."""
        pool = self._pool_required()
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "DELETE FROM corpus_chunks WHERE regulation = $1 AND corpus_version = $2;",
                self.regulation,
                corpus_version,
            )
            if passages:
                await self.upsert(passages)
            await conn.execute(
                """
                    INSERT INTO corpus_versions(corpus_version, regulation, chunk_count)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (regulation, corpus_version)
                    DO UPDATE SET indexed_at = now(), chunk_count = EXCLUDED.chunk_count;
                    """,
                corpus_version,
                self.regulation,
                len(passages),
            )

    async def search_dense(
        self,
        query_vector: list[float],
        *,
        scope: str | None = None,
        k: int = 20,
    ) -> list[RetrievedPassage]:
        pool = self._pool_required()
        query = """
            SELECT text, celex_id, article, paragraph, annex_ref, recital_ref,
                   lang, url, corpus_version, retrieval_scope,
                   1 - (embedding <=> $1::vector) AS score
            FROM corpus_chunks
            WHERE regulation = $2
              AND ($3::text IS NULL OR retrieval_scope = $3)
            ORDER BY embedding <=> $1::vector
            LIMIT $4;
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                query,
                self._vector_literal(query_vector),
                self.regulation,
                scope,
                k,
            )
        return [self._row_to_passage(row) for row in rows]

    async def search_sparse(
        self,
        query_text: str,
        *,
        scope: str | None = None,
        k: int = 20,
    ) -> list[RetrievedPassage]:
        pool = self._pool_required()
        query = """
            SELECT text, celex_id, article, paragraph, annex_ref, recital_ref,
                   lang, url, corpus_version, retrieval_scope,
                   ts_rank_cd(text_search, plainto_tsquery('simple', $1)) AS score
            FROM corpus_chunks
            WHERE regulation = $2
              AND ($3::text IS NULL OR retrieval_scope = $3)
              AND text_search @@ plainto_tsquery('simple', $1)
            ORDER BY score DESC
            LIMIT $4;
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, query_text, self.regulation, scope, k)
        return [self._row_to_passage(row) for row in rows]

    @staticmethod
    def _row_to_passage(row: Any) -> RetrievedPassage:
        citation = Citation(
            celex_id=row["celex_id"],
            article=row["article"],
            paragraph=row["paragraph"],
            annex_ref=row["annex_ref"],
            recital_ref=row["recital_ref"],
            lang=row["lang"],
            url=row["url"],
            corpus_version=row["corpus_version"],
        )
        return RetrievedPassage(
            text=row["text"],
            citation=citation,
            score=float(row["score"]) if row["score"] is not None else 0.0,
            retrieval_scope=row["retrieval_scope"],
        )

    async def corpus_version(self) -> str:
        pool = self._pool_required()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT corpus_version FROM corpus_versions
                WHERE regulation = $1
                ORDER BY indexed_at DESC
                LIMIT 1;
                """,
                self.regulation,
            )
        if row is None:
            raise RuntimeError(f"No corpus has been indexed for regulation {self.regulation!r}.")
        return str(row["corpus_version"])
