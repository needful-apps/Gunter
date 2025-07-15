#!/bin/bash
# Script to format imports using isort in the Gunter project

# Find the project directory (one directory above the script)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Check if virtual environment exists and activate
if [ -d "venv" ]; then
    echo "🔍 Virtual environment found, activating..."
    source venv/bin/activate
fi

# Check if isort is installed
if ! command -v isort &> /dev/null; then
    echo "⚠️ isort not found. Installing..."
    pip install isort
fi

echo "🔄 Sorting imports with isort..."
isort --profile black .

echo "✅ Import sorting completed!"
