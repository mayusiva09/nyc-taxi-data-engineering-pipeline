#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
. .venv/bin/activate

python -m pip install --upgrade pip

pip install -r requirements.txt

mkdir -p data/raw data/processed logs
# Demo-only: allow the non-root Airflow container user to write processed files.
chmod a+rwx data data/raw data/processed logs
# Download two months through Python streaming HTTP; equivalent to curl/wget.
python -m src.cli download
docker compose up -d --build postgres
printf '\nSetup complete. Run: docker compose up -d --build\n'
