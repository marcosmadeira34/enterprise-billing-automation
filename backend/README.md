# EBA Backend API

Serviço de backend da plataforma Enterprise Billing Automation construído com FastAPI, SQLAlchemy 2.x, Alembic, Celery e Redis.

## Execução Local

```bash
uv sync --all-extras
source .venv/bin/activate
uvicorn app.main:app --reload
```

