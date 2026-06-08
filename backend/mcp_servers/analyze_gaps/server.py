"""
FastMCP server for analyze_gaps.

Run with: `python -m backend.mcp_servers.analyze_gaps`
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from backend.agent.state import (
    ActorRole,
    ClassificationResult,
    Tier,
)
from backend.mcp_servers._common import JsonDict
from backend.mcp_servers.analyze_gaps.core import (
    AnalyzeGapsArgs,
    analyze_gaps,
)
from regulations.ai_act.obligations import AiActObligations
from regulations.ai_act.rules import RULES_VERSION


def build_default_server() -> FastMCP:
    mcp = FastMCP("boussole.analyze_gaps")
    obligations_map = AiActObligations()

    @mcp.tool()
    async def gap_analysis(
        tier: str,
        declared_controls: list[str],
        actor_role: str | None = None,
    ) -> JsonDict:
        """
        Compute a gap analysis: which obligations are covered, partial, missing.
        """
        classification = ClassificationResult(
            tier=Tier(tier),
            fired_rule="external.tool_call",
            supporting_refs=(),
            confidence=1.0,
            rationale="Provided externally via MCP call.",
            rules_version=RULES_VERSION,
        )
        obligations = obligations_map.obligations_for(classification)
        result = await analyze_gaps(
            AnalyzeGapsArgs(
                required=tuple(obligations),
                declared_controls=tuple(declared_controls),
                actor_role=ActorRole(actor_role) if actor_role else None,
            )
        )
        return {
            "coverage_ratio": result.coverage_ratio,
            "findings": [
                {
                    "obligation_id": f.obligation_id,
                    "status": f.status,
                    "notes": f.notes,
                    "declared_evidence": f.declared_evidence,
                }
                for f in result.findings
            ],
        }

    return mcp


def main() -> None:
    mcp = build_default_server()
    mcp.run()


if __name__ == "__main__":
    main()
