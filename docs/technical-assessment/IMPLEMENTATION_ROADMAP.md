# IMPLEMENTATION ROADMAP — Enterprise Billing Automation (EBA)

**Data:** 2026-11-03  
**Status:** Greenfield — 0% implementado  
**Versão do Documento:** 1.0.0

---

## 1. PRINCÍPIOS GUIAS

> [!IMPORTANT]
> Este roadmap segue uma sequência **deliberada e não negociável**. Cada fase cria a fundação para a próxima. Pular fases cria débito técnico e de segurança difícil de corrigir retroativamente.

1. **Security First** — Controles de segurança são implementados com o primeiro código, não depois
2. **Test-Driven** — Nenhum módulo vai para produção sem suite de testes (≥ 80% coverage)
3. **Extensibility Over Features** — Framework de extensão antes de features de negócio
4. **No Premature Optimization** — Resolver problema real antes de otimizar
5. **Documentation as Code** — Docs gerados automaticamente (OpenAPI), não escritos manualmente

---

## 2. VISÃO GERAL DAS FASES

```
FASE 0: Fundação          ████████░░░░░░░░░░░░░  ~1 semana
FASE 1: Core Backend      ██████████████░░░░░░░  ~2 semanas  
FASE 2: Ext. Framework    ████████████░░░░░░░░░  ~1 semana
FASE 3: Auth Module       ████████████████░░░░░  ~1 semana
FASE 4: Domain Modules    ██████████████████░░░  ~3-4 semanas
FASE 5: Frontend Core     ██████████████████░░░  ~2 semanas
FASE 6: Frontend Features ████████████████████░  ~2-3 semanas
FASE 7: Observabilidade   ████████████████████░  ~1 semana
FASE 8: Production Ready  ████████████████████░  ~1 semana
```

---

## 3. FASE 0 — FUNDAÇÃO E SCAFFOLDING

**Objetivo:** Repositório funcional com ambiente de desenvolvimento completo.  
**Estimativa:** 3-5 dias  
**Pré-requisito:** Nenhum  
**Critério de conclusão:** `docker compose up` → todos os serviços sobem; lint/typecheck passam

### 3.1 Tarefas

| ID | Tarefa | Prioridade | Dependência | Critério de Aceite |
|----|--------|------------|-------------|-------------------|
| F0-01 | `git init` + `.gitignore` abrangente | 🔴 P0 | — | `git status` mostra apenas arquivos rastreáveis |
| F0-02 | Estrutura de diretórios completa | 🔴 P0 | F0-01 | Todos os diretórios conforme arquitetura |
| F0-03 | `backend/pyproject.toml` com dependências | 🔴 P0 | F0-02 | `uv sync` instala sem erro |
| F0-04 | Instalar `uv` + Python 3.12 via uv | 🔴 P0 | F0-03 | `python --version` → 3.12.x no venv |
| F0-05 | `frontend/package.json` + Vite scaffold | 🔴 P0 | F0-02 | `npm run dev` inicia sem erro |
| F0-06 | `docker-compose.yml` (development) | 🔴 P0 | F0-02 | Todos os 6+ serviços sobem healthy |
| F0-07 | `.env.example` documentado | 🔴 P0 | F0-06 | Todos os campos documentados com tipo e exemplo |
| F0-08 | `backend/app/config.py` (BaseSettings) | 🔴 P0 | F0-07 | Startup falha com msg clara se var obrigatória ausente |
| F0-09 | `Makefile` com comandos do dia-a-dia | 🟠 P1 | F0-06 | `make up`, `make down`, `make test`, `make lint` funcionam |
| F0-10 | `pre-commit` configurado | 🟠 P1 | F0-04 | `pre-commit run --all-files` passa sem erro |
| F0-11 | CI básico (GitHub Actions) | 🟠 P1 | F0-10 | Lint + typecheck rodando em PR |
| F0-12 | `README.md` com setup em 5 minutos | 🟡 P2 | F0-09 | Dev novo sobe o ambiente seguindo apenas o README |

