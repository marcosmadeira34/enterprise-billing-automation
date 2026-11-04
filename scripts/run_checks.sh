#!/usr/bin/env bash
set -e
export PATH="/home/marcosmadeira/.local/bin:$PATH"

cd /home/marcosmadeira/enterprise-billing-automation/backend

echo "=== 1. Checking Ruff Linting ==="
.venv/bin/ruff check .

echo "=== 2. Checking Ruff Formatting ==="
.venv/bin/ruff format --check .

echo "=== 3. Checking Mypy Type Hints ==="
.venv/bin/mypy app/

echo "=== 4. Running Pytest Suite ==="
.venv/bin/pytest -v

echo "All checks passed successfully!"

