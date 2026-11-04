# DEPENDENCY AUDIT — Enterprise Billing Automation (EBA)

**Data da Auditoria:** 2026-11-03  
**Status:** 🔴 Nenhuma dependência definida — Projeto Greenfield  
**Versão do Documento:** 1.0.0

---

## 1. SUMÁRIO EXECUTIVO

Nenhum arquivo de dependências existe no repositório. Este documento define as dependências **recomendadas e justificadas** para cada componente da stack, com versões mínimas, rationale técnico e flags de risco.

> [!IMPORTANT]
> Todas as versões indicadas representam os **mínimos recomendados** no momento da auditoria (2026-11-03). Devem ser fixadas com versões exatas em `pyproject.toml` e `package.json` para garantir builds reproduzíveis.

---

## 2. DEPENDÊNCIAS DO BACKEND (Python)

### 2.1 Problema de Versão do Python

| Item | Detalhe |
|------|---------|
| **ID** | DEP-001 |
| **Arquivo** | `backend/pyproject.toml` |
| **Problema** | Python 3.14.4 instalado no ambiente; stack requer 3.12+. Python 3.14 não é LTS e diversas bibliotecas críticas (Celery 5.x, algumas extensões C do SQLAlchemy) podem não ter wheels pré-compilados para 3.14, gerando falhas de instalação ou necessidade de compilação local. |
| **Impacto** | Build instável, potencial incompatibilidade com bibliotecas de produção |
| **Severidade** | 🟡 MEDIUM |
| **Recomendação** | Usar Python 3.12 (LTS, amplamente suportado) via `uv` ou `pyenv`. Fixar `requires-python = ">=3.12,<3.13"` no `pyproject.toml` para garantir consistência. |
| **Critério de Aceite** | `python --version` no venv retorna `3.12.x` |

---

### 2.2 Framework e API

| Pacote | Versão Mínima | Justificativa | Risco |
|--------|---------------|---------------|-------|
| `fastapi` | `>=0.115.0` | Framework principal. 0.115+ suporta Pydantic v2 nativo, melhora de performance de serialização significativa. | Baixo — projeto maduro |
| `pydantic` | `>=2.9.0` | Pydantic v2 (Rust core) — 5-50x mais rápido que v1. Obrigatório com FastAPI 0.115+. | Baixo — LTS |
| `pydantic-settings` | `>=2.5.0` | Carregamento de variáveis de ambiente com validação de tipos. Substitui `python-decouple`. | Baixo |
| `uvicorn[standard]` | `>=0.32.0` | ASGI server. `[standard]` inclui `httptools` e `websockets` para produção. | Baixo |
| `httpx` | `>=0.27.0` | Cliente HTTP assíncrono. Usado nos testes de integração da API e chamadas externas. | Baixo |
| `python-multipart` | `>=0.0.12` | Suporte a upload de arquivos (multipart/form-data). Obrigatório para upload de documentos no EBA. | Baixo |
| `orjson` | `>=3.10.0` | Serialização JSON ultra-rápida. 2-10x mais rápido que `json` stdlib. FastAPI suporta nativamente. | Baixo |

---

### 2.3 Banco de Dados

| Pacote | Versão Mínima | Justificativa | Risco |
|--------|---------------|---------------|-------|
| `sqlalchemy` | `>=2.0.36` | ORM principal. SQLAlchemy 2.x tem API melhorada (`Mapped`, `mapped_column`), suporte nativo async. **Nunca usar SQLAlchemy 1.x neste projeto.** | Baixo |
| `alembic` | `>=1.14.0` | Migrações de schema. Compatível com SQLAlchemy 2.x. | Baixo |
| `asyncpg` | `>=0.30.0` | Driver PostgreSQL assíncrono (para SQLAlchemy async engine). Alta performance. | Baixo |
| `psycopg2-binary` | `>=2.9.10` | Driver PostgreSQL síncrono. Necessário para Alembic (que não usa async). Usar `psycopg2-binary` apenas em dev; em prod usar `psycopg2` compilado. | ⚠️ Médio — `psycopg2-binary` não recomendado em produção |

> [!WARNING]
> **DEP-002:** `psycopg2-binary` inclui uma versão estática da libpq e pode ter conflitos em ambientes de produção. Em produção, usar `psycopg2` (sem binary) compilado contra a libpq do sistema, ou migrar para `psycopg[c]` (psycopg3). Alternativa moderna: usar `psycopg[binary]` 3.x que suporta modo async nativamente, eliminando a necessidade de dois drivers.

---

### 2.4 Workers Assíncronos