### 3.2 Serviços Docker Compose (Fase 0)

```yaml
# Serviços mínimos para desenvolvimento
services:
  db:         # postgres:16-alpine    + healthcheck
  redis:      # redis:7-alpine         + senha + healthcheck
  minio:      # minio/minio            + criar bucket inicial
  mailhog:    # mailhog/mailhog        # SMTP fake para dev
  api:        # FastAPI (build local)  + depends_on db, redis
  worker:     # Celery (build local)   + depends_on redis
  flower:     # Celery monitor         + depends_on worker
  web:        # Vite dev server        + depends_on api
```

---

## 4. FASE 1 — CORE BACKEND INFRASTRUCTURE

**Objetivo:** Base técnica sólida: banco, migrations, segurança, observabilidade básica.  
**Estimativa:** 10-14 dias  
**Pré-requisito:** Fase 0 concluída  
**Critério de conclusão:** API responde em `/health/ready`; banco configurado; JWT funcional

### 4.1 Tarefas

| ID | Tarefa | Prioridade | Gap Resolvido | Critério de Aceite |
|----|--------|------------|---------------|-------------------|
| F1-01 | Application factory (`create_app` + lifespan) | 🔴 P0 | ARCH-002 | `TestClient(create_app())` cria instância isolada |
| F1-02 | SQLAlchemy 2.x setup (async engine + session) | 🔴 P0 | GAP-009 | `async with get_session() as s:` funcional |
| F1-03 | `BaseModel` com `id`, `tenant_id`, `created_at`, `updated_at` | 🔴 P0 | SEC-004 | Todos os models herdam de BaseModel |
| F1-04 | Alembic configurado + migration inicial | 🔴 P0 | ARCH-013 | `alembic upgrade head` cria tabelas; `downgrade -1` reverte |
| F1-05 | Health check endpoints (`/health/live`, `/ready`) | 🟠 P1 | ARCH-010 | 200 quando tudo up; 503 quando dependência falha |
| F1-06 | Logging estruturado (`structlog` + JSON em prod) | 🟠 P1 | ARCH-009 | Logs com `trace_id`, `tenant_id`, `request_id` |
| F1-07 | Middleware de request ID | 🟠 P1 | ARCH-009 | Todo request tem `X-Request-ID` único |
| F1-08 | CORS middleware (por ambiente) | 🟠 P1 | SEC-008 | Origem não listada recebe 400 no preflight |
| F1-09 | Security: JWT (`PyJWT`) + Argon2 hashing | 🔴 P0 | SEC-001, SEC-002 | `create_access_token()` e `verify_token()` testados |
| F1-10 | Validação de `SECRET_KEY` no startup | 🔴 P0 | SEC-006 | Startup falha com `ValueError` se key fraca |
| F1-11 | Rate limiting (`slowapi` + Redis backend) | 🟠 P1 | SEC-007 | 6ª req em 1min retorna 429 |
| F1-12 | Custom exception handlers (padronização erros) | 🟠 P1 | — | Todos erros retornam `{error, detail, trace_id}` |
| F1-13 | Celery app configurado com filas nomeadas | 🔴 P0 | GAP-010, ARCH-012 | Worker inicia; task de teste executada com sucesso |
| F1-14 | Multi-tenancy middleware (tenant_id do JWT) | 🔴 P0 | SEC-004, ARCH-007 | Contexto de tenant injetado em toda request |
| F1-15 | Repository pattern base (`BaseRepository[T]`) | 🟠 P1 | ARCH-004 | CRUD genérico com `tenant_id` automático |
| F1-16 | Unit of Work pattern (`AsyncUnitOfWork`) | 🟠 P1 | ARCH-005 | Rollback automático em exceção dentro do UoW |
| F1-17 | Suite de testes base (`conftest.py`, fixtures, DB de teste) | 🔴 P0 | GAP-009 | `pytest` passa; DB de teste criado/destruído por sessão |

