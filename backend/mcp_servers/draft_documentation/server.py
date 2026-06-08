"""
FastMCP server for draft_documentation.

Run with: `python -m backend.mcp_servers.draft_documentation`
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from backend.agent.state import (
    AttributeSet,
    ClassificationResult,
    Tier,
)
from backend.mcp_servers._common import JsonDict, citation_to_json
from backend.mcp_servers.draft_documentation.core import (
    DraftDocumentationArgs,
    draft_documentation,
)
from regulations.ai_act.document_templates import AiActTemplates
from regulations.ai_act.rules import RULES_VERSION


def build_default_server() -> FastMCP:
    mcp = FastMCP("boussole.draft_documentation")
    templates = AiActTemplates()

    @mcp.tool()
    async def draft(
        system_name: str,
        tier: str,
        attribute_purpose: str,
        documents_to_draft: list[str] | None = None,
        language: str = "fr",
    ) -> JsonDict:
        """
        Render selected document templates for the given classification tier.

        The actual classification + retrieval should happen upstream; this
        tool only renders. Returns drafted documents with citation lists.
        """
        classification = ClassificationResult(
            tier=Tier(tier),
            fired_rule="external.tool_call",
            supporting_refs=(),
            confidence=1.0,
            rationale="Provided externally via MCP call.",
            rules_version=RULES_VERSION,
        )
        attributes = AttributeSet(purpose=attribute_purpose)
        result = await draft_documentation(
            DraftDocumentationArgs(
                system_name=system_name,
                classification=classification,
                attributes=attributes,
                retrieved_passages=(),
                documents_to_draft=tuple(documents_to_draft or ()),
                language=language,
            ),
            templates=templates,
        )
        return {
            "documents": [
                {
                    "kind": d.kind,
                    "title": d.title,
                    "body": d.body,
                    "citations": [citation_to_json(c) for c in d.citations],
                }
                for d in result.documents
            ],
        }

    return mcp


def main() -> None:
    mcp = build_default_server()
    mcp.run()


if __name__ == "__main__":
    main()