| Pacote | Versão Mínima | Justificativa | Risco |
|--------|---------------|---------------|-------|
| `celery` | `>=5.4.0` | Task queue distribuída. 5.4+ com suporte melhorado a Python 3.12. | ⚠️ Médio — verificar suporte a 3.14 |
| `redis` | `>=5.2.0` | Cliente Redis. Usado como broker Celery e cache. | Baixo |
| `celery[redis]` | `>=5.4.0` | Extra do Celery que inclui dependências para usar Redis como broker. | Baixo |
| `flower` | `>=2.0.1` | Dashboard web para monitoramento de workers Celery. Apenas desenvolvimento. | Baixo |

> [!NOTE]
> **DEP-003:** Avaliar uso de `dramatiq` como alternativa ao Celery. Dramatiq tem API mais simples, melhor suporte assíncrono e menos overhead. Para o volume de 10k-100k docs/mês, ambos são adequados. A decisão deve ser tomada na Fase 1 e não alterada depois sem refactoring significativo.

---

### 2.5 Armazenamento de Objetos

| Pacote | Versão Mínima | Justificativa | Risco |
|--------|---------------|---------------|-------|
| `boto3` | `>=1.35.0` | SDK AWS S3 — compatível com MinIO via configuração de endpoint personalizado. | Baixo |
| `minio` | `>=7.2.0` | SDK oficial MinIO. Mais simples que boto3 para operações básicas. **Escolher um** (boto3 ou minio SDK), não ambos. | Baixo |

> [!IMPORTANT]
> **DEP-004 — Decisão Arquitetural Pendente:** Escolher entre `boto3` e `minio` SDK. Recomendação: usar `boto3` com endpoint configurado para MinIO. Justificativa: se no futuro o projeto migrar para AWS S3 real, nenhuma mudança de código é necessária — apenas variáveis de ambiente. Usar `minio` SDK cria lock-in desnecessário com MinIO.

---

### 2.6 Segurança e Autenticação

| Pacote | Versão Mínima | Justificativa | Risco |
|--------|---------------|---------------|-------|
| `python-jose[cryptography]` | `>=3.3.0` | Geração e validação de JWT. O extra `[cryptography]` adiciona suporte a RS256/ES256 além de HS256. | ⚠️ Médio — verificar CVEs |
| `passlib[bcrypt]` | `>=1.7.4` | Hashing seguro de senhas com bcrypt. | ⚠️ Médio — bcrypt 4.x mudou API |
| `slowapi` | `>=0.1.9` | Rate limiting para FastAPI (baseado em `limits`). | Baixo |
| `itsdangerous` | `>=2.2.0` | Tokens assinados para e-mail de verificação, reset de senha. | Baixo |

> [!CAUTION]
> **DEP-005 — Vulnerabilidade Conhecida:** `python-jose` tem histórico de CVEs relacionados a algoritmos fracos. Verificar com `pip-audit` antes de cada release. Alternativa mais mantida: `PyJWT` (>=2.9.0) com `cryptography` library. Recomendação: usar `PyJWT` ao invés de `python-jose`.

> [!WARNING]
> **DEP-006:** `passlib` com `bcrypt` 4.x pode gerar warning de API deprecated. Verificar compatibilidade e considerar usar `bcrypt` diretamente ou `argon2-cffi` (algoritmo mais moderno e recomendado pelo OWASP para novas implementações).

---

### 2.7 E-mail

| Pacote | Versão Mínima | Justificativa | Risco |
|--------|---------------|---------------|-------|
| `fastapi-mail` | `>=1.4.1` | Envio de e-mail assíncrono integrado com FastAPI. Suporte a templates Jinja2. | Baixo |
| `jinja2` | `>=3.1.4` | Templates HTML para e-mails transacionais e geração de relatórios. | Baixo |

---

### 2.8 Utilitários

| Pacote | Versão Mínima | Justificativa | Risco |
|--------|---------------|---------------|-------|
| `python-dotenv` | `>=1.0.1` | Carregamento de `.env` em desenvolvimento. `pydantic-settings` já suporta, mas `python-dotenv` é útil em scripts. | Baixo |
| `structlog` | `>=24.4.0` | Logging estruturado (JSON). Essencial para sistemas de produção com volumes altos. | Baixo |
| `sentry-sdk[fastapi]` | `>=2.17.0` | Monitoramento de erros em produção. Extra `[fastapi]` adiciona integração automática. | Baixo |
| `pendulum` | `>=3.0.0` | Manipulação de datas/timezones (crítico para faturamento recorrente). Substitui `datetime` stdlib para casos complexos. | Baixo |
| `openpyxl` | `>=3.1.5` | Leitura/escrita de planilhas Excel — necessário para importação de dados de clientes. | Baixo |
| `weasyprint` ou `reportlab` | Qualquer | Geração de PDFs (boletos, NF-e, relatórios). Escolher um na Fase 1. | ⚠️ WeasyPrint requer libs C do sistema |

