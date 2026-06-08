"""lookup_obligations MCP tool: tier -> obligations + article refs."""

from backend.mcp_servers.lookup_obligations.core import (
    LookupObligationsArgs,
    LookupObligationsResult,
    lookup_obligations,
)

__all__ = [
    "LookupObligationsArgs",
    "LookupObligationsResult",
    "lookup_obligations",
]
