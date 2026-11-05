#!/usr/bin/env bash
# Setup script for Claude Code cloud sessions (paste into the environment's setup script).
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  pip install --quiet uv
fi

uv sync
mkdir -p data
