#!/usr/bin/env bash
# run.sh — starts the Flask dev server using the uv-managed virtual environment
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PYTHON="$VENV/bin/python"
FLASK="$VENV/bin/flask"

echo "═══════════════════════════════════════"
echo "  G2Commons — Flask Dev Server"
echo "═══════════════════════════════════════"

# Check venv exists
if [ ! -f "$PYTHON" ]; then
    echo "✗ Virtual environment not found at $VENV"
    echo "  Create it with: uv venv && uv pip install -r requirements.txt"
    exit 1
fi

echo "✓ Using Python: $($PYTHON --version)"

# Sync dependencies via uv
if command -v uv &>/dev/null; then
    echo "→ Syncing dependencies with uv..."
    uv pip install -q -r "$SCRIPT_DIR/requirements.txt"
else
    echo "→ uv not found, skipping dependency sync"
fi

# Start Flask inside the venv
echo "→ Starting Flask at http://localhost:5000"
echo "═══════════════════════════════════════"
cd "$SCRIPT_DIR"
"$FLASK" run --debug
