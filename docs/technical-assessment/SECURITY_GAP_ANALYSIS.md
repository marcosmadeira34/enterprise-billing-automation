# SECURITY GAP ANALYSIS — Enterprise Billing Automation (EBA)

**Data da Auditoria:** 2026-11-03  
**Metodologia:** OWASP Top 10 (2021), OWASP API Security Top 10 (2023), CWE Top 25  
**Status:** 🔴 Nenhuma implementação de segurança existe — Greenfield  
**Versão do Documento:** 1.0.0

---

## 1. SUMÁRIO EXECUTIVO

O projeto EBA está em estado greenfield. **Nenhum controle de segurança foi implementado.** Esta análise identifica os riscos de segurança que **devem** ser endereçados durante a implementação, antes de qualquer deploy em ambiente acessível externamente.

> [!CAUTION]
> EBA é uma plataforma de faturamento corporativo. Processa dados financeiros, contratos e documentos sensíveis de múltiplas empresas. Falhas de segurança têm impacto direto: vazamento de dados de clientes (LGPD), fraude financeira, perda de reputação irreparável.

---

## 2. ANÁLISE POR CAMADA

### 2.1 AUTENTICAÇÃO E AUTORIZAÇÃO

#### SEC-001 — Ausência de Sistema de Autenticação

| Campo | Valor |
|-------|-------|
| **ID** | SEC-001 |
| **CWE** | CWE-306: Missing Authentication for Critical Function |
| **OWASP** | A07:2021 – Identification and Authentication Failures |
| **Arquivo** | `backend/app/core/security.py` (inexistente) |
| **Problema** | Nenhum mecanismo de autenticação implementado. Sem JWT, sem session management, sem password hashing. |
| **Impacto** | Todos os endpoints acessíveis sem autenticação |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | Implementar autenticação JWT com: (1) Access Token (curta duração: 15 min); (2) Refresh Token (longa duração: 7 dias, armazenado em banco como hash); (3) `HttpOnly` cookie para refresh token; (4) PKCE para fluxo de autorização futuro |
| **Critério de Aceite** | Endpoint sem token retorna 401; token expirado retorna 401 com mensagem específica; token inválido retorna 401 |

---

#### SEC-002 — Ausência de Hashing de Senhas

| Campo | Valor |
|-------|-------|
| **ID** | SEC-002 |
| **CWE** | CWE-916: Use of Password Hash With Insufficient Computational Effort |
| **OWASP** | A02:2021 – Cryptographic Failures |
| **Arquivo** | `backend/app/core/security.py` (inexistente) |
| **Problema** | Sem implementação de hashing de senhas. Risco de armazenar senhas em texto plano ou com algoritmo fraco. |
| **Impacto** | Em caso de breach do banco, todas as senhas expostas |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | Usar `argon2-cffi` (Argon2id — recomendado pelo OWASP para novas implementações) ou `bcrypt` com work factor ≥ 12. **Nunca usar MD5, SHA1, SHA256 sem salt para senhas.** Configurar work factor adequado ao hardware (mínimo 250ms por operação). |
| **Critério de Aceite** | `verify_password("plain", hashed)` retorna True apenas para hash correto; hash único por senha (salt automático); tempo de hashing > 100ms |

---

#### SEC-003 — Ausência de Autorização por Roles (RBAC)

| Campo | Valor |
|-------|-------|
| **ID** | SEC-003 |
| **CWE** | CWE-285: Improper Authorization |
| **OWASP** | A01:2021 – Broken Access Control |
| **Arquivo** | `backend/app/core/permissions.py` (inexistente) |
| **Problema** | Sem implementação de RBAC. Sem definição de roles e permissões. Todos os usuários teriam o mesmo nível de acesso. |
| **Impacto** | Usuário comum poderia acessar dados de outros usuários/clientes; ações administrativas sem restrição |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | Implementar RBAC com roles mínimas: `SUPERADMIN` (plataforma), `ADMIN` (empresa), `MANAGER` (departamental), `OPERATOR` (operacional), `VIEWER` (somente leitura). Cada endpoint especifica roles permitidas via decorator. |
| **Critério de Aceite** | Usuário com role VIEWER recebe 403 em endpoints de escrita; RBAC testado em 100% dos endpoints protegidos |

