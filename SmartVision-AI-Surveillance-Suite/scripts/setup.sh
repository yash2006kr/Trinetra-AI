#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
test -f .env || cp .env.example .env
mkdir -p data logs sample_datasets
echo "SmartVision setup complete. Run: ./.venv/bin/uvicorn api_gateway.main:app --reload"
