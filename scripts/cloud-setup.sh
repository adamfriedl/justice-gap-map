#!/usr/bin/env bash
# Setup script for Claude Code cloud sessions (paste into the environment's setup script).
# Runs before the repo is cloned, so it only installs tools. Dependencies are
# installed by the SessionStart hook in .claude/settings.json.
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  pip install --quiet uv
fi
