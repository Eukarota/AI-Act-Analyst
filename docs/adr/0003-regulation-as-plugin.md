# 0003: Regulation as a plugin Protocol

Date: 2026-06-09
Status: Accepted

## Context

The AI Act is the first regulation Boussole assesses. RGPD, DORA, and
NIS2 are credible second, third, and fourth additions for the same
buyer. The agent core (LangGraph state machine, retrieval, grounding,
report assembler) is regulation-agnostic by design; the temptation when
shipping the first regulation is to let AI-Act-specific assumptions
leak into the core.

## Decision

A `Regulation` Protocol lives at `backend/ports/regulation.py`:

```python
class Regulation(Protocol):
    name: str
    corpus_loader: CorpusLoader
    chunker_config: ChunkerConfig
    classifier_rules: RuleSet
    obligations_map: ObligationsMap
    document_templates: TemplateSet
    defined_terms: Glossary
    timeline: TimelineConfig
```

The AI Act is one implementation under `regulations/ai_act/`. Adding
RGPD or DORA is a parallel `regulations/<name>/` directory implementing
the same Protocol, with zero changes to `backend/agent/`.

A conformance test suite at `tests/regulation_conformance/` runs a
fixture regulation end-to-end against the agent core. Any new plugin
must pass that suite.

## Consequences

Positive:

- The cabinet-phase product story is "we plug in your regulation",
  backed by a working pattern, not a slide deck claim.
- The agent core in `backend/agent/` is reusable IP for the eventual
  agency.

Negative:

- The Protocol is now part of the contract and resists changes. Adding
  a method means updating every plugin.
- Some regulation-specific reasoning (e.g. Art. 6(3) carve-out for the
  AI Act) is hard to express without leaking into the rule semantics.
  The current pragmatic answer is: the rules layer keeps such systems
  high-risk by default, and the clarify loop surfaces the carve-out as
  a question the operator answers.
