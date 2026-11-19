#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
  python3.12 -m venv .venv
fi
if [[ ! -f .venv/bullbench-local-installed ]]; then
  .venv/bin/python -m pip install -r requirements-local.lock
  .venv/bin/python -m pip install --no-deps -e .
  .venv/bin/python -m pip check
  .venv/bin/python scripts/run_local.py --check
  touch .venv/bullbench-local-installed
fi
exec .venv/bin/python scripts/run_local.py
