#!/usr/bin/env bash
# SessionStart hook: ensure the plugin's Python venv exists and is in sync
# with mcp-server/requirements.txt. Runs silently if everything is already
# in place; only does work on first session or when requirements change.

set -euo pipefail

PLUGIN_DATA="${CLAUDE_PLUGIN_DATA:?CLAUDE_PLUGIN_DATA not set}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT not set}"
VENV="${PLUGIN_DATA}/venv"
REQ_SRC="${PLUGIN_ROOT}/mcp-server/requirements.txt"
REQ_MARKER="${PLUGIN_DATA}/requirements.txt"

mkdir -p "${PLUGIN_DATA}"

# Pick a Python interpreter (prefer python3.12+, fall back to python3)
PYTHON=""
for candidate in python3.13 python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "anything-to-dataiku: ERROR — no python3 found on PATH. Install Python 3.12+ and restart Claude Code." >&2
    exit 0  # exit 0 so the session still starts; the user gets an MCP startup error which surfaces the issue
fi

# Create venv if missing
if [ ! -d "$VENV" ]; then
    echo "anything-to-dataiku: creating Python venv at ${VENV}..." >&2
    "$PYTHON" -m venv "$VENV" >&2
fi

# Install/update deps if requirements changed (or marker absent)
if ! diff -q "$REQ_SRC" "$REQ_MARKER" >/dev/null 2>&1; then
    echo "anything-to-dataiku: installing Python dependencies..." >&2
    "$VENV/bin/pip" install -q --upgrade pip >&2
    "$VENV/bin/pip" install -q -r "$REQ_SRC" >&2
    cp "$REQ_SRC" "$REQ_MARKER"
    echo "anything-to-dataiku: dependencies ready." >&2
fi
