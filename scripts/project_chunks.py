"""
project_chunks.py: project the indexed corpus into a 3D point cloud for the
RAG cube UI.

Reads every chunk currently in `corpus_chunks` for the latest corpus_version,
runs PCA on the 1024-d embeddings down to 3 components, scales each axis into
[-1, 1] for stable rendering inside a unit cube, and writes
`frontend/public/chunks_pca3.json` with the projected coordinates plus the
citation metadata the UI needs to match the report's retrieved_passages back
to the right points.

PCA is implemented directly via numpy (covariance + eigendecomposition); no
scikit-learn dependency is added for this. The projection is deterministic
modulo sign of each eigenvector, which we lock by forcing the largest
absolute value in each component to be positive.

Usage:
    .venv/bin/python scripts/project_chunks.py
    .venv/bin/python scripts/project_chunks.py --regulation ai_act --out path

The script picks the latest corpus_version (by row count, ties broken by
lexicographic max) so it always reflects what the running backend can serve.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import asyncpg
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]


def _short_citation(row: dict[str, Any]) -> str:
    if row["article"]:
        s = f"Art. {row['article']}"
        if row["paragraph"]:
            s += f"({row['paragraph']})"
        return s
    if row["annex_ref"]:
        s = f"Annexe {row['annex_ref']}"
        if row["paragraph"]:
            s += f"({row['paragraph']})"
        return s
    if row["recital_ref"]:
        return f"Cons. {row['recital_ref']}"
    return "?"


def _citation_key(row: dict[str, Any]) -> str:
    parts = (
        row["celex_id"] or "",
        row["article"] or "",
        row["paragraph"] or "",
        row["annex_ref"] or "",
        row["recital_ref"] or "",
    )
    return "|".join(parts)


def _kind(row: dict[str, Any]) -> str:
    if row["article"]:
        return "article"
    if row["annex_ref"]:
        return "annex"
    if row["recital_ref"]:
        return "recital"
    return "other"


def _pca_3d(matrix: np.ndarray) -> np.ndarray:
    """Return the 3D PCA projection of an (N, D) embedding matrix."""
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    cov = np.cov(centered, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(cov)
    # eigh returns ascending eigenvalues; take the top three columns.
    top = eigvecs[:, -3:][:, ::-1]
    projected = centered @ top
    # Stabilize sign: force the largest absolute value in each component
    # to be positive, so re-running on the same corpus produces the same
    # picture rather than mirrored ones.
    for i in range(projected.shape[1]):
        col = projected[:, i]
        idx = int(np.argmax(np.abs(col)))
        if col[idx] < 0:
            projected[:, i] = -col
    # Scale each axis into [-1, 1] independently so the cube fills cleanly
    # without one component dominating.
    span = np.max(np.abs(projected), axis=0)
    span[span == 0] = 1.0
    return projected / span


def _parse_vector(raw: object) -> list[float]:
    """asyncpg returns pgvector as a string like '[0.1,0.2,...]'."""
    if isinstance(raw, str):
        return [float(x) for x in raw.strip("[]").split(",")]
    if isinstance(raw, (list, tuple)):
        return [float(x) for x in raw]
    raise TypeError(f"unsupported embedding representation: {type(raw)!r}")


async def _fetch_rows(
    dsn: str, regulation: str
) -> tuple[str, list[dict[str, Any]]]:
    conn = await asyncpg.connect(dsn)
    try:
        version_row = await conn.fetchrow(
            """
            SELECT corpus_version
            FROM corpus_chunks
            WHERE regulation = $1
            GROUP BY corpus_version
            ORDER BY count(*) DESC, corpus_version DESC
            LIMIT 1
            """,
            regulation,
        )
        if version_row is None:
            raise RuntimeError(
                f"no chunks found for regulation={regulation!r}; "
                f"run scripts/index_corpus.py first"
            )
        version = version_row["corpus_version"]
        rows = await conn.fetch(
            """
            SELECT id, celex_id, article, paragraph, annex_ref, recital_ref,
                   retrieval_scope, embedding::text AS embedding_text
            FROM corpus_chunks
            WHERE regulation = $1 AND corpus_version = $2
            ORDER BY id
            """,
            regulation,
            version,
        )
        return version, [dict(r) for r in rows]
    finally:
        await conn.close()


def _emit_payload(
    version: str,
    rows: Sequence[dict[str, Any]],
    projected: np.ndarray,
) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    for row, xyz in zip(rows, projected, strict=True):
        x, y, z = (float(v) for v in xyz)
        points.append(
            {
                "id": int(row["id"]),
                "key": _citation_key(row),
                "label": _short_citation(row),
                "kind": _kind(row),
                "scope": row["retrieval_scope"],
                "x": round(x, 4),
                "y": round(y, 4),
                "z": round(z, 4),
            }
        )
    return {
        "corpus_version": version,
        "point_count": len(points),
        "points": points,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project corpus chunks to 3D.")
    parser.add_argument("--regulation", default="ai_act")
    parser.add_argument(
        "--dsn",
        default="postgresql://boussole:boussole@localhost:5432/boussole",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "frontend" / "public" / "chunks_pca3.json",
    )
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()
    version, rows = await _fetch_rows(args.dsn, args.regulation)
    if not rows:
        print("no rows to project", file=sys.stderr)
        return 1

    matrix = np.array(
        [_parse_vector(r["embedding_text"]) for r in rows], dtype=np.float32
    )
    projected = _pca_3d(matrix)

    payload = _emit_payload(version, rows, projected)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload), encoding="utf-8")
    print(
        f"wrote {args.out.relative_to(REPO_ROOT)} "
        f"(corpus_version={version}, points={len(rows)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
