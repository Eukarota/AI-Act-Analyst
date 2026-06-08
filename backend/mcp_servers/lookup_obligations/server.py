"""
FastMCP server for lookup_obligations.

Run with: `python -m backend.mcp_servers.lookup_obligations`
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from backend.agent.state import (
    ActorRole,
    ClassificationResult,
    Tier,
)
from backend.mcp_servers._common import (
    JsonDict,
    citation_to_json,
)
from backend.mcp_servers.lookup_obligations.core import (
    LookupObligationsArgs,
    lookup_obligations,
)
from regulations.ai_act.obligations import AiActObligations
from regulations.ai_act.rules import RULES_VERSION


def build_default_server() -> FastMCP:
    mcp = FastMCP("boussole.lookup_obligations")
    obligations_map = AiActObligations()

    @mcp.tool()
    async def lookup(
        tier: str,
        actor_role: str | None = None,
    ) -> JsonDict:
        """
        Return the obligations that apply at the given tier.

        Each obligation carries an article reference + citation.
        """
        classification = ClassificationResult(
            tier=Tier(tier),
            fired_rule="external.tool_call",
            supporting_refs=(),
            confidence=1.0,
            rationale="Provided externally via MCP call.",
            rules_version=RULES_VERSION,
        )
        result = await lookup_obligations(
            LookupObligationsArgs(
                classification=classification,
                actor_role=ActorRole(actor_role) if actor_role else None,
            ),
            obligations_map=obligations_map,
        )
        return {
            "tier": result.tier,
            "obligations": [
                {
                    "obligation_id": o.obligation_id,
                    "summary": o.summary,
                    "article_ref": o.article_ref,
                    "applies_to": [r.value for r in o.applies_to],
                    "citation": citation_to_json(o.citation),
                }
                for o in result.obligations
            ],
        }

    return mcp


def main() -> None:
    mcp = build_default_server()
    mcp.run()


if __name__ == "__main__":
    main()
