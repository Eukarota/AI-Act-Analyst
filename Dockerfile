# Boussole backend image.
#
# Multi-stage so the runtime image carries only the compiled site-packages,
# the source, and the corpus fixture. No build toolchain in prod.
#
# Build:
#   docker build -t boussole-backend:dev .
# Run:
#   docker run --rm -p 8000:8000 \
#     -e BOUSSOLE_DATABASE_URL=postgresql://... \
#     -e BOUSSOLE_LLM_URL=https://... \
#     -e BOUSSOLE_LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3 \
#     boussole-backend:dev

ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
 && cp /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Copy only what `uv sync` needs to resolve; this keeps the dep cache layer
# stable across source-only changes.
COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-dev --extra backend --extra rag --extra agent \
 || uv sync --no-dev --extra backend --extra rag --extra agent

# Now copy the actual source.
COPY backend ./backend
COPY regulations ./regulations
COPY prompts ./prompts
COPY scripts ./scripts

RUN uv sync --frozen --no-dev --extra backend --extra rag --extra agent \
 || uv sync --no-dev --extra backend --extra rag --extra agent

FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    BOUSSOLE_LOG_LEVEL=INFO

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd -r boussole \
 && useradd -r -g boussole -d /app -s /sbin/nologin boussole

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/backend ./backend
COPY --from=builder /app/regulations ./regulations
COPY --from=builder /app/prompts ./prompts
COPY --from=builder /app/scripts ./scripts

USER boussole

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys;urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3)" || exit 1

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "backend.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