---

## 5. FASE 2 — EXTENSION FRAMEWORK

**Objetivo:** Sistema de extensibilidade antes de qualquer módulo de negócio.  
**Estimativa:** 5-7 dias  
**Pré-requisito:** Fase 1 concluída  
**Critério de conclusão:** Hook system funcional; EventBus com teste de integração entre dois módulos mock

### 5.1 Tarefas

| ID | Tarefa | Prioridade | Gap Resolvido | Critério de Aceite |
|----|--------|------------|---------------|-------------------|
| F2-01 | EventBus interno (pub/sub síncrono) | 🔴 P0 | ARCH-003 | Módulo A publica → Módulo B recebe sem importar A |
| F2-02 | Hook registry (`PRE_*`, `POST_*` hooks) | 🔴 P0 | ARCH-006 | Hook registrado executa no ponto correto do fluxo |
| F2-03 | Plugin registry (por tenant) | 🔴 P0 | ARCH-006 | Plugin do Tenant A não executa para Tenant B |
| F2-04 | Tenant configuration store | 🟠 P1 | ARCH-006 | Configurações de tenant carregadas do banco com cache |
| F2-05 | Documentação do framework de extensão | 🟠 P1 | — | Developer guide: como criar um novo plugin |

> [!NOTE]
> Esta fase é crítica para o modelo de negócio do EBA. Regras específicas de clientes são implementadas como plugins/hooks, não como modificações no core. O tempo investido aqui economiza semanas de refactoring futuro.

---

## 6. FASE 3 — MÓDULO DE AUTENTICAÇÃO

**Objetivo:** Auth completo e funcional como base para todos os outros módulos.  
**Estimativa:** 5-7 dias  
**Pré-requisito:** Fase 1 concluída  
**Critério de conclusão:** Login, refresh, logout, RBAC completos com testes

### 6.1 Tarefas

| ID | Tarefa | Prioridade | Gap Resolvido | Critério de Aceite |
|----|--------|------------|---------------|-------------------|
| F3-01 | Model `User` com roles | 🔴 P0 | SEC-003 | Migration criada; modelo testado |
| F3-02 | Model `Company` (tenant) | 🔴 P0 | ARCH-007 | Company = tenant; `tenant_id` = `company_id` |
| F3-03 | `POST /api/v1/auth/login` | 🔴 P0 | SEC-001 | Retorna access + refresh token; rate limited |
| F3-04 | `POST /api/v1/auth/refresh` | 🔴 P0 | SEC-013 | Rotation de refresh token; family tracking |
| F3-05 | `POST /api/v1/auth/logout` | 🔴 P0 | SEC-013 | Invalida family de tokens; blacklist no Redis |
| F3-06 | `GET /api/v1/auth/me` | 🟠 P1 | — | Retorna perfil do usuário autenticado |
| F3-07 | `POST /api/v1/auth/password/reset-request` | 🟠 P1 | — | E-mail com token de reset (via Celery) |
| F3-08 | `POST /api/v1/auth/password/reset` | 🟠 P1 | — | Valida token; altera senha; invalida sessões |
| F3-09 | Decorators de permissão por role | 🔴 P0 | SEC-003 | `@require_role("ADMIN")` retorna 403 para outros |
| F3-10 | Testes de segurança auth (IDOR, brute force, token forjado) | 🔴 P0 | SEC-001..004 | 15+ cenários de segurança com casos negativos |

---

## 7. FASE 4 — MÓDULOS DE DOMÍNIO

**Objetivo:** Módulos de negócio core do EBA.  
**Estimativa:** 3-4 semanas  
**Pré-requisito:** Fases 1, 2 e 3 concluídas  
**Critério de conclusão:** API completa para cada módulo com testes ≥ 80% coverage

### 7.1 Módulo: Companies (Clientes)

