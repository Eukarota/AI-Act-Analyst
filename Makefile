.PHONY: help install lint type test smoke index-corpus project-chunks dev-backend dev-backend-fake \
        dev-frontend frontend-build frontend-lint eval eval-smoke eval-freeze \
        reindex-and-eval clean up-db down-db up-llm down-llm down integration-test \
        demo-local demo-local-down demo-up demo-down

help:
	@echo "Boussole targets:"
	@echo "  install           Install dev + backend + rag + agent dependencies via uv"
	@echo "  lint              Run ruff"
	@echo "  type              Run mypy"
	@echo "  test              Run pytest (excludes integration and eval markers)"
	@echo "  smoke             Run the Phase 1 smoke test"
	@echo "  integration-test  Run pytest with the 'integration' marker only"
	@echo "  index-corpus      Fetch and index the AI Act corpus (Phase 2)"
	@echo "  up-db / down-db   Start / stop the Postgres+pgvector dev container"
	@echo "  up-llm / down-llm Start / stop the vLLM container (GPU host only)"
	@echo "  down              Stop all dev containers"
	@echo "  dev-backend       Run FastAPI locally against Postgres run-store (Phase 7)"
	@echo "  dev-backend-fake  Run FastAPI locally against the in-memory run-store (no DB)"
	@echo "  dev-frontend      Run Next.js dev server (Phase 8)"
	@echo "  eval-smoke        Run the 5-case smoke eval (fast CI sanity check)"
	@echo "  eval              Run the gold eval (§12.1 gates) against the frozen baseline"
	@echo "  eval-freeze       Re-freeze the baseline at the current corpus_version"
	@echo ""
	@echo "Demo targets:"
	@echo "  demo-local        Bring up Postgres + index corpus locally; next steps printed"
	@echo "  demo-local-down   Tear down the local demo (stops Postgres + vLLM containers)"
	@echo "  demo-up           Provision the full prod stack on OVH (terraform apply)"
	@echo "  demo-down         Destroy the prod stack on OVH (terraform destroy)"

install:
	uv sync --all-extras

lint:
	uv run ruff check .
	uv run ruff format --check .

type:
	uv run mypy backend regulations tests

test:
	uv run pytest -m "not integration and not eval"

smoke:
	uv run pytest tests/test_phase1_smoke.py -v

integration-test:
	uv run pytest -m integration -v

index-corpus:
	uv run python scripts/index_corpus.py --regulation ai_act

# 3D projection of the indexed embeddings for the RAG cube UI. Run after
# any successful `make index-corpus` so the projection matches the corpus
# the backend will serve.
project-chunks:
	uv run python scripts/project_chunks.py

up-db:
	docker compose -f docker-compose.dev.yml up -d postgres

down-db:
	docker compose -f docker-compose.dev.yml stop postgres

up-llm:
	docker compose -f docker-compose.dev.yml --profile llm up -d vllm

down-llm:
	docker compose -f docker-compose.dev.yml --profile llm stop vllm

down:
	docker compose -f docker-compose.dev.yml --profile llm down

dev-backend:
	uv run uvicorn backend.api.app:app --reload --port 8000

dev-backend-fake:
	BOUSSOLE_USE_IN_MEMORY_STORE=true \
	  uv run uvicorn backend.api.app:app --reload --port 8000

dev-frontend:
	cd frontend && npm install && npm run dev

frontend-build:
	cd frontend && npm install && npm run build

frontend-lint:
	cd frontend && npm run lint
	cd frontend && npm run typecheck

eval-smoke:
	uv run python eval/run_eval.py --regulation ai_act --smoke --report

eval:
	uv run python eval/run_eval.py --regulation ai_act --gold \
		--baseline eval/baselines/$$(cat regulations/ai_act/corpus/VERSION).json --report

eval-freeze:
	uv run python eval/run_eval.py --regulation ai_act --gold --freeze-baseline --report

reindex-and-eval:
	uv run python scripts/reindex_and_eval.py --regulation ai_act --source local --target memory

clean:
	rm -rf .venv .ruff_cache .mypy_cache .pytest_cache **/__pycache__ dist build

# Local end-to-end demo for portfolio reviewers. Uses Mistral La Plateforme
# (or local Ollama) for inference; no GPU required. Cost: 0 EUR for the
# infra layer.
#
# Real RAG pipeline:
#   1. Postgres + pgvector via docker compose.
#   2. scripts/index_corpus.py downloads Regulation (EU) 2024/1689 from
#      EUR-Lex, parses it into article/recital/annex chunks, embeds them
#      with multilingual-e5-large (downloads ~1.1 GB on first run), upserts
#      into pgvector. Idempotent: re-running with unchanged source is a
#      no-op.
#   3. Backend connects to pgvector at query time. Same e5 model embeds
#      user queries; hybrid retrieval (dense + tsvector + RRF + reranker)
#      returns cited passages.
demo-local: up-db
	@echo ">> waiting for postgres to be healthy..."
	@until docker compose -f docker-compose.dev.yml ps postgres --format '{{.Health}}' | grep -q healthy; do sleep 1; done
	@echo ">> indexing the AI Act corpus (downloads OJ XHTML from the EU Publications Office cellar + multilingual-e5-large; first run ~5 minutes)..."
	@uv run python scripts/index_corpus.py --regulation ai_act
	@echo ">> projecting embeddings to 3D for the RAG cube UI..."
	@uv run python scripts/project_chunks.py
	@echo ""
	@echo "============================================================"
	@echo "Local demo ready. In two separate terminals, run:"
	@echo "  terminal 1: make dev-backend"
	@echo "  terminal 2: make dev-frontend"
	@echo "Then open: http://localhost:3000"
	@echo ""
	@echo "Tear it down with:  make demo-local-down"
	@echo "============================================================"

demo-local-down:
	docker compose -f docker-compose.dev.yml --profile llm down

# On-demand provisioning of the full sovereign stack on OVH. Use ONLY when
# a live demo or paying mission needs it. The bill starts the moment apply
# succeeds. Run `make demo-down` to return to zero.
demo-up:
	@command -v /opt/homebrew/bin/terraform >/dev/null 2>&1 || command -v terraform >/dev/null 2>&1 || { echo "terraform not installed: brew install hashicorp/tap/terraform"; exit 1; }
	@test -f .env || { echo "missing .env (required for OVH_* credentials)"; exit 1; }
	@test -f infra/terraform/environments/prod/main.tfvars || { echo "missing infra/terraform/environments/prod/main.tfvars (cp from .example, fill service_name)"; exit 1; }
	@set -a; . ./.env; set +a; \
	  cd infra/terraform && \
	  $${TERRAFORM:-/opt/homebrew/bin/terraform} init && \
	  $${TERRAFORM:-/opt/homebrew/bin/terraform} apply -var-file=environments/prod/main.tfvars
	@echo ""
	@echo ">> Provisioned. Outputs:"
	@cd infra/terraform && $${TERRAFORM:-/opt/homebrew/bin/terraform} output
	@echo ""
	@echo "Next: enable pgvector + index corpus + apply k8s overlay."
	@echo "Tear down with:  make demo-down"

demo-down:
	@set -a; . ./.env; set +a; \
	  cd infra/terraform && \
	  $${TERRAFORM:-/opt/homebrew/bin/terraform} destroy -var-file=environments/prod/main.tfvars
	@echo ">> Destroyed. OVH bill returns to zero on those line items."
