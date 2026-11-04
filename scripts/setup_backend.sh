#!/usr/bin/env bash
set -e
export PATH="/home/marcosmadeira/.local/bin:$PATH"

cd /home/marcosmadeira/enterprise-billing-automation/backend
echo "Installing dependencies via uv sync..."
uv sync --all-extras
echo "Backend setup complete!"