| ID | Endpoint/Tarefa | Critério |
|----|-----------------|----------|
| F4-C01 | `POST /companies` — Criar empresa cliente | CNPJ validado; tenant criado automaticamente |
| F4-C02 | `GET /companies` — Listar (paginado) | Filtragem por tenant; paginação cursor-based |
| F4-C03 | `GET /companies/{id}` — Detalhes | 404 para IDs de outro tenant |
| F4-C04 | `PATCH /companies/{id}` — Atualizar | Audit log criado |
| F4-C05 | `DELETE /companies/{id}` — Desativar (soft delete) | Dados preservados; acesso bloqueado |

### 7.2 Módulo: Contracts

| ID | Endpoint/Tarefa | Critério |
|----|-----------------|----------|
| F4-K01 | `POST /contracts` — Criar contrato | Validação de datas, valores, tipo de recorrência |
| F4-K02 | `GET /contracts` — Listar | Filtros por status, empresa, período |
| F4-K03 | `PATCH /contracts/{id}` — Atualizar | Evento `ContractUpdated` publicado |
| F4-K04 | `POST /contracts/{id}/activate` | Evento `ContractActivated`; billing schedule criado |
| F4-K05 | `POST /contracts/{id}/cancel` | Cancela cobranças futuras |
| F4-K06 | Recorrência automática (Celery Beat) | Task cria invoices automaticamente |

### 7.3 Módulo: Billing (Core)

| ID | Endpoint/Tarefa | Critério |
|----|-----------------|----------|
| F4-B01 | `POST /invoices` — Criar fatura manual | Validações de valor, empresa, vencimento |
| F4-B02 | `GET /invoices` — Listar (paginado) | Filtros por status, período, empresa |
| F4-B03 | `GET /invoices/{id}` — Detalhes | PDF gerado sob demanda |
| F4-B04 | `POST /invoices/{id}/send` — Enviar por e-mail | Task Celery; retry automático |
| F4-B05 | `POST /invoices/{id}/mark-paid` — Marcar como pago | Audit log; evento `PaymentReceived` |
| F4-B06 | Geração de PDF de fatura | Assíncrono via Celery; armazenado no MinIO |
| F4-B07 | Geração automática de faturas (Celery Beat) | Faturas geradas antes do vencimento configurável |

### 7.4 Módulo: Documents

| ID | Endpoint/Tarefa | Critério |
|----|-----------------|----------|
| F4-D01 | `POST /documents/upload` — Upload de arquivo | Validação de tipo; antivírus scan (ClamAV) |
| F4-D02 | `GET /documents/{id}/download` — Download | Presigned URL com TTL 15min; validação de tenant |
| F4-D03 | `GET /documents` — Listar documentos | Filtros por tipo, contrato, empresa |
| F4-D04 | `DELETE /documents/{id}` | Soft delete; arquivo preservado por retenção |

### 7.5 Módulo: Notifications

| ID | Endpoint/Tarefa | Critério |
|----|-----------------|----------|
| F4-N01 | Task: envio de e-mail (Celery) | Retry com backoff exponencial; 3 tentativas |
| F4-N02 | Template de e-mail (Jinja2) | 5 templates: welcome, invoice, overdue, payment, reset |
| F4-N03 | `GET /notifications` — Listar notificações | In-app notifications |
| F4-N04 | Webhook outbound | Notificação para sistemas externos do cliente |

### 7.6 Módulo: Audit

| ID | Endpoint/Tarefa | Critério |
|----|-----------------|----------|
| F4-A01 | Model `AuditLog` (imutável, append-only) | Sem UPDATE/DELETE; timestamps imutáveis |
| F4-A02 | Decorator `@auditable` para endpoints | Auto-registra ação ao decorar endpoint |
| F4-A03 | `GET /audit-logs` — Listar (admin only) | Filtros por entidade, usuário, período |
| F4-A04 | Export de audit log (CSV/XLSX) | Para compliance fiscal |

---

## 8. FASE 5 — FRONTEND CORE

