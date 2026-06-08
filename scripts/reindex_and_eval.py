"""
reindex_and_eval.py: a thin orchestrator that re-indexes a regulation corpus
and, when the diff is non-empty, re-runs the gold eval against the new
corpus_version.

CLAUDE.md section 12.4: "A new corpus_version auto-triggers an eval re-run."
This script is the human-runnable surface of that rule. CI invokes the same
two steps (index + eval) via separate stages; this script lets a developer
do the same locally without remembering both commands.

Exit codes:
    0  no diff, or diff + eval gates green
    1  diff present and eval gates failed
    2  re-index failed
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-index corpus and trigger eval on change.")
    parser.add_argument("--regulation", required=True, choices=["ai_act"])
    parser.add_argument("--source", default="local", choices=["fetch", "local"])
    parser.add_argument("--target", default="memory", choices=["pgvector", "memory"])
    parser.add_argument(
        "--force-eval",
        action="store_true",
        help="Run the eval even when the diff is empty.",
    )
    return parser.parse_args()


async def _run_index(args: argparse.Namespace) -> int:
    from scripts.index_corpus import main as index_main

    sys.argv = [
        "index_corpus.py",
        "--regulation",
        args.regulation,
        "--source",
        args.source,
        "--target",
        args.target,
        "--use-fake-embedder",
    ]
    return await index_main()


def _load_latest_diff(regulation: str) -> dict[str, object]:
    version_file = REPO_ROOT / "regulations" / regulation / "corpus" / "VERSION"
    if not version_file.exists():
        return {}
    version = version_file.read_text(encoding="utf-8").strip()
    diff_path = REPO_ROOT / "regulations" / regulation / "corpus" / "diff" / f"{version}.json"
    if not diff_path.exists():
        return {}
    raw = json.loads(diff_path.read_text(encoding="utf-8"))
    return dict(raw) if isinstance(raw, dict) else {}


def _diff_is_empty(diff: dict[str, object]) -> bool:
    counts = diff.get("counts") or {}
    if not isinstance(counts, dict):
        return True
    return all(int(counts.get(k, 0)) == 0 for k in ("added", "removed", "changed"))


def _run_eval(regulation: str) -> int:
    version_file = REPO_ROOT / "regulations" / regulation / "corpus" / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip()
    baseline = REPO_ROOT / "eval" / "baselines" / f"{version}.json"
    cmd: list[str] = [
        sys.executable,
        str(REPO_ROOT / "eval" / "run_eval.py"),
        "--regulation",
        regulation,
        "--gold",
        "--report",
    ]
    if baseline.exists():
        cmd.extend(["--baseline", str(baseline)])
    result = subprocess.run(cmd, check=False)
    return result.returncode


async def amain() -> int:
    args = _parse_args()

    index_exit = await _run_index(args)
    if index_exit != 0:
        print(
            f"[reindex_and_eval] index_corpus failed with exit code {index_exit}", file=sys.stderr
        )
        return 2

    diff = _load_latest_diff(args.regulation)
    counts = diff.get("counts") or {}
    print(f"[reindex_and_eval] diff counts: {counts}")
    changed_buckets = diff.get("changed_article_buckets") or []
    if changed_buckets:
        print(f"[reindex_and_eval] changed sections: {', '.join(map(str, changed_buckets))}")

    if _diff_is_empty(diff) and not args.force_eval:
        print("[reindex_and_eval] diff empty, skipping eval re-run.")
        return 0

    print("[reindex_and_eval] running gold eval...")
    return _run_eval(args.regulation)


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    sys.exit(main())
