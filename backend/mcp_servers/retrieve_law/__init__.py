"""retrieve_law MCP tool: hybrid retrieval over a regulation's corpus."""

from backend.mcp_servers.retrieve_law.core import (
    RetrieveLawArgs,
    RetrieveLawResult,
    retrieve_law,
)

__all__ = ["RetrieveLawArgs", "RetrieveLawResult", "retrieve_law"]