**Objetivo:** Frontend funcional integrado com API.  
**Estimativa:** 10-14 dias  
**Pré-requisito:** Fase 3 concluída (auth API disponível)

| ID | Tarefa | Critério |
|----|--------|----------|
| F5-01 | Setup Vite + React 19 + TypeScript strict | `npm run build` sem erros de tipo |
| F5-02 | API client tipado (axios + interceptors) | Refresh token automático; 401 → redirect login |
| F5-03 | Auth store (zustand) | Token armazenado em memória (não localStorage) |
| F5-04 | Route guards | Rota protegida redireciona para login se não autenticado |
| F5-05 | Tela de Login | Validação zod; rate limit feedback; "Lembrar-me" |
| F5-06 | Layout principal (sidebar, header, breadcrumb) | Responsivo (mobile-first) |
| F5-07 | Sistema de toast notifications | Sucesso, erro, warning padronizados |
| F5-08 | Componentes base (Table, Form, Modal, Button) | Acessíveis (WCAG 2.1 AA) |
| F5-09 | Dashboard principal (KPIs) | Faturas em aberto, vencidas, pagas; gráfico mensal |
| F5-10 | Error boundary global | Página de erro amigável; não expõe stack trace |

---

## 9. FASE 6 — FRONTEND FEATURES

**Objetivo:** Todas as telas do produto.  
**Estimativa:** 2-3 semanas  
**Pré-requisito:** Fase 4 e Fase 5 concluídas

| Módulo | Telas | Critério |
|--------|-------|----------|
| Empresas | CRUD completo + busca | Filtros, paginação, export |
| Contratos | CRUD + timeline de status | Calendário de vencimentos |
| Faturamento | Lista de invoices + detalhes + PDF viewer | Bulk actions (enviar, marcar pagas) |
| Documentos | Upload drag-and-drop + galeria | Preview inline de PDFs |
| Relatórios | 5+ relatórios padrão + export | Charts interativos |
| Configurações | Empresa, usuários, integrações | RBAC por seção |

---

## 10. FASE 7 — OBSERVABILIDADE

**Objetivo:** Monitoramento completo em produção.  
**Estimativa:** 3-5 dias  
**Pré-requisito:** Fase 4 concluída

| ID | Tarefa | Critério |
|----|--------|----------|
| F7-01 | Prometheus metrics (FastAPI instrumentator) | `/metrics` com latência, erros, throughput |
| F7-02 | Grafana dashboards (4 dashboards base) | API, DB, Celery, Business |
| F7-03 | Alertas (Alertmanager) | Alert se error rate > 1%; latência p99 > 2s |
| F7-04 | Sentry integration | Erros com contexto de tenant e user |
| F7-05 | OpenTelemetry tracing | Traces de request end-to-end (API → DB → Celery) |

---

## 11. FASE 8 — PRODUCTION READINESS

**Objetivo:** Deploy seguro em produção.  
**Estimativa:** 3-5 dias  
**Pré-requisito:** Fases 1-7 concluídas + Penetration testing

| ID | Tarefa | Critério |
|----|--------|----------|
| F8-01 | `docker-compose.prod.yml` + Nginx TLS | HTTPS com A+ no SSL Labs |
| F8-02 | CD pipeline (GitHub Actions) | Deploy automático em merge para `main` |
| F8-03 | Database backup automático | Backup diário; restore testado |
| F8-04 | Security hardening final | Trivy scan limpo; `pip-audit` limpo |
| F8-05 | Load testing (k6) | 1000 req/s sustentado por 5min sem degradação |
| F8-06 | Documentação de operações (runbook) | Playbooks para incidentes comuns |

---

## 12. SUMÁRIO DE PROBLEMAS VS FASES