---

#### SEC-004 — Ausência de Isolamento de Tenants (IDOR)

| Campo | Valor |
|-------|-------|
| **ID** | SEC-004 |
| **CWE** | CWE-639: Authorization Bypass Through User-Controlled Key |
| **OWASP** | A01:2021 – Broken Access Control, API3:2023 – Broken Object Property Level Authorization |
| **Arquivo** | `backend/app/models/base.py` (inexistente) |
| **Problema** | Sem `tenant_id` nos models. Sem filtragem automática de queries por tenant. Um usuário do Tenant A pode potencialmente acessar dados do Tenant B manipulando IDs na URL. |
| **Impacto** | 🚨 LGPD Art. 46 — Vazamento de dados pessoais entre empresas clientes; potencial fraude financeira |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | (1) `tenant_id` UUID em todos os models de dados; (2) Row-Level Security (RLS) no PostgreSQL como segunda barreira; (3) Middleware que injeta `tenant_id` do JWT em todas as queries; (4) Testes de segurança específicos para IDOR em cada módulo |
| **Critério de Aceite** | `GET /api/v1/invoices/{id}` com tenant A não retorna invoices de tenant B mesmo que o ID exista; RLS no PostgreSQL bloqueia acesso direto ao banco sem o tenant correto |

---

### 2.2 CONFIGURAÇÃO E SECRETS

#### SEC-005 — Ausência de Gestão de Secrets

| Campo | Valor |
|-------|-------|
| **ID** | SEC-005 |
| **CWE** | CWE-798: Use of Hard-coded Credentials |
| **OWASP** | A05:2021 – Security Misconfiguration |
| **Arquivo** | `.env`, `backend/app/config.py` (inexistentes) |
| **Problema** | Sem gestão de secrets. Risco alto de hardcode de credenciais (database URL, JWT secret, MinIO keys) no código. |
| **Impacto** | Credenciais expostas no repositório Git; comprometimento total do ambiente |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | (1) Todos os secrets em variáveis de ambiente; (2) Validação na startup (falha com mensagem clara se SECRET_KEY não definido); (3) SECRET_KEY mínimo de 256 bits; (4) `.env` sempre no `.gitignore`; (5) `.env.example` com valores placeholder. Em produção: usar Docker secrets ou Vault (HashiCorp Vault). |
| **Critério de Aceite** | `git grep -r "password\|secret\|key" --include="*.py"` não retorna valores hardcoded; startup falha se `SECRET_KEY` não definido ou muito curto |

---

#### SEC-006 — Ausência de Validação de `SECRET_KEY`

| Campo | Valor |
|-------|-------|
| **ID** | SEC-006 |
| **CWE** | CWE-330: Use of Insufficiently Random Values |
| **OWASP** | A02:2021 – Cryptographic Failures |
| **Arquivo** | `backend/app/config.py` (inexistente) |
| **Problema** | Sem validação de entropia do `SECRET_KEY`. Desenvolvedores podem usar secrets fracos como `"secret"` ou `"changeme"` em produção. |
| **Impacto** | JWT tokens forjáveis se secret for previsível |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | Implementar validação no `BaseSettings`: tamanho mínimo de 32 bytes, negar valores conhecidos (`secret`, `changeme`, `password`). Em produção, usar `secrets.token_hex(32)` para gerar automaticamente. |
| **Critério de Aceite** | Startup falha com `ValueError` descritivo se `SECRET_KEY` < 32 chars ou igual a valor padrão |

---

### 2.3 SEGURANÇA DA API

#### SEC-007 — Ausência de Rate Limiting

| Campo | Valor |
|-------|-------|
| **ID** | SEC-007 |
| **CWE** | CWE-770: Allocation of Resources Without Limits or Throttling |
| **OWASP** | API4:2023 – Unrestricted Resource Consumption |
| **Arquivo** | `backend/app/core/middleware.py` (inexistente) |
| **Problema** | Sem rate limiting em nenhum endpoint. Endpoints de autenticação sem throttling são vulneráveis a brute force. |
| **Impacto** | Ataques de brute force em login; DoS por requisições excessivas; aumento de custo de infra |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | Implementar rate limiting com `slowapi`: (1) `/api/v1/auth/login`: 5 req/min por IP; (2) `/api/v1/auth/register`: 3 req/min por IP; (3) Endpoints gerais: 100 req/min por usuário autenticado; (4) Endpoints de export/relatório: 10 req/min. Usar Redis como backend do rate limiter. |
| **Critério de Aceite** | 6ª tentativa de login em 1 minuto retorna 429; header `Retry-After` presente na resposta |

