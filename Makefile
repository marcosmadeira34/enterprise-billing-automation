# =============================================================================
# EBA — Makefile
# =============================================================================
# Uso: make <target>
# Exemplo: make up | make test | make lint
# =============================================================================

.PHONY: help up down restart logs shell test lint format typecheck audit \
        migrate migrate-new migrate-rollback seed db-reset install \
        worker-logs api-logs clean

# Cores
RESET  := \033[0m
BOLD   := \033[1m
GREEN  := \033[32m
YELLOW := \033[33m
BLUE   := \033[34m
RED    := \033[31m

##@ Ajuda
help: ## Exibe esta mensagem de ajuda
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(BOLD)EBA — Enterprise Billing Automation$(RESET)\n\nUso:\n  make $(BLUE)<target>$(RESET)\n\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(BLUE)%-20s$(RESET) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BOLD)%s$(RESET)\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Desenvolvimento
up: ## Sobe todos os serviços em background
	@echo "$(GREEN)Iniciando EBA...$(RESET)"
	docker compose up -d
	@echo "$(GREEN)✓ Serviços iniciados$(RESET)"
	@echo "  API:    http://localhost:8000"
	@echo "  Docs:   http://localhost:8000/docs"
	@echo "  Web:    http://localhost:5173"
	@echo "  Flower: http://localhost:5555"
	@echo "  MinIO:  http://localhost:9001"
	@echo "  Mail:   http://localhost:8025"

down: ## Para todos os serviços
	@echo "$(YELLOW)Parando EBA...$(RESET)"
	docker compose down

restart: ## Reinicia todos os serviços
	docker compose restart

build: ## Reconstrói as imagens Docker
	docker compose build --no-cache

logs: ## Exibe logs de todos os serviços (Ctrl+C para sair)
	docker compose logs -f

api-logs: ## Exibe logs apenas da API
	docker compose logs -f api

worker-logs: ## Exibe logs dos workers Celery
	docker compose logs -f worker beat

##@ Desenvolvimento Backend
install: ## Instala dependências Python (com uv)
	@echo "$(BLUE)Instalando dependências Python...$(RESET)"
	cd backend && uv sync --all-extras

shell-api: ## Abre shell no container da API
	docker compose exec api bash

shell-db: ## Abre psql no banco de dados
	docker compose exec db psql -U $${POSTGRES_USER:-eba_user} -d $${POSTGRES_DB:-eba_dev}

##@ Banco de Dados
migrate: ## Executa migrations pendentes
	@echo "$(BLUE)Executando migrations...$(RESET)"
	docker compose exec api alembic upgrade head
	@echo "$(GREEN)✓ Migrations aplicadas$(RESET)"

migrate-new: ## Cria nova migration (uso: make migrate-new MSG="descrição")
	@[ "$(MSG)" ] || ( echo "$(RED)Erro: informe MSG='descrição da migration'$(RESET)"; exit 1 )
	docker compose exec api alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## Reverte última migration
	@echo "$(YELLOW)Revertendo última migration...$(RESET)"
	docker compose exec api alembic downgrade -1

migrate-history: ## Exibe histórico de migrations
	docker compose exec api alembic history --verbose

migrate-current: ## Exibe migration atual do banco
	docker compose exec api alembic current

seed: ## Popula o banco com dados de desenvolvimento
	docker compose exec api python -m app.cli seed-dev

db-reset: ## CUIDADO: apaga e recria o banco de desenvolvimento
	@echo "$(RED)⚠ ATENÇÃO: Isso apagará TODOS os dados de desenvolvimento!$(RESET)"
	@read -p "Confirme digitando 'sim': " confirm && [ "$$confirm" = "sim" ] || exit 1
	docker compose down -v db
	docker compose up -d db
	@sleep 5
	$(MAKE) migrate
	$(MAKE) seed
	@echo "$(GREEN)✓ Banco recriado$(RESET)"

##@ Qualidade de Código
lint: ## Executa linting (ruff)
	@echo "$(BLUE)Linting backend...$(RESET)"
	cd backend && .venv/bin/ruff check .
	cd backend && .venv/bin/ruff format --check .
	@echo "$(BLUE)Linting frontend...$(RESET)"
	cd frontend && npm run lint

lint-fix: ## Corrige problemas de linting automaticamente
	cd backend && .venv/bin/ruff check --fix .
	cd backend && .venv/bin/ruff format .
	cd frontend && npm run lint:fix

typecheck: ## Verifica tipos (mypy + tsc)
	@echo "$(BLUE)Type checking backend...$(RESET)"
	cd backend && .venv/bin/mypy app/
	@echo "$(BLUE)Type checking frontend...$(RESET)"
	cd frontend && npm run type-check

format: ## Formata código (ruff + prettier)
	cd backend && .venv/bin/ruff format .
	cd frontend && npm run format

audit: ## Auditoria de segurança de dependências
	@echo "$(BLUE)Auditoria Python...$(RESET)"
	cd backend && .venv/bin/pip-audit
	@echo "$(BLUE)Auditoria Node.js...$(RESET)"
	cd frontend && npm audit

bandit: ## Análise de segurança do código Python
	cd backend && .venv/bin/bandit -r app/ -x tests/

##@ Testes
test: ## Executa todos os testes
	@echo "$(BLUE)Executando testes backend...$(RESET)"
	docker compose exec api pytest
	@echo "$(BLUE)Executando testes frontend...$(RESET)"
	cd frontend && npm run test:coverage

test-unit: ## Apenas testes unitários (rápidos, sem banco)
	cd backend && .venv/bin/pytest -m unit -v

test-integration: ## Testes de integração (requer banco)
	docker compose exec api pytest -m integration -v

test-cov: ## Testes com relatório de coverage
	docker compose exec api pytest --cov-report=html
	@echo "$(GREEN)✓ Coverage em backend/htmlcov/index.html$(RESET)"

##@ Utilitários
clean: ## Remove arquivos temporários e caches
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/.mypy_cache backend/.ruff_cache backend/htmlcov backend/.coverage
	rm -rf frontend/dist frontend/node_modules/.cache
	@echo "$(GREEN)✓ Limpeza concluída$(RESET)"

ps: ## Lista serviços e seus status
	docker compose ps

health: ## Verifica saúde de todos os serviços
	@echo "$(BLUE)Verificando saúde dos serviços...$(RESET)"
	@curl -sf http://localhost:8000/health/ready | python3 -m json.tool || echo "$(RED)API não responde$(RESET)"