| Problema | Severidade | Fase de Resolução |
|----------|------------|-------------------|
| GAP-001 (repositório vazio) | 🔴 CRITICAL | Fase 0 |
| GAP-002 (sem git) | 🔴 CRITICAL | Fase 0 |
| GAP-006 (sem pyproject.toml) | 🔴 CRITICAL | Fase 0 |
| GAP-007 (sem frontend) | 🔴 CRITICAL | Fase 0 + Fase 5 |
| GAP-008 (sem Docker Compose) | 🔴 CRITICAL | Fase 0 |
| GAP-012 (sem .env) | 🔴 CRITICAL | Fase 0 |
| GAP-003 (Python 3.14) | 🟡 MEDIUM | Fase 0 |
| GAP-004 (sem uv) | 🟠 HIGH | Fase 0 |
| GAP-005 (Docker daemon parado) | 🟠 HIGH | Fase 0 |
| GAP-013 (sem CI) | 🟠 HIGH | Fase 0 |
| GAP-014 (sem README) | 🟡 MEDIUM | Fase 0 |
| GAP-009 (sem models/migrations) | 🔴 CRITICAL | Fase 1 |
| GAP-010 (sem Celery) | 🔴 CRITICAL | Fase 1 |
| GAP-011 (sem segurança) | 🔴 CRITICAL | Fase 1 + Fase 3 |
| ARCH-001 (sem módulos) | 🔴 CRITICAL | Fase 4 |
| ARCH-002 (sem app factory) | 🔴 CRITICAL | Fase 1 |
| ARCH-003 (sem events) | 🟠 HIGH | Fase 2 |
| ARCH-004 (sem repository) | 🟠 HIGH | Fase 1 |
| ARCH-005 (sem UoW) | 🟠 HIGH | Fase 1 |
| ARCH-006 (sem extensibilidade) | 🔴 CRITICAL | Fase 2 |
| ARCH-007 (sem multi-tenancy) | 🔴 CRITICAL | Fase 1 |
| ARCH-008 (sem API versioning) | 🟠 HIGH | Fase 1 |
| ARCH-009 (sem observabilidade) | 🟠 HIGH | Fase 1 (básico) + Fase 7 |
| ARCH-010 (sem health checks) | 🟠 HIGH | Fase 1 |
| ARCH-011 (sem cache strategy) | 🟡 MEDIUM | Fase 4 |
| ARCH-012 (sem filas Celery) | 🟠 HIGH | Fase 1 |
| ARCH-013 (sem migrations) | 🟠 HIGH | Fase 1 |
| ARCH-014 (sem doc strategy) | 🟡 MEDIUM | Fase 4 |
| SEC-001..018 (todos os SECs) | 🔴 CRITICAL/HIGH | Fases 0-3 |

---

## 13. MÉTRICAS DE QUALIDADE (ALVOS)

| Métrica | Alvo Mínimo | Alvo Ideal |
|---------|-------------|------------|
| Test Coverage (backend) | 80% | 90% |
| Test Coverage (frontend) | 70% | 85% |
| Mypy strict mode | 0 erros | 0 erros |
| Ruff linting | 0 warnings | 0 warnings |
| Bandit security | 0 HIGH/CRITICAL | 0 em todos |
| API p99 latency | < 500ms | < 200ms |
| API error rate | < 0.1% | < 0.01% |
| Celery task success rate | > 99% | > 99.9% |
| Docker image size (API) | < 500MB | < 200MB |
| Time to first byte (frontend) | < 1s | < 500ms |

---

## 14. PRÓXIMOS PASSOS IMEDIATOS

Ações a executar **após aprovação** deste roadmap:

1. **Aprovação do roadmap** ← *Aguardando aqui*
2. Instalar `uv` e Python 3.12 no ambiente WSL
3. Executar Prompt 02: Scaffolding da estrutura de diretórios
4. Executar Prompt 03: Docker Compose e infraestrutura
5. Executar Prompt 04: Backend Core (config, database, security)
6. Executar Prompt 05: Extension Framework
7. Executar Prompt 06: Auth Module
8. Executar Prompts 07-N: Módulos de domínio (por ordem de dependência)

---
*Gerado em 2026-11-03 | EBA Technical Assessment v1.0*

