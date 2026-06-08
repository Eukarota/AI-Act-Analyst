# 0004: Hybrid retrieval is mandatory for legal text

Date: 2026-06-09
Status: Accepted

## Context

Pure-dense retrieval (vector similarity over chunk embeddings) is the
default in most RAG tutorials. It fails on legal text. The reasons are
concrete:

- Article numbers are tokens, not concepts. "Art. 9" must be retrieved
  exactly when the agent asks for it; an embedding search by semantic
  similarity returns Art. 8 and Art. 10 as readily.
- Art. 3 defined terms have legal meanings that differ from their
  natural-language priors ("provider", "deployer", "placing on the
  market"). A dense model trained on the open web returns the natural
  prior more often than the legal definition.
- Boundary cases between Annex III categories ("biometric" vs.
  "biometric categorisation" vs. "remote biometric identification") hinge
  on phrase-level exact matches.

## Decision

Retrieval is the union of dense + sparse, fused with Reciprocal Rank
Fusion (RRF), then re-ranked with a cross-encoder. See
`backend/rag/retrieve.py`:

- Dense: pgvector over multilingual-e5-large embeddings.
- Sparse: Postgres `tsvector` with `to_tsvector('simple', text)` and
  GIN indexing for sub-second BM25-style recall.
- Fusion: RRF with k=60, top_n=40.
- Re-rank: bge-reranker-v2 cross-encoder, top_k=8.

Each agent node passes a `scope` (`art_5_prohibited`,
`annex_iii_high_risk_uses`, `art_50_transparency`, etc.) so retrieval
is bounded; there is no global pass.

## Consequences

Positive:

- Exact article references and Art. 3 defined terms recall correctly.
- The cross-encoder rerank caps the LLM context at the top 8 passages,
  which fits the 8k token budget the production runner enforces.
- Scoped retrieval is auditable in the trace: every node logs its
  scope and its returned citations.

Negative:

- Two retrieval paths and a reranker model are more moving parts than
  a single dense call. The performance budget (p95 < 5 s) has to
  account for the reranker's per-passage cost.
- The reranker model is open-weight but not Mistral-aligned. We
  document the dependency and host it in-jurisdiction; an EU-resident
  swap is a Phase-12 candidate, not a blocker.
