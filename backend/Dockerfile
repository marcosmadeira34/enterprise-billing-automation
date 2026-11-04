# =============================================================================
# EBA Backend — Dockerfile
# Multi-stage: development | production
# =============================================================================

# ---------------------------------------------------------------------------
# Stage: base — dependências comuns
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

# Metadados
LABEL maintainer="EBA Team"
LABEL description="Enterprise Billing Automation — Backend API"

# Variáveis de ambiente Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    UV_SYSTEM_PYTHON=0

# Diretório de trabalho
WORKDIR /app

# Dependências do sistema (mínimas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# ---------------------------------------------------------------------------
# Stage: dependencies — instala dependências Python
# ---------------------------------------------------------------------------
FROM base AS dependencies

COPY pyproject.toml ./

# Cria venv e instala dependências de produção
RUN uv venv .venv --python 3.12 && \
    uv pip install --python .venv/bin/python -e "."

# ---------------------------------------------------------------------------
# Stage: development — hot-reload, devtools
# ---------------------------------------------------------------------------
FROM dependencies AS development

# Instala dependências de desenvolvimento também
RUN uv pip install --python .venv/bin/python -e ".[dev]"

# Adiciona venv ao PATH
ENV PATH="/app/.venv/bin:$PATH"

COPY . .

EXPOSE 8000

# Comando padrão (sobrescrito pelo docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------------------------------------------------------------------------
# Stage: production — imagem final enxuta
# ---------------------------------------------------------------------------
FROM base AS production

# Copia apenas o venv instalado (sem devtools)
COPY --from=dependencies /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Cria usuário não-root
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