---

### 2.9 Dependências de Desenvolvimento

| Pacote | Versão Mínima | Justificativa |
|--------|---------------|---------------|
| `pytest` | `>=8.3.0` | Framework de testes |
| `pytest-asyncio` | `>=0.24.0` | Suporte a testes async |
| `pytest-cov` | `>=6.0.0` | Coverage de testes |
| `pytest-mock` | `>=3.14.0` | Mocking nos testes |
| `factory-boy` | `>=3.3.1` | Fixtures de objetos para testes |
| `httpx` | `>=0.27.0` | Cliente HTTP para testes de integração da API |
| `ruff` | `>=0.7.0` | Linting e formatação (substitui flake8, isort, black) |
| `mypy` | `>=1.13.0` | Type checking estático |
| `bandit` | `>=1.8.0` | Análise de segurança do código |
| `pip-audit` | `>=2.7.0` | Auditoria de vulnerabilidades nas dependências |
| `pre-commit` | `>=4.0.0` | Hooks de pré-commit (ruff, mypy, bandit) |

---

## 3. DEPENDÊNCIAS DO FRONTEND (Node.js / React)

### 3.1 Core

| Pacote | Versão | Justificativa |
|--------|--------|---------------|
| `react` | `^19.0.0` | Framework UI principal |
| `react-dom` | `^19.0.0` | Renderer DOM |
| `typescript` | `^5.6.0` | Tipagem estática |
| `vite` | `^6.0.0` | Build tool e dev server |
| `@vitejs/plugin-react` | `^4.3.0` | Plugin React para Vite |

### 3.2 Roteamento e Estado

| Pacote | Versão | Justificativa |
|--------|--------|---------------|
| `react-router-dom` | `^7.0.0` | Roteamento client-side |
| `@tanstack/react-query` | `^5.62.0` | Server state management — cache, invalidação, refetch automático. Essencial para dashboards de billing |
| `zustand` | `^5.0.0` | Client state management (auth, UI state). Mais simples que Redux para este caso de uso |

### 3.3 HTTP e API

| Pacote | Versão | Justificativa |
|--------|--------|---------------|
| `axios` | `^1.7.0` | Cliente HTTP com interceptors — essencial para injeção automática de JWT e refresh token |

### 3.4 UI e Estilos

| Pacote | Versão | Justificativa |
|--------|--------|---------------|
| `tailwindcss` | `^3.4.0` | CSS utility-first |
| `@radix-ui/*` | `^1.x` | Componentes acessíveis headless (base para shadcn/ui) |
| `lucide-react` | `^0.460.0` | Ícones SVG |
| `clsx` | `^2.1.0` | Utilitário de classnames condicionais |
| `tailwind-merge` | `^2.5.0` | Merge de classes Tailwind |

### 3.5 Formulários e Validação

| Pacote | Versão | Justificativa |
|--------|--------|---------------|
| `react-hook-form` | `^7.54.0` | Formulários performáticos (sem re-renders desnecessários) |
| `zod` | `^3.24.0` | Validação de schema com TypeScript-first. Integra com react-hook-form via `@hookform/resolvers` |
| `@hookform/resolvers` | `^3.9.0` | Integração zod + react-hook-form |

### 3.6 Tabelas e Dados

| Pacote | Versão | Justificativa |
|--------|--------|---------------|
| `@tanstack/react-table` | `^8.20.0` | Tabelas headless com virtualização — crítico para listagem de 10k+ documentos |
| `recharts` | `^2.13.0` | Gráficos para dashboards de billing |
| `date-fns` | `^4.1.0` | Manipulação de datas no frontend |

### 3.7 Dev Dependencies Frontend

| Pacote | Versão | Justificativa |
|--------|--------|---------------|
| `@types/react` | `^19.0.0` | Tipos TypeScript |
| `@types/react-dom` | `^19.0.0` | Tipos TypeScript |
| `eslint` | `^9.0.0` | Linting JavaScript/TypeScript |
| `@typescript-eslint/*` | `^8.0.0` | Regras ESLint para TypeScript |
| `vitest` | `^2.1.0` | Testes unitários (compatível com Vite) |
| `@testing-library/react` | `^16.0.0` | Testes de componentes React |

---

## 4. DEPENDÊNCIAS DE INFRAESTRUTURA (Docker)

### 4.1 Imagens Docker

| Serviço | Imagem | Tag | Justificativa |
|---------|--------|-----|---------------|
| PostgreSQL | `postgres` | `16-alpine` | Alpine: menor footprint, mais seguro |
| Redis | `redis` | `7-alpine` | Broker Celery + cache |
| MinIO | `minio/minio` | `latest` | Armazenamento de objetos S3-compatible |
| Nginx | `nginx` | `1.27-alpine` | Reverse proxy e serving de estáticos |

