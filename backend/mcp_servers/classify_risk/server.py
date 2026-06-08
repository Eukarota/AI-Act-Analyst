"""
FastMCP server for classify_risk.

Run with: `python -m backend.mcp_servers.classify_risk`

Requires a live LLM endpoint via BOUSSOLE_LLM_URL and BOUSSOLE_LLM_MODEL.
For tests, use the core function with FakeLLM directly.
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from backend.adapters.vllm_provider import SelfHostedVLLM
from backend.mcp_servers._common import JsonDict, classification_to_json
from backend.mcp_servers.classify_risk.core import ClassifyRiskArgs, classify_risk
from backend.prompts.loader import default_registry
from regulations.ai_act.rules import AiActRules


def build_default_server() -> FastMCP:
    mcp = FastMCP("boussole.classify_risk")
    rules = AiActRules()
    prompts = default_registry()

    base_url = os.environ.get("BOUSSOLE_LLM_URL", "http://localhost:11434")
    model_id = os.environ.get("BOUSSOLE_LLM_MODEL", "mistral:7b-instruct")
    llm = SelfHostedVLLM(base_url, model_id=model_id)

    @mcp.tool()
    async def classify(
        system_description: str,
        declared_attributes: dict[str, Any] | None = None,
    ) -> JsonDict:
        """
        Extract attributes from the description and classify against the AI Act.

        Returns a classification with supporting article references; the rules
        layer decides the tier deterministically once attributes are extracted.
        """
        async with llm as live:
            result = await classify_risk(
                ClassifyRiskArgs(
                    system_description=system_description,
                    declared_attributes=declared_attributes,
                ),
                llm=live,
                rules=rules,
                prompts=prompts,
            )
        return {
            "attributes": result.attributes.model_dump(),
            "classification": classification_to_json(result.classification),
        }

    return mcp


def main() -> None:
    mcp = build_default_server()
    mcp.run()


if __name__ == "__main__":
    main()
