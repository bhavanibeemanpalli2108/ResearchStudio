#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${RESEARCH_PYTHON:-.venv/bin/python}" -m src.research_platform.dev "$@"
