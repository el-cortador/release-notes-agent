#!/usr/bin/env bash
set -e

# In WSL, prefer Windows Python (py.exe) over the system Linux Python
PYTHON=$(command -v py.exe || command -v python || command -v python3 || true)
if [ -z "$PYTHON" ]; then
    echo "Error: Python not found."
    exit 1
fi

echo "Using Python: $PYTHON"
"$PYTHON" -m pip install -q -r requirements.txt

echo "Starting server at http://127.0.0.1:5000"
"$PYTHON" backend/app.py