---

#### SEC-008 — Ausência de Configuração CORS

| Campo | Valor |
|-------|-------|
| **ID** | SEC-008 |
| **CWE** | CWE-942: Permissive Cross-domain Policy with Untrusted Domains |
| **OWASP** | A05:2021 – Security Misconfiguration |
| **Arquivo** | `backend/app/main.py` (inexistente) |
| **Problema** | Sem CORS configurado. Em desenvolvimento, tentação de usar `allow_origins=["*"]` e esquecer de restringir em produção. |
| **Impacto** | CSRF attacks; requisições de origens não autorizadas aceitas |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Configurar CORS via variável de ambiente `ALLOWED_ORIGINS`. Em dev: `["http://localhost:3000"]`. Em prod: domínios específicos. **Nunca usar `["*"]` com `allow_credentials=True`** — isso é bloqueado por browsers modernos mas é erro de configuração crítico. |
| **Critério de Aceite** | Requisição de origem não listada recebe resposta sem headers CORS; `OPTIONS` preflight de origem válida retorna 204 com headers corretos |

---

#### SEC-009 — Ausência de Validação de Input (Injection Prevention)

| Campo | Valor |
|-------|-------|
| **ID** | SEC-009 |
| **CWE** | CWE-89: SQL Injection, CWE-79: XSS |
| **OWASP** | A03:2021 – Injection |
| **Arquivo** | `backend/app/modules/*/schemas.py` (inexistentes) |
| **Problema** | Sem schemas Pydantic para validação de input. Sem sanitização de strings. Sem proteção contra SQL injection ou XSS. |
| **Impacto** | SQL injection via queries construídas com string concatenação; XSS via dados armazenados e renderizados sem escape |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | (1) Todos os inputs validados via Pydantic schemas (nunca aceitar `dict` raw); (2) SQLAlchemy ORM com queries parametrizadas (nunca string format em queries); (3) Sanitização de HTML em campos de texto livre; (4) Validação de regex em campos críticos (CNPJ, CPF, e-mail) |
| **Critério de Aceite** | Payload `'; DROP TABLE users; --` em qualquer campo retorna erro de validação 422; SQLAlchemy usa `bindparams` em todos os casos |

---

#### SEC-010 — Ausência de Security Headers HTTP

| Campo | Valor |
|-------|-------|
| **ID** | SEC-010 |
| **CWE** | CWE-116: Improper Encoding or Escaping of Output |
| **OWASP** | A05:2021 – Security Misconfiguration |
| **Arquivo** | `infra/nginx/nginx.conf` (inexistente) |
| **Problema** | Sem security headers HTTP: sem `Content-Security-Policy`, sem `X-Frame-Options`, sem `X-Content-Type-Options`, sem `Strict-Transport-Security`. |
| **Impacto** | Clickjacking; MIME sniffing attacks; man-in-the-middle sem HSTS |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Configurar no Nginx: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block`, `Strict-Transport-Security: max-age=31536000; includeSubDomains`, `Content-Security-Policy: default-src 'self'`, `Referrer-Policy: strict-origin-when-cross-origin` |
| **Critério de Aceite** | `curl -I https://eba.example.com` retorna todos os headers de segurança; score A+ no securityheaders.com |

---

### 2.4 DADOS E CRIPTOGRAFIA

#### SEC-011 — Ausência de Criptografia de Dados Sensíveis em Repouso

