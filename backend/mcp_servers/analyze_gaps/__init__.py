"""analyze_gaps MCP tool: diff declared controls vs required obligations."""

from backend.mcp_servers.analyze_gaps.core import (
    AnalyzeGapsArgs,
    AnalyzeGapsResult,
    analyze_gaps,
)

__all__ = ["AnalyzeGapsArgs", "AnalyzeGapsResult", "analyze_gaps"]
