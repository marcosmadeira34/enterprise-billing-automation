# ARCHITECTURE GAP ANALYSIS — Enterprise Billing Automation (EBA)

**Data da Auditoria:** 2026-11-03  
**Arquitetura Proposta:** Modular Monolith  
**Status:** 🔴 Implementação: 0% — Greenfield  
**Versão do Documento:** 1.0.0

---

## 1. VISÃO GERAL DA ARQUITETURA PROPOSTA

```
┌─────────────────────────────────────────────────────────────────┐
│                    EBA — Modular Monolith                        │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React + Vite + TS)                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  Auth    │ │ Billing  │ │Contracts │ │    Reports       │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  API Gateway (FastAPI + Nginx)                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  /api/v1/auth  /api/v1/billing  /api/v1/contracts  ...    │  │
│  └────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Backend Modules (Python 3.12 + FastAPI)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  auth    │ │ billing  │ │contracts │ │    reports       │  │
│  │  module  │ │  module  │ │  module  │ │     module       │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Core (config, security, exceptions, middleware, events) │    │
│  └─────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│  Async Processing (Celery + Redis)                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│  │ billing  │ │  email   │ │ reports  │  queues                │
│  │  tasks   │ │  tasks   │ │  tasks   │                        │
│  └──────────┘ └──────────┘ └──────────┘                        │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                     │
│  ┌──────────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ PostgreSQL 16│ │  Redis 7 │ │  MinIO   │                    │
│  │  (principal) │ │ (cache+  │ │ (objetos)│                    │
│  │              │ │  broker) │ │          │                    │
│  └──────────────┘ └──────────┘ └──────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. ANÁLISE DE GAPS ARQUITETURAIS

### ARCH-001 — Módulos de Domínio Não Definidos

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-001 |
| **Componente** | `backend/app/modules/` |
| **Problema** | Nenhum módulo de domínio existe. A arquitetura Modular Monolith requer que cada domínio de negócio seja isolado em seu próprio módulo com router, service, models, schemas e testes próprios. |
| **Impacto** | Sem isolamento de domínio, código tende a acoplar-se; torna difícil extrair módulos para microserviços no futuro se necessário |
| **Severidade** | 🔴 CRITICAL |
| **Módulos Mínimos Necessários** | `auth`, `companies`, `contracts`, `billing`, `documents`, `notifications`, `audit` |
| **Recomendação** | Cada módulo deve seguir a estrutura: `router.py`, `service.py`, `models.py`, `schemas.py`, `tasks.py`, `exceptions.py`, `tests/` |
| **Critério de Aceite** | Cada módulo é completamente autocontido; cross-module dependencies passam apenas por interfaces definidas, nunca por acesso direto a models de outro módulo |

---

### ARCH-002 — Ausência de Application Factory Pattern

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-002 |
| **Componente** | `backend/app/main.py` |
| **Problema** | Sem `create_app()` factory. Sem ciclo de vida de startup/shutdown (lifespan). Conexões de banco e workers não são gerenciadas corretamente. |
| **Impacto** | Memory leaks em testes; conexões de banco não fechadas; impossibilidade de múltiplas instâncias da app em testes |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | Implementar `create_app()` factory com FastAPI `lifespan` context manager. Inicializar connection pools, Celery, e verificações de saúde no startup. |
| **Critério de Aceite** | `app = create_app()` cria instância isolada; testes criam instâncias independentes sem conflito |

---

### ARCH-003 — Ausência de Camada de Eventos (Event-Driven dentro do Monolito)

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-003 |
| **Componente** | `backend/app/core/events.py` |
| **Problema** | Sem sistema de eventos interno. Em um Modular Monolith, módulos se comunicam via eventos internos (dispatcher simples) em vez de chamadas diretas entre services. Isso preserva o isolamento e facilita futura extração de módulos. |
| **Impacto** | Acoplamento forte entre módulos (ex.: billing service chama notification service diretamente); impossibilidade de adicionar novos comportamentos sem modificar o módulo emissor |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Implementar dispatcher de eventos interno simples (não precisa ser um message broker — pode ser um `EventBus` em memória). Exemplos: `InvoiceCreated`, `ContractActivated`, `PaymentReceived`. Módulos subscribem a eventos de outros módulos sem dependência direta. |
| **Critério de Aceite** | Módulo A publica evento → Módulo B recebe e processa sem importar nada de A |

---

### ARCH-004 — Ausência de Repository Pattern

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-004 |
| **Componente** | `backend/app/modules/*/repository.py` |
| **Problema** | Sem camada de repositório. Sem abstração entre Service e Database. SQLAlchemy queries diretas em services dificultam testes (necessidade de banco real) e violam Single Responsibility Principle. |
| **Impacto** | Testes unitários de services requerem banco de dados; mudanças de ORM afetam toda a lógica de negócio |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Implementar Repository Pattern: `BaseRepository[T]` genérico com operações CRUD; repositories específicos por módulo (ex.: `InvoiceRepository`). Services recebem repositories via dependency injection. |
| **Critério de Aceite** | Services testados com mock de repository sem conexão ao banco; repository testado com banco de dados de teste |

---

### ARCH-005 — Ausência de Unit of Work Pattern

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-005 |
| **Componente** | `backend/app/core/unit_of_work.py` |
| **Problema** | Sem Unit of Work para gerenciamento de transações. Múltiplas operações em services diferentes podem deixar o banco em estado inconsistente se uma operação falhar no meio. |
| **Impacto** | Inconsistência de dados em operações de billing (ex.: fatura criada mas contrato não atualizado) |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Implementar `AsyncUnitOfWork` com context manager. Services que precisam de atomicidade recebem um UoW que agrupa repositories numa mesma sessão/transação. |
| **Critério de Aceite** | Falha em qualquer operação dentro de um UoW faz rollback de todas as operações anteriores; committed apenas quando tudo tem sucesso |

---

### ARCH-006 — Ausência de Camada de Extensibilidade (Plugin System)

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-006 |
| **Componente** | `backend/app/extensions/` |
| **Problema** | O requisito central do EBA é: "extensível e configurável para incorporar novas automações sem modificar o núcleo". Não há nenhum mecanismo de extensibilidade (plugin/hook system) definido. |
| **Impacto** | Cada nova automação de cliente requer modificação do core; impossibilidade de separar código genérico de código específico de cliente; violação do Open/Closed Principle |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | Implementar sistema de extensão baseado em: (1) **Hook Points** — pontos definidos no fluxo onde código externo pode ser injetado (ex.: `PRE_INVOICE_GENERATE`, `POST_PAYMENT_RECEIVED`); (2) **Plugin Registry** — registro de plugins por tenant/empresa; (3) **Configuration-Driven Rules** — regras de negócio específicas de cliente armazenadas em banco como configurações, não como código. |
| **Critério de Aceite** | Nova regra de cliente adicionada via configuração sem alterar nenhum arquivo do core; testes do core passam sem conhecimento das extensões |

---

### ARCH-007 — Ausência de Multi-Tenancy

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-007 |
| **Componente** | `backend/app/models/base.py`, `backend/app/core/tenant.py` |
| **Problema** | O modelo de negócio serve múltiplas empresas clientes. Sem implementação de multi-tenancy, dados de clientes diferentes podem vazar entre si (tenant isolation). |
| **Impacto** | 🚨 Risco de segurança crítico — vazamento de dados entre clientes é LGPD/GDPR violation |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | Implementar multi-tenancy via **Row-Level Security (RLS) no PostgreSQL** + `tenant_id` em todos os models. Middleware que extrai `tenant_id` do JWT e injeta no contexto da request. Todos os queries filtram por `tenant_id` automaticamente via base query class. |
| **Critério de Aceite** | Query de tenant A nunca retorna dados de tenant B; RLS verificado em testes de integração; `tenant_id` ausente resulta em 403 |

---

### ARCH-008 — Ausência de API Versioning Strategy

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-008 |
| **Componente** | `backend/app/api/` |
| **Problema** | Sem estratégia de versionamento de API definida. Sem prefixo `/api/v1/`. Clientes que integram com a API serão impactados por breaking changes sem versionamento. |
| **Impacto** | Breaking changes na API quebram integrações de clientes; impossibilidade de deprecar endpoints gracefully |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Usar URL versioning (`/api/v1/`). Manter versão atual em `APIRouter(prefix="/api/v1")`. Documentar política de deprecação (6 meses de suporte após anúncio de nova versão). |
| **Critério de Aceite** | Todos os endpoints servidos em `/api/v1/`; OpenAPI docs refletem versão |

---

### ARCH-009 — Ausência de Observabilidade

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-009 |
| **Componente** | `backend/app/core/telemetry.py` |
| **Problema** | Sem logging estruturado, sem métricas (Prometheus), sem tracing (OpenTelemetry). Para volume de 10k-100k documentos mensais, observabilidade é crítica para diagnóstico de problemas. |
| **Impacto** | Impossibilidade de debugar problemas em produção; sem alertas de degradação de performance |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Implementar: (1) Logging estruturado com `structlog` (JSON em produção); (2) Métricas com `prometheus-fastapi-instrumentator`; (3) OpenTelemetry para tracing distribuído (preparado para Grafana Tempo). Prometheus + Grafana citados na stack como "evolução". |
| **Critério de Aceite** | `/metrics` endpoint retorna métricas Prometheus; logs em JSON com `trace_id`, `tenant_id`, `request_id` |

---

### ARCH-010 — Ausência de Health Check e Readiness Probes

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-010 |
| **Componente** | `backend/app/api/health.py` |
| **Problema** | Sem endpoints de health check (`/health`, `/ready`, `/live`). Docker Compose e orquestradores (Kubernetes futuro) precisam desses endpoints para determinar se o serviço está funcional. |
| **Impacto** | Docker Compose não consegue determinar se o serviço iniciou corretamente; zero-downtime deploys impossíveis |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Implementar: `/health/live` (liveness — app está rodando), `/health/ready` (readiness — banco, Redis, MinIO acessíveis), `/health/startup` (startup probe). Retornar status de cada dependência individualmente. |
| **Critério de Aceite** | `GET /health/ready` retorna 200 quando todas as dependências estão up; retorna 503 se qualquer dependência falhar |

---

### ARCH-011 — Ausência de Estratégia de Cache

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-011 |
| **Componente** | `backend/app/core/cache.py` |
| **Problema** | Redis está na stack mas sem estratégia de uso definida. Para o volume esperado, sem cache, queries repetitivas sobrecarregam o banco. |
| **Impacto** | Performance degradada; custo de infra maior; time-to-response alto para relatórios |
| **Severidade** | 🟡 MEDIUM |
| **Recomendação** | Definir estratégia: (1) **Cache aside** para dados de contratos/configurações que mudam raramente; (2) **Cache invalidation** por evento (InvoiceUpdated → invalida cache); (3) **TTL policies** por tipo de dado. Usar `aiocache` ou `fastapi-cache2`. |
| **Critério de Aceite** | Endpoint de relatório com cache responde < 100ms na segunda requisição; invalidação do cache ocorre quando dados mudam |

---

### ARCH-012 — Ausência de Estratégia de Filas Celery

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-012 |
| **Componente** | `backend/app/tasks/` |
| **Problema** | Celery está na stack mas sem design de filas. Sem prioridade de tarefas, uma task de relatório pesado pode bloquear o envio de e-mails urgentes. |
| **Impacto** | SLA de processamento de documentos comprometido; notificações críticas atrasadas |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Definir filas por prioridade e tipo: `critical` (alertas, e-mails de cobrança urgente), `high` (geração de NF-e, boletos), `default` (processamento normal), `low` (relatórios, exports). Configurar workers dedicados por fila. |
| **Critério de Aceite** | Tasks em fila `critical` processadas antes de tasks em `low`; workers dedicados por fila configurados no Docker Compose |

---

### ARCH-013 — Ausência de Estratégia de Migrations

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-013 |
| **Componente** | `backend/alembic/` |
| **Problema** | Sem configuração do Alembic. Sem convenção para naming de migrations, rollback strategy ou zero-downtime migrations. |
| **Impacto** | Migrations de produção podem requerer downtime; sem rollback seguro em caso de falha |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Configurar Alembic com: autogenerate habilitado; naming convention consistente; `--sql` mode para review antes de executar em produção; convention de zero-downtime migrations (adicionar coluna nullable antes, backfill, depois tornar NOT NULL). |
| **Critério de Aceite** | `alembic upgrade head` e `alembic downgrade -1` executam sem erro; migrations revisadas por SQL antes de produção |

---

### ARCH-014 — Ausência de Estratégia de Armazenamento de Documentos

| Campo | Valor |
|-------|-------|
| **ID** | ARCH-014 |
| **Componente** | `backend/app/modules/documents/` |
| **Problema** | MinIO está na stack mas sem estratégia de organização de objetos, lifecycle policies, versionamento ou acesso seguro (presigned URLs). |
| **Impacto** | Documentos sem organização; sem controle de acesso por tenant; sem lifecycle de retenção |
| **Severidade** | 🟡 MEDIUM |
| **Recomendação** | Definir estrutura de buckets: `{tenant_id}/documents/{year}/{month}/{document_id}`. Usar presigned URLs com TTL curto (< 15 min) para downloads. Configurar lifecycle para arquivamento após 1 ano. Política de acesso por tenant no MinIO. |
| **Critério de Aceite** | URL de documento de tenant A inválida para tenant B; presigned URLs expiram no TTL configurado |

---

## 3. ANÁLISE DE CONFORMIDADE COM ARQUITETURA PROPOSTA

```
Componente                        | Proposto | Implementado | Conformidade
─────────────────────────────────────────────────────────────────────────
Modular Monolith structure        |    ✅    |      ❌      |    0%
FastAPI application factory       |    ✅    |      ❌      |    0%
SQLAlchemy 2.x models             |    ✅    |      ❌      |    0%
Alembic migrations                |    ✅    |      ❌      |    0%
PostgreSQL 16 (Docker)            |    ✅    |      ❌      |    0%
Redis (Docker)                    |    ✅    |      ❌      |    0%
MinIO (Docker)                    |    ✅    |      ❌      |    0%
Celery workers                    |    ✅    |      ❌      |    0%
React + Vite + TypeScript         |    ✅    |      ❌      |    0%
Docker Compose orchestration      |    ✅    |      ❌      |    0%
Multi-tenancy                     |    ✅    |      ❌      |    0%
Plugin/Extension system           |    ✅    |      ❌      |    0%
Repository pattern                |    ✅    |      ❌      |    0%
Event system                      |    ✅    |      ❌      |    0%
Observability (Prometheus)        |    ✅    |      ❌      |    0%
Health checks                     |    ✅    |      ❌      |    0%
API versioning                    |    ✅    |      ❌      |    0%
Security (JWT, CORS, rate limit)  |    ✅    |      ❌      |    0%
CI/CD pipelines                   |    ✅    |      ❌      |    0%
Test suite                        |    ✅    |      ❌      |    0%
─────────────────────────────────────────────────────────────────────────
CONFORMIDADE TOTAL                                              0% (0/20)
```

---

## 4. DIAGRAMA DE DEPENDÊNCIAS DOS MÓDULOS (ALVO)

```
┌─────────────────────────────────────────────────────────┐
│                      CORE LAYER                          │
│  config | database | security | events | middleware       │
└─────────────────────────────────────────────────────────┘
           ↑                 ↑
    ┌──────┴──────┐   ┌──────┴──────────────────────┐
    │             │   │                              │
┌───▼──┐  ┌──────▼─┐ ┌▼────────┐  ┌───────────┐  ┌▼──────────┐
│auth  │  │companies│ │contracts│  │ billing   │  │ documents │
│module│  │ module  │ │ module  │  │  module   │  │  module   │
└──────┘  └─────────┘ └─────────┘  └───────────┘  └──────────┘
                ↑            ↑            ↑
         ┌──────┴────────────┴────────────┴──────────┐
         │              EVENTS (internal)              │
         │  CompanyCreated | ContractActivated |       │
         │  InvoiceGenerated | PaymentReceived          │
         └─────────────────────────────────────────────┘
                              ↑
         ┌────────────────────┴────────────────────────┐
         │           EXTENSION LAYER                    │
         │  hooks | plugins | tenant-specific rules     │
         └─────────────────────────────────────────────┘
```

---

## 5. RISCOS ARQUITETURAIS IDENTIFICADOS

| Risco | Probabilidade | Impacto | Score | Mitigação |
|-------|---------------|---------|-------|-----------|
| Acoplamento entre módulos sem event system | Alta | Alto | 🔴 9 | Implementar EventBus antes de outros módulos |
| Data leak entre tenants sem RLS | Alta | Crítico | 🔴 10 | Multi-tenancy na primeira migration |
| Lock-in em MinIO sem abstração | Média | Médio | 🟡 4 | Usar boto3 com interface S3 |
| Celery blocking de tasks críticas | Média | Alto | 🟠 6 | Filas separadas por prioridade |
| Python 3.14 incompatibilidade | Baixa | Médio | 🟡 3 | Fixar Python 3.12 no pyproject.toml |
| Schema drift sem convenção de migration | Alta | Alto | 🔴 8 | Alembic autogenerate + review obrigatório |
| Extensibilidade não implementada desde o início | Alta | Crítico | 🔴 10 | Definir hook system antes de módulos de negócio |

---

## 6. ORDEM RECOMENDADA DE IMPLEMENTAÇÃO

```
FASE 0 — Fundação (Sem Funcionalidade)
  ├── Scaffolding de estrutura de diretórios
  ├── Docker Compose (todos os serviços)
  ├── pyproject.toml + uv setup
  ├── package.json + Vite setup
  ├── .env.example + config.py (BaseSettings)
  ├── .gitignore + .git init
  └── CI/CD básico (lint + typecheck)

FASE 1 — Core Infrastructure
  ├── Database setup (SQLAlchemy 2.x + Alembic)
  ├── Base models com tenant_id
  ├── Multi-tenancy middleware
  ├── Application factory (create_app + lifespan)
  ├── Health checks
  ├── Logging estruturado
  └── Security (JWT, bcrypt, CORS)

FASE 2 — Extension Framework
  ├── EventBus interno
  ├── Repository pattern base
  ├── Unit of Work pattern
  ├── Hook/Plugin registry
  └── Tenant-scoped configuration

FASE 3 — Módulos de Domínio (por prioridade)
  ├── auth module (Users, Companies)
  ├── contracts module
  ├── billing module (core)
  ├── documents module (MinIO integration)
  └── notifications module (Celery)

FASE 4 — Frontend
  ├── Auth flow (login, refresh token)
  ├── Companies management
  ├── Contracts management
  ├── Billing dashboard
  └── Documents viewer

FASE 5 — Observabilidade e Produção
  ├── Prometheus metrics
  ├── Grafana dashboards
  ├── Sentry integration
  └── Production Docker Compose
```

---
*Gerado em 2026-11-03 | EBA Technical Assessment v1.0*