| Campo | Valor |
|-------|-------|
| **ID** | SEC-011 |
| **CWE** | CWE-311: Missing Encryption of Sensitive Data |
| **OWASP** | A02:2021 – Cryptographic Failures |
| **Arquivo** | `backend/app/models/` (inexistente) |
| **Problema** | Dados financeiros e pessoais sensíveis (CNPJ, dados bancários, valores de contratos) armazenados sem criptografia em colunas do banco. |
| **Impacto** | Em caso de breach do banco, dados financeiros expostos em texto claro; violação LGPD Art. 46 |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Implementar colunas criptografadas para dados altamente sensíveis usando `sqlalchemy-utils` `EncryptedType` com AES-256. Criptografia em nível de aplicação (não apenas disk encryption). Considerar PostgreSQL `pgcrypto` para colunas específicas. |
| **Critério de Aceite** | Dump do banco não expõe dados bancários em texto claro; apenas campos estritamente necessários são criptografados (não over-engineering) |

---

#### SEC-012 — Ausência de TLS/HTTPS em Produção

| Campo | Valor |
|-------|-------|
| **ID** | SEC-012 |
| **CWE** | CWE-319: Cleartext Transmission of Sensitive Information |
| **OWASP** | A02:2021 – Cryptographic Failures |
| **Arquivo** | `infra/nginx/nginx.conf`, `infra/docker-compose.prod.yml` (inexistentes) |
| **Problema** | Sem configuração de TLS no Nginx. Dados financeiros transmitidos em cleartext. |
| **Impacto** | Man-in-the-middle attacks; intercepção de dados financeiros; violação LGPD |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | Configurar Nginx com TLS 1.2+. Em produção: Let's Encrypt via Certbot ou certificado corporativo. Em dev: certificado auto-assinado via mkcert. Redirecionar HTTP → HTTPS. Configurar HSTS. |
| **Critério de Aceite** | Toda comunicação em HTTPS; HTTP redireciona para HTTPS; TLS 1.0 e 1.1 desabilitados |

---

#### SEC-013 — Ausência de Proteção de Tokens de Refresh

| Campo | Valor |
|-------|-------|
| **ID** | SEC-013 |
| **CWE** | CWE-613: Insufficient Session Expiration |
| **OWASP** | A07:2021 – Identification and Authentication Failures |
| **Arquivo** | `backend/app/modules/auth/` (inexistente) |
| **Problema** | Refresh tokens (longa duração) sem estratégia de armazenamento seguro, rotação, e invalidação. |
| **Impacto** | Refresh token roubado permite acesso indefinido mesmo após logout |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | (1) Refresh token em `HttpOnly; Secure; SameSite=Strict` cookie; (2) Hash do refresh token armazenado no banco (nunca o token em si); (3) Token rotation — cada uso emite novo refresh token; (4) Token family tracking para detectar reutilização (possível roubo); (5) Logout invalida token family inteiro. |
| **Critério de Aceite** | Refresh token não acessível via JavaScript; reutilização de refresh token antigo invalida todos os tokens da sessão |

---

### 2.5 LGPD E COMPLIANCE

#### SEC-014 — Ausência de Controles LGPD

| Campo | Valor |
|-------|-------|
| **ID** | SEC-014 |
| **Referência** | Lei 13.709/2018 (LGPD) — Art. 6, 15, 18, 37, 46, 48 |
| **Arquivo** | Múltiplos módulos (inexistentes) |
| **Problema** | Nenhum controle de compliance com LGPD implementado. EBA processa dados pessoais de funcionários e dados empresariais. |
| **Impacto** | Multas de até 2% do faturamento (max R\$ 50M por infração); suspensão de atividades; dano reputacional |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | Implementar desde o início: (1) **Data minimization** — coletar apenas dados necessários; (2) **Audit log** de acesso a dados sensíveis; (3) **Right to deletion** — mecanismo de anonimização/exclusão de dados do titular; (4) **Data retention policies** — exclusão automática após período de retenção; (5) **Privacy by design** — dados pessoais identificados e documentados no schema |
| **Critério de Aceite** | Audit log registra todo acesso a dados pessoais; `DELETE /api/v1/gdpr/my-data` anonymiza dados do usuário; retenção automática configurável por tipo de dado |

---

#### SEC-015 — Ausência de Audit Log

