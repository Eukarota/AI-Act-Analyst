.PHONY: help install lint type test smoke index-corpus dev-backend dev-frontend eval clean \
        up-db down-db up-llm down-llm down integration-test

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
	@echo "  dev-backend       Run FastAPI + MCP servers locally (Phase 7)"
	@echo "  dev-frontend      Run Next.js dev server (Phase 8)"
	@echo "  eval              Run the eval suite against the frozen baseline (Phase 9)"

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

dev-frontend:
	cd frontend && npm install && npm run dev

eval:
	uv run python eval/run_eval.py --regulation ai_act \
		--baseline eval/baselines/$$(cat regulations/ai_act/corpus/VERSION).json --report

clean:
	rm -rf .venv .ruff_cache .mypy_cache .pytest_cache **/__pycache__ dist build
