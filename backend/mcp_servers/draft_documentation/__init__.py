"""draft_documentation MCP tool: render Annex IV + Art. 50 documents."""

from backend.mcp_servers.draft_documentation.core import (
    DraftDocumentationArgs,
    DraftDocumentationResult,
    draft_documentation,
)

__all__ = ["DraftDocumentationArgs", "DraftDocumentationResult", "draft_documentation"]