> [!CAUTION]
> **DEP-007 — Uso de `latest` tag:** MinIO usa `latest` — isso é aceitável para desenvolvimento local, mas em produção **DEVE** ser fixado em uma tag específica (ex.: `RELEASE.2024-11-07T00-52-20Z`). Tags mutáveis podem quebrar deploys.

---

## 5. ANÁLISE DE RISCOS DE DEPENDÊNCIAS

### 5.1 Riscos de Compatibilidade Python 3.14

| Pacote | Risco | Mitigação |
|--------|-------|-----------|
| `celery` | ⚠️ Médio — Celery 5.x tem suporte tardio a versões novas de Python | Usar Python 3.12 via uv/pyenv |
| `psycopg2-binary` | ⚠️ Médio — Wheels binários podem não existir para 3.14 | Usar Python 3.12 |
| `weasyprint` | 🔴 Alto — Requer GTK libs do sistema | Alternativa: `reportlab` |

### 5.2 Dependências com CVEs Históricos

| Pacote | Histórico | Ação |
|--------|-----------|------|
| `python-jose` | CVE-2024-33664, CVE-2024-33663 (2024) | Substituir por `PyJWT` |
| `pillow` | Múltiplos CVEs históricos de parsing de imagem | Manter sempre atualizado |
| `cryptography` | CVEs periódicos de timing attack | Usar versão mais recente |

### 5.3 Licenças

| Tipo de Licença | Pacotes | Compatibilidade com Projeto Comercial |
|-----------------|---------|---------------------------------------|
| MIT | FastAPI, Pydantic, React, Vite | ✅ Compatível |
| Apache 2.0 | SQLAlchemy, Celery, Redis-py | ✅ Compatível |
| BSD | Alembic, Uvicorn | ✅ Compatível |
| LGPL | psycopg2 | ✅ Compatível (lib dinâmica) |
| GPL | Qualquer | ❌ Evitar em código proprietário |

---

## 6. ESTRUTURA RECOMENDADA DO `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "eba-backend"
version = "0.1.0"
description = "Enterprise Billing Automation — Backend"
requires-python = ">=3.12,<3.15"
dependencies = [
    # API
    "fastapi>=0.115.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "uvicorn[standard]>=0.32.0",
    "httpx>=0.27.0",
    "python-multipart>=0.0.12",
    "orjson>=3.10.0",
    # Database
    "sqlalchemy>=2.0.36",
    "alembic>=1.14.0",
    "asyncpg>=0.30.0",
    "psycopg2-binary>=2.9.10",  # dev only; trocar por psycopg2 em prod
    # Workers
    "celery[redis]>=5.4.0",
    "redis>=5.2.0",
    # Storage
    "boto3>=1.35.0",
    # Security
    "PyJWT>=2.9.0",
    "cryptography>=43.0.0",
    "passlib[bcrypt]>=1.7.4",
    "slowapi>=0.1.9",
    "itsdangerous>=2.2.0",
    # Email
    "fastapi-mail>=1.4.1",
    "jinja2>=3.1.4",
    # Utilities
    "structlog>=24.4.0",
    "pendulum>=3.0.0",
    "openpyxl>=3.1.5",
    "sentry-sdk[fastapi]>=2.17.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "pytest-mock>=3.14.0",
    "factory-boy>=3.3.1",
    "ruff>=0.7.0",
    "mypy>=1.13.0",
    "bandit>=1.8.0",
    "pip-audit>=2.7.0",
    "pre-commit>=4.0.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "S", "ANN"]
ignore = ["ANN101", "ANN102"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=80"

[tool.coverage.run]
branch = true
omit = ["tests/*", "alembic/*"]
```

---

## 7. CONCLUSÃO E AÇÕES REQUERIDAS

| Prioridade | Ação |
|------------|------|
| 🔴 P0 | Instalar `uv` e Python 3.12 via `uv` |
| 🔴 P0 | Criar `backend/pyproject.toml` com dependências fixadas |
| 🔴 P0 | Criar `frontend/package.json` com dependências fixadas |
| 🟠 P1 | Configurar `pre-commit` com ruff, mypy, bandit |
| 🟠 P1 | Substituir `python-jose` por `PyJWT` |
| 🟡 P2 | Avaliar `psycopg2-binary` vs `psycopg[binary]` 3.x |
| 🟡 P2 | Decidir entre `minio` SDK e `boto3` |
| 🔵 P3 | Avaliar `argon2-cffi` vs `bcrypt` para hashing |

---
*Gerado em 2026-11-03 | EBA Technical Assessment v1.0*

