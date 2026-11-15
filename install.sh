#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Expense Tracker – first-time setup
# Run once:  bash install.sh
# Then launch any time by double-clicking: run.command
# ─────────────────────────────────────────────────────────────────────────────

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo ""
echo "  ◈  Expense Tracker — Setup"
echo "  ──────────────────────────"
echo ""

# Check Python 3
if ! command -v python3 &>/dev/null; then
  echo "  ✗  Python 3 not found. Install from https://python.org"
  exit 1
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  ✓  Python $PY_VER found"

# Create virtual environment
if [ ! -d "venv" ]; then
  echo "  →  Creating virtual environment…"
  python3 -m venv venv
fi

# Activate and install deps
echo "  →  Installing dependencies…"
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "  ✓  Dependencies installed"

# Make launcher executable
chmod +x run.command
echo "  ✓  run.command is ready"

echo ""
echo "  ✅  Setup complete!"
echo "      Double-click  run.command  to launch the app."
echo ""