| Campo | Valor |
|-------|-------|
| **ID** | SEC-015 |
| **CWE** | CWE-778: Insufficient Logging |
| **OWASP** | A09:2021 – Security Logging and Monitoring Failures |
| **Arquivo** | `backend/app/modules/audit/` (inexistente) |
| **Problema** | Sem audit log de ações sensíveis. Em plataforma financeira, toda ação que afeta dados financeiros deve ser rastreável. |
| **Impacto** | Impossibilidade de detectar fraudes; sem evidências para investigação de incidentes; violação de requisitos de auditoria fiscal |
| **Severidade** | 🔴 CRITICAL |
| **Recomendação** | Módulo de audit log com: entidade afetada, ID do registro, ação (CREATE/UPDATE/DELETE), valor anterior, valor novo, usuário, tenant, timestamp, IP. Imutável (append-only). Retenção mínima de 5 anos para dados fiscais. |
| **Critério de Aceite** | Toda alteração em Invoice, Contract, Payment gera registro no audit log; audit log não permite UPDATE ou DELETE; queries de auditoria disponíveis para administradores |

---

### 2.6 INFRAESTRUTURA E CONFIGURAÇÃO

#### SEC-016 — Credenciais Padrão no Docker Compose

| Campo | Valor |
|-------|-------|
| **ID** | SEC-016 |
| **CWE** | CWE-1188: Initialization of a Resource with an Insecure Default |
| **OWASP** | A05:2021 – Security Misconfiguration |
| **Arquivo** | `docker-compose.yml` (inexistente) |
| **Problema** | Risco de usar credenciais padrão no Docker Compose de desenvolvimento (`postgres:postgres`, `redis:` sem senha). Esses arquivos podem ser deployados acidentalmente em produção. |
| **Impacto** | Banco de dados de produção acessível com credenciais triviais |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | (1) Credenciais via variáveis de ambiente (nunca hardcoded no compose); (2) `docker-compose.yml` (dev) e `docker-compose.prod.yml` (prod) separados; (3) Redis com senha obrigatória mesmo em dev; (4) MinIO com credenciais não-padrão |
| **Critério de Aceite** | `docker-compose.yml` não contém nenhuma senha hardcoded; credenciais de prod nunca coincidem com dev |

---

#### SEC-017 — Ausência de Scanning de Vulnerabilidades nas Dependências

| Campo | Valor |
|-------|-------|
| **ID** | SEC-017 |
| **CWE** | CWE-1104: Use of Unmaintained Third Party Components |
| **OWASP** | A06:2021 – Vulnerable and Outdated Components |
| **Arquivo** | `.github/workflows/ci.yml` (inexistente) |
| **Problema** | Sem processo automatizado de verificação de CVEs nas dependências Python e Node.js. |
| **Impacto** | Dependências com vulnerabilidades conhecidas chegam a produção sem detecção |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | Integrar no CI: (1) `pip-audit` para dependências Python; (2) `npm audit` para dependências Node; (3) Trivy para imagens Docker; (4) Dependabot para PRs automáticos de atualização. Falhar CI em vulnerabilidades CRITICAL ou HIGH. |
| **Critério de Aceite** | CI falha se CVE CRITICAL detectado; PR automático criado para dependências com CVE dentro de 24h |

---

#### SEC-018 — MinIO Exposto Diretamente (Sem Presigned URLs)

| Campo | Valor |
|-------|-------|
| **ID** | SEC-018 |
| **CWE** | CWE-284: Improper Access Control |
| **OWASP** | API1:2023 – Broken Object Level Authorization |
| **Arquivo** | `backend/app/modules/documents/` (inexistente) |
| **Problema** | Sem estratégia de acesso controlado ao MinIO. Se MinIO exposto publicamente ou com ACLs abertas, documentos de qualquer tenant acessíveis. |
| **Impacto** | Documentos financeiros e contratos de clientes expostos publicamente |
| **Severidade** | 🟠 HIGH |
| **Recomendação** | (1) MinIO não exposto externamente (apenas rede interna Docker); (2) Acesso via API (backend gera presigned URL com TTL de 15 min); (3) Bucket por tenant com policy de acesso; (4) Nunca retornar URL direta do MinIO ao frontend |
| **Critério de Aceite** | MinIO inacessível externamente; download de documento retorna presigned URL com expiração; URL de outro tenant não funciona |

---

## 3. ANÁLISE OWASP TOP 10 (2021)

