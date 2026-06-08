"""
End-to-end grounding fail-closed test.

CLAUDE.md non-negotiable: a planted uncited claim must never reach a final
report. Phase 6's assemble_report node enforces this by import of the same
assert_grounded function the eval harness uses.

We exercise the path by patching the assemble_report claim builder so the
test does not require constructing an actual unhappy LLM output.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.agent.graph import run_assessment
from backend.rag.grounding import Claim, GroundingError
from tests.agent.conftest import AgentEnv, initial_state
from tests.agent.test_graph_e2e import (
    _RECRUITMENT_ATTRIBUTES,
    RECRUITMENT_SYSTEM_DESCRIPTION,
)


def _planted_claims_builder(_state: object) -> list[Claim]:
    """A claim builder that returns one citation that is NOT in the retrieved set."""
    from backend.agent.state import Citation

    return [
        Claim(
            text="Fabricated claim referencing a non-retrieved article.",
            citations=(
                Citation(
                    celex_id="32024R1689",
                    article="999",  # not present anywhere in the fixture
                    corpus_version="planted",
                ),
            ),
            source_node="test_plant",
        ),
    ]


async def test_planted_uncited_claim_is_rejected_fail_closed(
    agent_env: AgentEnv,
) -> None:
    agent_env.script_extraction(RECRUITMENT_SYSTEM_DESCRIPTION, _RECRUITMENT_ATTRIBUTES)
    state = initial_state(RECRUITMENT_SYSTEM_DESCRIPTION)

    with (
        patch(
            "backend.agent.nodes.assemble_report._build_claims",
            side_effect=_planted_claims_builder,
        ),
        pytest.raises(GroundingError) as exc,
    ):
        await run_assessment(state, deps=agent_env.deps)

    assert exc.value.result.violation_count >= 1
    unmatched_articles = {
        c.article for v in exc.value.result.violations for c in v.unmatched_citations
    }
    assert "999" in unmatched_articles
