# 0002: The rules layer decides the tier, not the LLM

Date: 2026-06-09
Status: Accepted

## Context

CLAUDE.md section 6 mandates: "attribute extraction is the LLM's job;
the verdict is the rules layer's job." The temptation in any agentic
codebase is to let the LLM reason about Article 5, Annex III, and Art.
50 directly. That fails three different correctness tests at once:

- Determinism: same input must produce the same classification, twice
  in a row, six months apart, against a pinned model.
- Auditability: the rule that fired must be inspectable. "The LLM said
  so" is not an audit trail.
- Reproducibility under model rotation: when the upstream Mistral
  weight changes, the classification must not move with it.

## Decision

A pure function `AiActRules.classify(attributes: AttributeSet) ->
ClassificationResult` lives at `regulations/ai_act/rules/engine.py`.
The LLM populates `AttributeSet`. The rules layer produces the
`Tier`, the `fired_rule` identifier, and the `supporting_refs` to the
exact Article + paragraph that justifies the verdict. Same
`(attributes, rules_version)` produces an identical
`ClassificationResult`.

The ordering is fixed: Art. 5 prohibitions, then Annex I (regulated
products), then Annex III (high-risk uses), then Art. 50 (transparency),
then minimal. GPAI runs on a parallel track at the top.

`rules_version` is pinned into the `RunManifest`, so any assessment can
be replayed against the exact rule vintage that produced it.

## Consequences

Positive:

- Classification accuracy is testable in a table-driven unit suite, not
  in an eval that requires an LLM.
- An incident response can answer "why this tier?" by reading 200
  lines of Python, not by guessing what the model thought.
- Rule edits go through code review and `rules_version` bumps. The
  manifest reflects the move.

Negative:

- The rules layer is the highest-stakes correctness surface in the
  project. It needs an actual lawyer's review before the public eval
  number is published. TASKS_USER.md tracks this.
- Detecting Annex III uses from a free-form description still requires
  phrase matching. Keyword lists in `regulations/ai_act/rules/` are the
  pragmatic Phase 2 approach; tightening them is ongoing work, gated by
  the gold-set false-negative-high-risk metric.