| OWASP | Descrição | Status EBA | SECs Relacionados |
|-------|-----------|------------|-------------------|
| A01 | Broken Access Control | 🔴 NÃO IMPLEMENTADO | SEC-003, SEC-004 |
| A02 | Cryptographic Failures | 🔴 NÃO IMPLEMENTADO | SEC-002, SEC-006, SEC-011, SEC-012 |
| A03 | Injection | 🔴 NÃO IMPLEMENTADO | SEC-009 |
| A04 | Insecure Design | 🔴 NÃO IMPLEMENTADO | SEC-004, SEC-014 |
| A05 | Security Misconfiguration | 🔴 NÃO IMPLEMENTADO | SEC-005, SEC-008, SEC-010, SEC-016 |
| A06 | Vulnerable Components | 🔴 NÃO IMPLEMENTADO | SEC-017 |
| A07 | Auth & Session Failures | 🔴 NÃO IMPLEMENTADO | SEC-001, SEC-002, SEC-013 |
| A08 | Software & Data Integrity | 🔴 NÃO IMPLEMENTADO | — |
| A09 | Logging & Monitoring | 🔴 NÃO IMPLEMENTADO | SEC-015 |
| A10 | SSRF | 🟡 Risco Médio | — |

**Cobertura OWASP Top 10: 0% implementado**

---

## 4. OWASP API SECURITY TOP 10 (2023)

| API | Descrição | Status EBA | SECs Relacionados |
|-----|-----------|------------|-------------------|
| API1 | Broken Object Level Auth | 🔴 NÃO IMPLEMENTADO | SEC-004, SEC-018 |
| API2 | Broken Authentication | 🔴 NÃO IMPLEMENTADO | SEC-001, SEC-013 |
| API3 | Broken Object Property Level Auth | 🔴 NÃO IMPLEMENTADO | SEC-003 |
| API4 | Unrestricted Resource Consumption | 🔴 NÃO IMPLEMENTADO | SEC-007 |
| API5 | Broken Function Level Auth | 🔴 NÃO IMPLEMENTADO | SEC-003 |
| API6 | Unrestricted Access to Sensitive Flows | 🔴 NÃO IMPLEMENTADO | SEC-007 |
| API7 | Server Side Request Forgery | 🟡 Risco Médio | — |
| API8 | Security Misconfiguration | 🔴 NÃO IMPLEMENTADO | SEC-005, SEC-016 |
| API9 | Improper Inventory Management | 🔴 NÃO IMPLEMENTADO | SEC-010 |
| API10 | Unsafe Consumption of APIs | 🔴 NÃO IMPLEMENTADO | — |

---

## 5. SUMÁRIO POR SEVERIDADE

| Severidade | Quantidade | IDs |
|------------|------------|-----|
| 🔴 CRITICAL | 10 | SEC-001, SEC-002, SEC-003, SEC-004, SEC-005, SEC-006, SEC-007, SEC-009, SEC-012, SEC-014, SEC-015 |
| 🟠 HIGH | 7 | SEC-008, SEC-010, SEC-011, SEC-013, SEC-016, SEC-017, SEC-018 |
| 🟡 MEDIUM | 0 | — |
| **Total** | **17** | |

---

## 6. ROADMAP DE SEGURANÇA

### Fase 0 — Antes de qualquer código (Pré-requisitos)
- [ ] `.gitignore` com `.env` e secrets
- [ ] `.env.example` documentado
- [ ] Validação de `SECRET_KEY` no startup
- [ ] `pip-audit` e `npm audit` no CI

### Fase 1 — Core Security (com o primeiro módulo)
- [ ] JWT authentication (access + refresh tokens)
- [ ] Password hashing com Argon2id
- [ ] RBAC básico (roles no JWT)
- [ ] Multi-tenancy com `tenant_id`
- [ ] Rate limiting no login endpoint
- [ ] CORS configurado por ambiente

### Fase 2 — Data Security
- [ ] Audit log module
- [ ] Criptografia de colunas sensíveis
- [ ] Presigned URLs para MinIO
- [ ] TLS configurado no Nginx

### Fase 3 — Hardening e Compliance
- [ ] Security headers completos
- [ ] LGPD controls (data deletion, retention)
- [ ] Penetration testing básico
- [ ] Dependabot configurado

---
*Gerado em 2026-11-03 | EBA Technical Assessment v1.0*

