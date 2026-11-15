#!/bin/bash
# Double-click this file in Finder to launch Expense Tracker.
# If you see a security warning, right-click → Open, then click Open.

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ -d "venv" ]; then
  source venv/bin/activate
fi

python3 main.py
