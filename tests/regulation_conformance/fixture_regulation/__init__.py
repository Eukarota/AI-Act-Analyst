"""
Fixture regulation for the regulation-conformance suite.

A minimal toy regulation that implements every Regulation Protocol component.
Any new regulation plugin under regulations/<name>/ must pass the conformance
tests against the same Protocol. This fixture proves the agent core is
regulation-agnostic (CLAUDE.md section 12.5).
"""

from tests.regulation_conformance.fixture_regulation.plugin import FixtureRegulation

__all__ = ["FixtureRegulation"]
