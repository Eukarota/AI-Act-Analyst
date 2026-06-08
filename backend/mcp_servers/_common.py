"""
Shared infrastructure for the Boussole MCP tools.

CLAUDE.md section 9: "Tools are pure and documented. Each MCP tool has a
docstring stating inputs, outputs, and citation guarantees."

Per the build plan, each tool ships in two forms:

  core.py    A pure async function exposing typed Args / Result dataclasses.
             The agent's LangGraph nodes (Phase 6) call this directly; tests
             call this directly; the MCP server delegates to it.

  server.py  A FastMCP server that translates JSON over stdio into the core
             call. Runnable with `python -m backend.mcp_servers.<tool>` and
             showcases the MCP half of the project's positioning.

This file holds the small pieces both layers share: the citation-serialisation
helpers (every tool response carries citation metadata per Phase 5 checkpoint)
and the JSON typing aliases.
"""

from __future__ import annotations

from typing import Any

from backend.agent.state import Citation, ClassificationResult, RetrievedPassage

JsonDict = dict[str, Any]


def citation_to_json(citation: Citation) -> JsonDict:
    """Citations are the load-bearing identifier in every tool response."""
    return {
        "celex_id": citation.celex_id,
        "article": citation.article,
        "paragraph": citation.paragraph,
        "annex_ref": citation.annex_ref,
        "recital_ref": citation.recital_ref,
        "lang": citation.lang,
        "url": citation.url,
        "corpus_version": citation.corpus_version,
        "short": citation.short(),
    }


def passage_to_json(passage: RetrievedPassage) -> JsonDict:
    return {
        "text": passage.text,
        "citation": citation_to_json(passage.citation),
        "score": passage.score,
        "retrieval_scope": passage.retrieval_scope,
    }


def classification_to_json(classification: ClassificationResult) -> JsonDict:
    return {
        "tier": classification.tier.value,
        "fired_rule": classification.fired_rule,
        "supporting_refs": [citation_to_json(c) for c in classification.supporting_refs],
        "confidence": classification.confidence,
        "rationale": classification.rationale,
        "rules_version": classification.rules_version,
    }
