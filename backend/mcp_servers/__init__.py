"""
MCP tools for Boussole.

Each subpackage holds a pure-function core (callable from the agent or tests)
plus a FastMCP server (runnable as a standalone MCP service via stdio).
"""

from backend.mcp_servers import (
    analyze_gaps,
    classify_risk,
    draft_documentation,
    lookup_obligations,
    retrieve_law,
)

__all__ = [
    "analyze_gaps",
    "classify_risk",
    "draft_documentation",
    "lookup_obligations",
    "retrieve_law",
]
