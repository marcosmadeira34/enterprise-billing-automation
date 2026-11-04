# Enterprise Billing Automation (EBA)

Plataforma corporativa de automação de faturamento recorrente, contratos e documentos fiscais para empresas prestadoras de serviços.

Projetada para volumes de **10.000 a 100.000 documentos mensais** com arquitetura **Modular Monolith** extensível e configurável para integrações e regras comerciais sob demanda.

---

## 🛠 Stack Tecnológica

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x (asyncpg), Alembic, Pydantic v2
- **Workers & Filas:** Celery, Redis
- **Storage:** MinIO (compatível S3)
- **Banco de Dados:** PostgreSQL 16
- **Frontend:** React 19, TypeScript, Vite, TanStack Query/Table, Tailwind CSS
- **Infraestrutura:** Docker Compose, Nginx, MailHog (dev)
- **Qualidade & Segurança:** Pytest, Ruff, Mypy, Bandit, pre-commit

---

## 🚀 Guia de Início Rápido (Setup em 5 Minutos)

### Pré-requisitos

- Git
- Docker e Docker Compose plugin
- (Opcional para rodar localmente sem Docker) [uv](https://astral.sh/uv) + Node.js 22+

### 1. Clonar e Configurar Variáveis de Ambiente

```bash
git clone <url-do-repositorio>
cd enterprise-billing-automation

# Copie o arquivo de exemplo
cp .env.example .env

# Gere uma SECRET_KEY segura (mínimo 32 caracteres)
# No Linux/WSL ou Python:
python3 -c "import secrets; print(secrets.token_hex(32))"
# Cole o valor gerado em SECRET_KEY no arquivo .env
```

Ajuste também senhas locais em `.env` se desejar (`POSTGRES_PASSWORD`, `REDIS_PASSWORD`, etc.).

### 2. Iniciar a Plataforma via Docker Compose

```bash
# Sobe banco, redis, minio, mailhog, api, celery workers e frontend
make up
# ou: docker compose up -d
```

### 3. Acessos aos Serviços

| Serviço | URL | Descrição |
|---|---|---|
| **Frontend Web** | [http://localhost:5173](http://localhost:5173) | Interface do Usuário |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | API FastAPI |
| **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Documentação Interativa OpenAPI |
| **Celery Flower** | [http://localhost:5555/flower](http://localhost:5555/flower) | Monitoramento de Tarefas Assíncronas |
| **MinIO Console** | [http://localhost:9001](http://localhost:9001) | Console do Storage de Documentos |
| **MailHog** | [http://localhost:8025](http://localhost:8025) | Webmail fake para inspeção de e-mails |

---

## 🏗 Estrutura do Repositório

```
enterprise-billing-automation/
├── backend/                  # Backend FastAPI + Celery
│   ├── app/
│   │   ├── api/              # Routers (health, v1)
│   │   ├── core/             # Config, security, database, logging
│   │   ├── modules/          # Módulos de domínio isolados (Modular Monolith)
│   │   │   ├── auth/         # Autenticação e RBAC
│   │   │   ├── companies/    # Gestão de empresas e multi-tenancy
│   │   │   ├── contracts/    # Contratos recorrentes
│   │   │   ├── billing/      # Faturamento, cálculos e faturas
│   │   │   ├── documents/    # Gestão de anexos e MinIO
│   │   │   ├── notifications/# E-mails e webhooks
│   │   │   └── audit/        # Trilha de auditoria imutável
│   │   ├── tasks/            # Definição e worker do Celery
│   │   └── models/           # Shared models & Base
│   ├── alembic/              # Migrações de banco
│   └── tests/                # Testes unitários, de integração e segurança
├── frontend/                 # SPA React + Vite + TypeScript
│   ├── src/
│   │   ├── components/       # Componentes reutilizáveis e UI
│   │   ├── pages/            # Telas da aplicação
│   │   ├── services/         # Cliente Axios e chamadas de API
│   │   └── store/            # Estado global (Zustand)
├── docs/                     # Documentação técnica e auditorias
│   └── technical-assessment/ # Relatórios de auditoria inicial
├── infra/                    # Configurações de Nginx e infraestrutura
└── scripts/                  # Scripts operacionais e seeds
```

---

## 🧪 Comandos Úteis (`make`)

| Comando | Descrição |
|---|---|
| `make up` | Inicia todos os serviços no Docker Compose |
| `make down` | Para todos os containers |
| `make logs` | Visualiza logs em tempo real |
| `make test` | Roda testes do backend e frontend |
| `make lint` | Executa Ruff (Python) e ESLint (Frontend) |
| `make format` | Formata automaticamente o código |
| `make typecheck` | Executa Mypy e verificação TypeScript |
| `make audit` | Executa verificações de segurança (`pip-audit` / `npm audit`) |

---

## 🔒 Auditoria Técnica e Documentos

Consulte a pasta [`docs/technical-assessment/`](docs/technical-assessment/):
- `REPOSITORY_AUDIT.md`: Levantamento inicial de gaps.
- `DEPENDENCY_AUDIT.md`: Análise de compatibilidade de bibliotecas.
- `ARCHITECTURE_GAP_ANALYSIS.md`: Estrutura do Modular Monolith e patterns.
- `SECURITY_GAP_ANALYSIS.md`: Mitigações OWASP Top 10 e LGPD.
- `IMPLEMENTATION_ROADMAP.md`: Cronograma sequencial de implementação.

